"""End-to-end pipeline tests in simulated demo mode (no network, no API keys)."""

from agents import fact_checking_agent, spam_and_quality_agent
from graph import RedditIntelligencePipeline
from llm import LLMClient

MOCK_COMMENTS = [
    {"author": "user1", "body": "Bro just buy a Mac lol", "ups": 5, "subreddit": "mac"},
    {
        "author": "user2",
        "body": "I have been using the M3 Max 128GB for running Llama 3. The unified memory makes a massive difference for local model loading.",
        "ups": 45,
        "subreddit": "LocalLLaMA",
    },
    {"author": "user3", "body": "[deleted]", "ups": 1, "subreddit": "LocalLLaMA"},
    {"author": "user4", "body": "Short text", "ups": 2, "subreddit": "test"},
]


def test_spam_filter_heuristics():
    llm = LLMClient()
    filtered = spam_and_quality_agent(llm, list(MOCK_COMMENTS))
    bodies = [c["body"] for c in filtered]
    assert all("[deleted]" not in b for b in bodies)
    assert all(len(b) >= 30 for b in bodies)
    assert filtered[0]["author"] == "user2"  # highest quality first


def test_demo_fact_check_never_fabricates_verification():
    # Regression: demo mode used to mark unmatched claims as "Verified" with a
    # fabricated explanation. Unmatched claims must be "Unverified" and labelled.
    llm = LLMClient()
    facts = fact_checking_agent(llm, "should I get into beekeeping?", MOCK_COMMENTS)
    assert facts, "demo mode should still return sample facts"
    for fact in facts:
        assert "[Demo sample]" in fact["explanation"]
        if fact["status"] == "Verified":
            # Only pre-authored topic samples may be 'Verified'; they carry the label too.
            assert "[Demo sample]" in fact["explanation"]


def test_full_pipeline_simulated():
    pipeline = RedditIntelligencePipeline("Is a CS degree worth it?")
    steps = [event for event in pipeline.run()]
    step_names = [e["step"] for e in steps]

    # All LangGraph nodes must actually execute — including the parallel trio.
    for expected in [
        "query_expansion",
        "retrieval",
        "spam_filtering",
        "perspective_extraction",
        "knowledge_graph_builder",
        "fact_checking",
        "synthesizer",
        "completed",
    ]:
        assert expected in step_names, f"missing pipeline step: {expected}"
    assert "failed" not in step_names

    report = steps[-1]["data"]
    assert report["llm_mode"] == "simulated"
    assert report["synthesis"]["consensus_summary"]
    assert 0.0 <= report["synthesis"]["confidence_score"] <= 1.0
    assert report["perspectives"]
    assert report["knowledge_graph"]["nodes"]
    assert report["featured_comments"]
