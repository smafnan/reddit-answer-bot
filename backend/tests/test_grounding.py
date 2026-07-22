"""The honesty contract: coverage gate, citation validation, and ranking signals."""

from grounding import build_citations, coverage_gate, validate_citations
from ranking import MIN_CITEABLE, rank_and_select
from retrieval import RetrievalResult
from schemas import AnswerOutput, QueryPlan


def _pack(n):
    return [{"index": i} for i in range(1, n + 1)]


# ---- coverage gate ----

def test_gate_no_credentials_message_is_distinct():
    out = coverage_gate(RetrievalResult("no_credentials"), {})
    assert out is not None and out.grounded is False
    assert "credential" in out.refusal_reason.lower()


def test_gate_error_is_distinct_from_empty():
    err = coverage_gate(RetrievalResult("error"), {})
    empty = coverage_gate(RetrievalResult("empty"), {"n_relevant": 0, "top_relevance": 0.0})
    assert err.refusal_reason != empty.refusal_reason
    assert "retry" in err.refusal_reason.lower() or "again" in err.refusal_reason.lower()


def test_gate_passes_with_enough_coverage():
    signals = {"n_relevant": MIN_CITEABLE, "top_relevance": 0.9}
    assert coverage_gate(RetrievalResult("ok"), signals) is None


def test_gate_refuses_thin_coverage():
    signals = {"n_relevant": 1, "top_relevance": 0.9}
    assert coverage_gate(RetrievalResult("ok"), signals) is not None


# ---- citation validation (anti-hallucination linchpin) ----

def test_fabricated_citation_downgrades_to_ungrounded():
    ans = AnswerOutput(answer_markdown="Bold claim [9].", grounded=True)
    out = validate_citations(ans, _pack(3))
    assert out.grounded is False


def test_grounded_answer_without_citations_is_downgraded():
    ans = AnswerOutput(answer_markdown="Claim with no marker.", grounded=True)
    out = validate_citations(ans, _pack(3))
    assert out.grounded is False


def test_valid_citations_are_kept():
    ans = AnswerOutput(answer_markdown="A [1]. B [3].", tldr="short [1]", grounded=True)
    out = validate_citations(ans, _pack(3))
    assert out.grounded is True
    assert out.used_citation_indices == [1, 3]


def test_build_citations_maps_indices_to_pack():
    pack = [{"index": 1, "post_title": "T", "post_url": "u", "comment_permalink": "p",
             "subreddit": "s", "author": "a", "body": "hello world", "ups": 5, "created_utc": 1.0}]
    cites = build_citations([1], pack)
    assert cites[0].index == 1 and cites[0].permalink == "p" and cites[0].snippet == "hello world"


# ---- ranking ----

def _comment(cid, title, body, ups=10, sub="test", ts=1718112000.0):
    return {"comment_id": cid, "post_title": title, "post_url": f"u/{cid}",
            "comment_permalink": f"p/{cid}", "subreddit": sub, "author": "x",
            "ups": ups, "body": body, "created_utc": ts}


def test_relevance_ranks_on_topic_above_off_topic():
    plan = QueryPlan(intent="answerable", standalone_question="best mechanical keyboard switches",
                     search_queries=["mechanical keyboard switches"])
    on = _comment("t1_a", "Keyboard switches", "I love tactile mechanical keyboard switches for typing", ups=5)
    off = _comment("t1_b", "Cooking pasta", "boil water and add salt to the pasta", ups=500)
    result = RetrievalResult("ok", [off, on], {"mechanical keyboard switches": ["t1_b", "t1_a"]})
    pack, signals = rank_and_select(plan, result)
    assert pack[0]["comment_id"] == "t1_a"  # relevance beats raw upvotes
    assert signals["n_relevant"] >= 1


def test_mmr_drops_near_duplicates():
    plan = QueryPlan(intent="answerable", standalone_question="tesla model y worth it",
                     search_queries=["tesla model y worth it"])
    body = "The tesla model y supercharger network is the main reason to buy it worth every penny"
    a = _comment("t1_a", "Tesla", body, ups=10)
    b = _comment("t1_b", "Tesla", body, ups=9)  # near-identical body
    c = _comment("t1_c", "Tesla", "Build quality on the tesla model y is inconsistent panel gaps", ups=8)
    result = RetrievalResult("ok", [a, b, c], {})
    pack, _ = rank_and_select(plan, result)
    bodies = [p["body"] for p in pack]
    assert bodies.count(body) == 1  # the duplicate was dropped
