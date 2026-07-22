"""Reddit retrieval — the ONLY grounding source for the engine.

Two paths, chosen automatically:

1. **No credentials (default).** A polite, low-volume scraper: Reddit's public
   `search.rss` for thread discovery + `old.reddit.com` HTML for comments. These
   endpoints still respond (200) to unauthenticated clients, unlike the JSON API
   (now 403). Best-effort: rate-limited and may be blocked from some datacenter
   IPs, so requests are spaced out, cached, and retried with backoff.

2. **Official Reddit API (optional upgrade).** If REDDIT_CLIENT_ID/SECRET are set
   (env or bring-your-own), PRAW app-only read-only mode is used instead — more
   reliable and higher-volume.

Every call returns a RetrievalResult carrying a STATUS so the pipeline can tell
apart genuine zero-coverage ("empty") from an unreachable Reddit ("error").
"""

import html
import logging
import os
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

try:
    import requests
except ImportError:  # requests is a hard dependency; guard only for safety
    requests = None

logger = logging.getLogger(__name__)

RetrievalStatus = Literal["ok", "empty", "error", "no_credentials", "demo"]

SCRAPE_UA = "web:com.portfolio.redditanswers:v3.0.0 (by /u/reddit_answer_engine)"
REQUEST_DELAY = 1.3   # seconds between scrape requests (politeness / rate limits)
_url_cache: Dict[str, Optional[str]] = {}   # per-process HTML/RSS cache


@dataclass
class RetrievalResult:
    status: RetrievalStatus
    comments: List[Dict[str, Any]] = field(default_factory=list)
    per_query_rank: Dict[str, List[str]] = field(default_factory=dict)


def _user_agent() -> str:
    return os.environ.get("REDDIT_USER_AGENT", SCRAPE_UA)


def _normalize_comment(comment_id, post_title, post_url, comment_permalink,
                       subreddit, author, ups, body, created_utc) -> Optional[Dict[str, Any]]:
    body = (body or "").strip()
    if not body or body in ("[deleted]", "[removed]"):
        return None
    return {
        "comment_id": comment_id or f"t1_{abs(hash(body)) % 10**10}",
        "post_title": post_title or "",
        "post_url": post_url or "",
        "comment_permalink": comment_permalink or post_url or "",
        "subreddit": subreddit or "",
        "author": author or "[deleted]",
        "ups": int(ups or 0),
        "body": body,
        "created_utc": float(created_utc or 0.0),
    }


# ======================================================================= API path

def build_reddit(reddit_creds: Optional[Dict[str, str]] = None):
    """App-only read-only PRAW client, or None when no credentials are configured."""
    creds = reddit_creds or {}
    client_id = creds.get("client_id") or os.environ.get("REDDIT_CLIENT_ID")
    client_secret = creds.get("client_secret") or os.environ.get("REDDIT_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None
    try:
        import praw

        reddit = praw.Reddit(client_id=client_id, client_secret=client_secret,
                             user_agent=_user_agent(), ratelimit_seconds=300, check_for_updates=False)
        reddit.read_only = True
        return reddit
    except Exception as exc:
        logger.warning("Could not initialise PRAW client: %s", exc)
        return None


def _search_reddit_api(reddit, plan, posts_per_query, top_posts, comments_per_post) -> RetrievalResult:
    scope = "+".join(plan.subreddits) if plan.subreddits else "all"
    try:
        sub = reddit.subreddit(scope)
    except Exception:
        sub = reddit.subreddit("all")

    submissions: Dict[str, Any] = {}
    per_query_post_rank: Dict[str, List[str]] = {}
    hit_error = False
    for q in (plan.search_queries or [plan.standalone_question]):
        if not q:
            continue
        order: List[str] = []
        for attempt in range(3):
            try:
                for post in sub.search(q, sort="relevance", time_filter="all", limit=posts_per_query):
                    submissions.setdefault(post.id, post)
                    order.append(f"t3_{post.id}")
                break
            except Exception as exc:
                logger.warning("API search '%s' attempt %d failed: %s", q, attempt + 1, exc)
                hit_error = True
                time.sleep(2 * (attempt + 1))
        per_query_post_rank[q] = order

    ranked = sorted(submissions.values(), key=lambda p: getattr(p, "score", 0), reverse=True)[:top_posts]
    post_to_cids: Dict[str, List[str]] = {}
    comments: List[Dict[str, Any]] = []
    for post in ranked:
        cs: List[Dict[str, Any]] = []
        try:
            post.comment_sort = "top"
            post.comments.replace_more(limit=0)
            for c in post.comments.list()[:comments_per_post]:
                author = getattr(c.author, "name", None) if getattr(c, "author", None) else None
                norm = _normalize_comment(f"t1_{c.id}", post.title,
                                          f"https://www.reddit.com{post.permalink}",
                                          f"https://www.reddit.com{getattr(c, 'permalink', '')}",
                                          str(post.subreddit), author, getattr(c, "score", 0),
                                          getattr(c, "body", ""), getattr(c, "created_utc", 0.0))
                if norm:
                    cs.append(norm)
        except Exception as exc:
            logger.warning("API comment fetch failed: %s", exc)
        post_to_cids[f"t3_{post.id}"] = [c["comment_id"] for c in cs]
        comments.extend(cs)

    per_query_rank = {q: [cid for pid in pids for cid in post_to_cids.get(pid, [])]
                      for q, pids in per_query_post_rank.items()}
    if comments:
        return RetrievalResult("ok", comments, per_query_rank)
    return RetrievalResult("error" if hit_error else "empty")


# ==================================================================== scrape path

def _http_get(url: str) -> Optional[str]:
    """Polite GET with UA, caching, and one 429 backoff. Returns text or None."""
    if url in _url_cache:
        return _url_cache[url]
    if requests is None:
        return None
    text = None
    for attempt in range(2):
        try:
            resp = requests.get(url, headers={"User-Agent": _user_agent()}, timeout=10)
            if resp.status_code == 200:
                text = resp.text
                break
            if resp.status_code == 429:
                time.sleep(2.5 * (attempt + 1))
                continue
            logger.warning("scrape GET %s -> HTTP %s", url, resp.status_code)
            break
        except Exception as exc:
            logger.warning("scrape GET %s failed: %s", url, exc)
            break
    _url_cache[url] = text
    return text


def _search_rss(query: str, subreddits: Optional[List[str]] = None, limit: int = 10) -> List[Dict[str, str]]:
    """Discover thread permalinks via Reddit's public search.rss (200 unauthenticated).

    Restricts to the plan's subreddits when provided (much better relevance),
    else searches all of Reddit.
    """
    from urllib.parse import quote

    if subreddits:
        scope = "+".join(subreddits[:3])
        url = f"https://www.reddit.com/r/{scope}/search.rss?q={quote(query)}&restrict_sr=1&sort=relevance&limit={limit}"
    else:
        url = f"https://www.reddit.com/search.rss?q={quote(query)}&sort=relevance&limit={limit}"
    xml = _http_get(url)
    if not xml:
        return []
    threads: List[Dict[str, str]] = []
    try:
        root = ET.fromstring(xml)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for entry in root.findall(".//a:entry", ns):
            link_el = entry.find("a:link", ns)
            title_el = entry.find("a:title", ns)
            link = link_el.get("href") if link_el is not None else ""
            if "/comments/" not in link:
                continue
            sub = re.search(r"/r/([A-Za-z0-9_]+)/", link)
            threads.append({"permalink": link, "title": (title_el.text if title_el is not None else "") or "",
                            "subreddit": sub.group(1) if sub else ""})
    except ET.ParseError as exc:
        logger.warning("search.rss parse error for '%s': %s", query, exc)
    return threads


_COMMENT_CHUNK_RE = re.compile(r'(?=<div [^>]*data-type="comment")')
_AUTHOR_RE = re.compile(r'data-author="([^"]+)"')
_PERMALINK_RE = re.compile(r'data-permalink="([^"]+)"')
_SCORE_RE = re.compile(r'<span class="score unvoted"[^>]*title="(-?\d+)"')
_MD_RE = re.compile(r'<div class="md">(.*?)</div>\s*</div>', re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")


def _scrape_thread_comments(permalink: str, title: str, subreddit: str, limit: int) -> List[Dict[str, Any]]:
    """Scrape top comments from an old.reddit.com thread page (200 unauthenticated)."""
    path = permalink.replace("https://www.reddit.com", "").replace("https://old.reddit.com", "")
    html_text = _http_get(f"https://old.reddit.com{path}?limit=50&sort=top")
    if not html_text:
        return []
    out: List[Dict[str, Any]] = []
    for chunk in _COMMENT_CHUNK_RE.split(html_text)[1:]:
        author_m = _AUTHOR_RE.search(chunk)
        body_m = _MD_RE.search(chunk)
        if not author_m or not body_m:
            continue
        body = " ".join(_TAG_RE.sub("", html.unescape(body_m.group(1))).split())
        score_m = _SCORE_RE.search(chunk)
        perma_m = _PERMALINK_RE.search(chunk)
        cid = ""
        if perma_m:
            tail = perma_m.group(1).rstrip("/").rsplit("/", 1)[-1]
            cid = f"t1_{tail}"
        norm = _normalize_comment(cid, title,
                                  f"https://www.reddit.com{path}",
                                  f"https://www.reddit.com{perma_m.group(1)}" if perma_m else f"https://www.reddit.com{path}",
                                  subreddit, author_m.group(1), score_m.group(1) if score_m else 0,
                                  body, 0.0)
        if norm:
            out.append(norm)
    # keep highest-scored comments from this thread
    out.sort(key=lambda c: c["ups"], reverse=True)
    return out[:limit]


def _search_reddit_scrape(plan, top_threads=6, comments_per_thread=6) -> RetrievalResult:
    """No-credential retrieval: search.rss discovery + old.reddit comment scraping."""
    if requests is None:
        return RetrievalResult("error")

    queries = (plan.search_queries or [plan.standalone_question])[:4]
    threads: Dict[str, Dict[str, str]] = {}
    per_query_threads: Dict[str, List[str]] = {}
    any_response = False
    for i, q in enumerate(queries):
        if not q:
            continue
        # First query also searches all of Reddit (broadens beyond the guessed
        # subreddits); the rest stay subreddit-restricted for precision.
        found = _search_rss(q, plan.subreddits)
        if i == 0 and plan.subreddits:
            found = found + _search_rss(q, None)
            time.sleep(REQUEST_DELAY)
        if found:
            any_response = True
        order = []
        for t in found:
            threads.setdefault(t["permalink"], t)
            order.append(t["permalink"])
        per_query_threads[q] = order
        time.sleep(REQUEST_DELAY)

    if not threads:
        # Discovery produced nothing: distinguish "reddit unreachable" from "no results".
        return RetrievalResult("error" if not any_response else "empty")

    # Fetch comments for the most-referenced threads first.
    thread_freq: Dict[str, int] = {}
    for order in per_query_threads.values():
        for p in order:
            thread_freq[p] = thread_freq.get(p, 0) + 1
    ordered_threads = sorted(threads.values(), key=lambda t: thread_freq.get(t["permalink"], 0), reverse=True)[:top_threads]

    thread_to_cids: Dict[str, List[str]] = {}
    comments: List[Dict[str, Any]] = []
    for t in ordered_threads:
        cs = _scrape_thread_comments(t["permalink"], t["title"], t["subreddit"], comments_per_thread)
        thread_to_cids[t["permalink"]] = [c["comment_id"] for c in cs]
        comments.extend(cs)
        time.sleep(REQUEST_DELAY)

    per_query_rank = {q: [cid for p in order for cid in thread_to_cids.get(p, [])]
                      for q, order in per_query_threads.items()}
    if comments:
        return RetrievalResult("ok", comments, per_query_rank)
    return RetrievalResult("empty")


# ====================================================================== dispatch

def search_reddit(plan, reddit_creds: Optional[Dict[str, str]] = None,
                  posts_per_query: int = 12, top_posts: int = 10, comments_per_post: int = 6) -> RetrievalResult:
    """Retrieve real Reddit comments for the plan. Uses the official API when
    credentials exist, otherwise the no-credential scraper."""
    reddit = build_reddit(reddit_creds)
    if reddit is not None:
        return _search_reddit_api(reddit, plan, posts_per_query, top_posts, comments_per_post)
    return _search_reddit_scrape(plan)
