"""Deterministic ranking and evidence-pack selection — no embeddings, no new deps.

Turns retrieved Reddit comments into a small, numbered, diverse evidence pack and
computes coverage signals the grounding gate uses to decide answer-vs-refuse.
"""

import math
import re
import time
from typing import Any, Dict, List, Tuple

MIN_CITEABLE = 3        # distinct relevant comments required to attempt an answer
REL_FLOOR = 0.12        # per-comment relevance floor to count toward coverage
TOP_REL_FLOOR = 0.20    # the best comment must clear this
MAX_PACK = 8            # comments cited into the evidence pack
DUP_OVERLAP = 0.6       # >60% token overlap => near-duplicate, dropped for diversity


def _tokens(s: str) -> set:
    return set(re.findall(r"[a-z0-9]{3,}", (s or "").lower()))


def _query_tokens(plan) -> set:
    toks = _tokens(plan.standalone_question)
    for q in plan.search_queries or []:
        toks |= _tokens(q)
    return toks


def _relevance(comment: Dict[str, Any], query_toks: set) -> float:
    """Cheap BM25-lite: weighted token overlap of comment(title+body) vs the query."""
    c = _tokens(comment.get("post_title", "")) | _tokens(comment.get("body", ""))
    if not query_toks or not c:
        return 0.0
    inter = len(query_toks & c)
    if not inter:
        return 0.0
    return inter / math.sqrt(len(query_toks) * math.log1p(len(c)))


def _strong_first_and_last(picked: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Order strongest-first-and-last to mitigate 'lost in the middle'."""
    if len(picked) <= 2:
        return picked
    ordered = [None] * len(picked)
    left, right = 0, len(picked) - 1
    for i, c in enumerate(picked):  # picked is already score-desc
        if i % 2 == 0:
            ordered[left] = c
            left += 1
        else:
            ordered[right] = c
            right -= 1
    return ordered


def rank_and_select(plan, result) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
    """Return (evidence_pack, signals). Pack comments carry a 1-based `index`."""
    comments = result.comments
    if not comments:
        return [], {"n_relevant": 0, "top_relevance": 0.0, "n_threads": 0}

    query_toks = _query_tokens(plan)

    # RRF across per-query rankings: comments surfaced by multiple queries get a boost.
    rrf: Dict[str, float] = {}
    for order in result.per_query_rank.values():
        for rank, cid in enumerate(order):
            rrf[cid] = rrf.get(cid, 0.0) + 1.0 / (60 + rank)

    max_ups = max((c["ups"] for c in comments), default=1) or 1
    half_life = 180.0 if plan.recency_sensitive else 540.0  # days
    now = time.time()
    plan_subs = {s.lower() for s in (plan.subreddits or [])}

    for c in comments:
        rel = _relevance(c, query_toks)
        ups_n = math.log1p(max(c["ups"], 0)) / math.log1p(max_ups)
        age_days = max((now - (c["created_utc"] or now)) / 86400.0, 0.0)
        recency = math.exp(-age_days / half_life)
        authority = 1.0 if c["subreddit"].lower() in plan_subs else 0.0
        c["_relevance"] = rel
        c["_score"] = (
            0.45 * rel
            + 0.20 * ups_n
            + 0.15 * rrf.get(c["comment_id"], 0.0)
            + 0.10 * recency
            + 0.10 * authority
        )

    ranked = sorted(comments, key=lambda x: x["_score"], reverse=True)

    # MMR-lite: drop near-duplicate bodies to preserve perspective diversity.
    picked: List[Dict[str, Any]] = []
    seen_tokens: List[set] = []
    for c in ranked:
        ct = _tokens(c["body"])
        if any(len(ct & s) / max(len(ct | s), 1) > DUP_OVERLAP for s in seen_tokens):
            continue
        picked.append(c)
        seen_tokens.append(ct)
        if len(picked) >= MAX_PACK:
            break

    pack = _strong_first_and_last(picked)
    for i, c in enumerate(pack, start=1):
        c["index"] = i

    signals = {
        "n_relevant": sum(1 for c in picked if c["_relevance"] >= REL_FLOOR),
        "top_relevance": max((c["_relevance"] for c in picked), default=0.0),
        "n_threads": len({c["post_url"] for c in picked}),
    }
    return pack, signals
