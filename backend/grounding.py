"""The honesty guarantee — deterministic, no LLM calls.

Two jobs:
  coverage_gate()     — decide, from retrieval status + ranking signals, whether
                        there's enough real Reddit coverage to attempt an answer;
                        otherwise return an honest refusal (distinguishing an
                        unreachable API and missing credentials from true zero-coverage).
  validate_citations()— after the LLM answers, enforce that every [n] marker maps
                        to a real retrieved comment. Fabricated or out-of-range
                        citations downgrade the answer to grounded=False. This is
                        what makes "grounded in Reddit" a guarantee, not a hope.
"""

import re
from typing import Any, Dict, List, Optional

from ranking import MIN_CITEABLE, TOP_REL_FLOOR
from schemas import AnswerOutput, Citation

REFUSAL_TEMPLATE = (
    "Reddit doesn't clearly cover this. I'd rather not guess — try rephrasing, "
    "adding specifics, or asking something communities actually discuss."
)


def _refuse(reason: str) -> AnswerOutput:
    return AnswerOutput(
        answer_markdown=reason,
        tldr="",
        grounded=False,
        refusal_reason=reason,
        used_citation_indices=[],
    )


def coverage_gate(result, signals: Dict[str, float]) -> Optional[AnswerOutput]:
    """Return a refusal AnswerOutput to short-circuit, or None to proceed to the LLM."""
    status = getattr(result, "status", "empty")
    if status == "error":
        return _refuse(
            "I couldn't reach Reddit right now (rate-limited or a network hiccup). "
            "This isn't 'no coverage' — please try again in a moment."
        )
    if status == "no_credentials":
        return _refuse(
            "Live Reddit access isn't configured yet. Add Reddit API credentials "
            "(REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET, or bring your own in settings) "
            "to get real, grounded answers."
        )
    if signals.get("n_relevant", 0) < MIN_CITEABLE or signals.get("top_relevance", 0.0) < TOP_REL_FLOOR:
        return _refuse(REFUSAL_TEMPLATE)
    return None


def validate_citations(answer: AnswerOutput, pack: List[Dict[str, Any]]) -> AnswerOutput:
    """Enforce that every [n] in the answer maps to a real pack comment.

    A grounded answer with no citations, or one citing an index that isn't in the
    evidence pack, is downgraded to grounded=False — never shown as fact.
    """
    valid = {c["index"] for c in pack}
    cited = {int(n) for n in re.findall(r"\[(\d+)\]", answer.answer_markdown or "")}
    cited |= {int(n) for n in re.findall(r"\[(\d+)\]", answer.tldr or "")}

    if answer.grounded:
        if not cited:
            return _refuse("The generated answer wasn't grounded in the retrieved comments.")
        if not cited.issubset(valid):
            return _refuse("The answer referenced sources that weren't in the evidence pack.")

    answer.used_citation_indices = sorted(cited & valid)
    return answer


def build_citations(used_indices: List[int], pack: List[Dict[str, Any]]) -> List[Citation]:
    by_idx = {c["index"]: c for c in pack}
    out: List[Citation] = []
    for i in used_indices:
        c = by_idx.get(i)
        if not c:
            continue
        out.append(
            Citation(
                index=i,
                thread_title=c["post_title"],
                permalink=c.get("comment_permalink") or c["post_url"],
                subreddit=c["subreddit"],
                author=c["author"],
                snippet=c["body"][:280],
                ups=c["ups"],
                created_utc=c["created_utc"],
            )
        )
    return out
