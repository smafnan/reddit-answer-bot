"""Reddit retrieval — the ONLY grounding source for the engine.

Primary path: the official Reddit Data API via PRAW in application-only
(client_credentials) read-only mode — client_id + client_secret only, no
username/password. This is the only path trusted for live grounding; anonymous
`.json` is blocked (HTTP 403) from servers and kept solely as a local-dev
best-effort fallback.

Every call returns a RetrievalResult carrying a STATUS so the pipeline can tell
apart genuine zero-coverage ("empty") from an unreachable API ("error") or
missing credentials ("no_credentials"). That distinction is what lets the engine
refuse honestly instead of pretending Reddit had nothing.
"""

import json
import logging
import os
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

logger = logging.getLogger(__name__)

RetrievalStatus = Literal["ok", "empty", "error", "no_credentials", "demo"]

BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


@dataclass
class RetrievalResult:
    status: RetrievalStatus
    comments: List[Dict[str, Any]] = field(default_factory=list)
    # query -> [comment_id, ...] in rank order, so ranking can compute RRF.
    per_query_rank: Dict[str, List[str]] = field(default_factory=dict)


def _local_dev() -> bool:
    """True when anon .json discovery is explicitly allowed (dev machines)."""
    return os.environ.get("ALLOW_ANON_REDDIT", "").lower() in ("1", "true", "yes")


def _default_user_agent() -> str:
    return os.environ.get(
        "REDDIT_USER_AGENT",
        "server:com.portfolio.redditanswers:v3.0.0 (by /u/reddit_answer_engine)",
    )


def build_reddit(reddit_creds: Optional[Dict[str, str]] = None):
    """Create an app-only, read-only PRAW client, or return None if no creds.

    Passing only client_id + client_secret makes PRAW use the client_credentials
    grant, so reddit.read_only is True and no user account is involved.
    Bring-your-own creds (from the request body) take precedence over env vars.
    """
    creds = reddit_creds or {}
    client_id = creds.get("client_id") or os.environ.get("REDDIT_CLIENT_ID")
    client_secret = creds.get("client_secret") or os.environ.get("REDDIT_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None
    try:
        import praw

        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=_default_user_agent(),
            ratelimit_seconds=300,  # let PRAW self-throttle within the free tier
            check_for_updates=False,
        )
        reddit.read_only = True
        return reddit
    except Exception as exc:
        logger.warning("Could not initialise PRAW client: %s", exc)
        return None


def _normalize_comment(
    comment_id: str,
    post_title: str,
    post_url: str,
    comment_permalink: str,
    subreddit: str,
    author: Optional[str],
    ups: int,
    body: str,
    created_utc: float,
) -> Optional[Dict[str, Any]]:
    body = (body or "").strip()
    if not body or body in ("[deleted]", "[removed]"):
        return None
    return {
        "comment_id": comment_id,
        "post_title": post_title or "",
        "post_url": post_url or "",
        "comment_permalink": comment_permalink or post_url or "",
        "subreddit": subreddit or "",
        "author": author or "[deleted]",
        "ups": int(ups or 0),
        "body": body,
        "created_utc": float(created_utc or 0.0),
    }


def _collect_comments_from_submission(submission, comments_per_post: int) -> List[Dict[str, Any]]:
    """Fetch the top comments of one submission (cheap: replace_more(limit=0))."""
    out: List[Dict[str, Any]] = []
    try:
        submission.comment_sort = "top"
        submission.comments.replace_more(limit=0)  # drop 'load more' stubs, no extra requests
        for c in submission.comments.list()[:comments_per_post]:
            permalink = f"https://www.reddit.com{getattr(c, 'permalink', '')}"
            author = getattr(c.author, "name", None) if getattr(c, "author", None) else None
            norm = _normalize_comment(
                comment_id=f"t1_{c.id}",
                post_title=submission.title,
                post_url=f"https://www.reddit.com{submission.permalink}",
                comment_permalink=permalink,
                subreddit=str(submission.subreddit),
                author=author,
                ups=getattr(c, "score", 0),
                body=getattr(c, "body", ""),
                created_utc=getattr(c, "created_utc", 0.0),
            )
            if norm:
                out.append(norm)
    except Exception as exc:
        logger.warning("Comment fetch failed for %s: %s", getattr(submission, "id", "?"), exc)
    return out


def search_reddit(
    plan,
    reddit_creds: Optional[Dict[str, str]] = None,
    posts_per_query: int = 12,
    top_posts: int = 10,
    comments_per_post: int = 6,
) -> RetrievalResult:
    """Search real Reddit for the plan's queries and collect top comments.

    Returns a RetrievalResult whose status distinguishes real zero-coverage from
    errors and missing credentials.
    """
    reddit = build_reddit(reddit_creds)
    if reddit is None:
        if _local_dev():
            return _anon_json_fallback(plan)
        return RetrievalResult("no_credentials")

    scope = "+".join(plan.subreddits) if plan.subreddits else "all"
    try:
        sub = reddit.subreddit(scope)
    except Exception as exc:
        logger.warning("Bad subreddit scope '%s': %s — falling back to r/all", scope, exc)
        sub = reddit.subreddit("all")

    queries = plan.search_queries or [plan.standalone_question]
    submissions_by_id: Dict[str, Any] = {}
    per_query_post_rank: Dict[str, List[str]] = {}
    hit_error = False

    for q in queries:
        if not q:
            continue
        order: List[str] = []
        for attempt in range(3):
            try:
                for post in sub.search(q, sort="relevance", time_filter="all", limit=posts_per_query):
                    submissions_by_id.setdefault(post.id, post)
                    order.append(f"t3_{post.id}")
                break
            except Exception as exc:
                # 403/429 from datacenter IPs, transient network, etc.
                logger.warning("search '%s' attempt %d failed: %s", q, attempt + 1, exc)
                hit_error = True
                time.sleep(2 * (attempt + 1))  # exponential-ish backoff
        per_query_post_rank[q] = order

    # Rank posts by score, keep the strongest, then fetch their top comments.
    ranked_posts = sorted(
        submissions_by_id.values(), key=lambda p: getattr(p, "score", 0), reverse=True
    )[:top_posts]

    post_to_comment_ids: Dict[str, List[str]] = {}
    comments: List[Dict[str, Any]] = []
    for post in ranked_posts:
        post_comments = _collect_comments_from_submission(post, comments_per_post)
        post_to_comment_ids[f"t3_{post.id}"] = [c["comment_id"] for c in post_comments]
        comments.extend(post_comments)

    # Rewrite per-query provenance from post ids to the comment ids we kept, so
    # ranking's RRF rewards comments from posts surfaced by multiple queries.
    per_query_rank: Dict[str, List[str]] = {}
    for q, post_ids in per_query_post_rank.items():
        cids: List[str] = []
        for pid in post_ids:
            cids.extend(post_to_comment_ids.get(pid, []))
        per_query_rank[q] = cids

    if comments:
        return RetrievalResult("ok", comments, per_query_rank)
    if hit_error:
        return RetrievalResult("error")  # unreachable / rate-limited — NOT "no coverage"
    return RetrievalResult("empty")  # genuine zero coverage


# ------------------------------------------------------------ local-dev anon fallback

def fetch_json_from_url(url: str) -> Any:
    """Fetch a Reddit thread's JSON (local dev only; 403s from servers)."""
    clean = url.split("?")[0]
    if not clean.endswith(".json"):
        clean = clean.rstrip("/") + ".json"
    req = urllib.request.Request(clean, headers={"User-Agent": BROWSER_UA})
    try:
        with urllib.request.urlopen(req, timeout=6) as response:
            if response.status == 200:
                return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        logger.warning("Anon JSON fetch failed for %s: %s", clean, exc)
    return None


def extract_comments_from_json(reddit_json: Any) -> List[Dict[str, Any]]:
    """Parse comments from a Reddit thread .json payload into normalized dicts."""
    out: List[Dict[str, Any]] = []
    if not reddit_json or len(reddit_json) < 2:
        return out
    try:
        post = reddit_json[0]["data"]["children"][0]["data"]
        title = post.get("title", "")
        post_url = f"https://www.reddit.com{post.get('permalink', '')}"
        subreddit = post.get("subreddit", "")
    except Exception:
        title, post_url, subreddit = "", "", ""
    try:
        for child in reddit_json[1]["data"]["children"]:
            if child.get("kind") != "t1":
                continue
            d = child.get("data", {})
            norm = _normalize_comment(
                comment_id=f"t1_{d.get('id', '')}",
                post_title=title,
                post_url=post_url,
                comment_permalink=f"https://www.reddit.com{d.get('permalink', '')}",
                subreddit=subreddit or d.get("subreddit", ""),
                author=d.get("author"),
                ups=d.get("ups", 0),
                body=d.get("body", ""),
                created_utc=d.get("created_utc", 0.0),
            )
            if norm:
                out.append(norm)
    except Exception as exc:
        logger.warning("Error parsing anon comments: %s", exc)
    return out


def _anon_json_fallback(plan) -> RetrievalResult:
    """Best-effort, local-dev-only: discover threads then read their real .json.

    DuckDuckGo is used only to DISCOVER thread URLs; grounding is always on the
    fetched comment JSON, never on search snippets. Gated behind ALLOW_ANON_REDDIT.
    """
    try:
        from duckduckgo_search import DDGS
    except Exception:
        return RetrievalResult("no_credentials")

    comments: List[Dict[str, Any]] = []
    per_query_rank: Dict[str, List[str]] = {}
    queries = plan.search_queries or [plan.standalone_question]
    for q in queries[:3]:
        order: List[str] = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(f"site:reddit.com {q}", max_results=4):
                    url = r.get("href", "")
                    if "/comments/" not in url:
                        continue
                    for c in extract_comments_from_json(fetch_json_from_url(url)):
                        comments.append(c)
                        order.append(c["comment_id"])
        except Exception as exc:
            logger.warning("Anon fallback query '%s' failed: %s", q, exc)
        per_query_rank[q] = order

    if comments:
        return RetrievalResult("ok", comments, per_query_rank)
    return RetrievalResult("empty")
