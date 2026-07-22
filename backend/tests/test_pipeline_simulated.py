"""End-to-end pipeline tests in offline demo mode (no network, no keys)."""

from graph import RedditAnswerEngine


def _run(messages):
    data = None
    steps = []
    for ev in RedditAnswerEngine(messages).run():
        steps.append(ev["step"])
        if ev["step"] == "completed":
            data = ev["data"]
    return steps, data


def test_pipeline_stages_execute():
    steps, data = _run([{"role": "user", "content": "Is a CS degree worth it?"}])
    for expected in ["understand", "retrieve", "answer", "completed"]:
        assert expected in steps, f"missing stage: {expected}"
    assert "failed" not in steps
    assert data is not None


def test_covered_topic_is_grounded_with_valid_citations():
    _, data = _run([{"role": "user", "content": "Best laptop for local LLMs and Ollama?"}])
    assert data["llm_mode"] == "simulated"
    assert data["grounded"] is True
    assert data["answer_markdown"]
    assert data["citations"], "grounded answer must have citations"
    # every citation index must exist in the sources/pack (1-based, contiguous)
    src_count = len(data["sources"])
    for c in data["citations"]:
        assert 1 <= c["index"] <= max(src_count, len(data["citations"]))
        assert c["permalink"].startswith("https://www.reddit.com")
    assert data["suggested_followups"]


def test_greeting_is_not_grounded_and_has_no_sources():
    _, data = _run([{"role": "user", "content": "hi there"}])
    assert data["intent"] == "greeting"
    assert data["grounded"] is False
    assert data["citations"] == []
    assert data["sources"] == []


def test_followup_resolves_prior_topic():
    """A context-free follow-up ('what about depreciation?') must inherit the
    topic from prior turns (the 'understand like Google' guarantee), not fall back
    to a different topic or refuse in demo mode."""
    _, data = _run([
        {"role": "user", "content": "Is a Tesla Model Y worth it?"},
        {"role": "assistant", "content": "Owners praise charging and software, warn on build quality."},
        {"role": "user", "content": "what about the depreciation you mentioned?"},
    ])
    assert data["grounded"] is True
    assert data["citations"]
    assert "tesla" in data["answer_markdown"].lower() or "supercharger" in data["answer_markdown"].lower()


def test_unknown_topic_refuses_instead_of_fabricating():
    _, data = _run([{"role": "user", "content": "How do I ferment homemade kimchi safely?"}])
    assert data["grounded"] is False
    assert data["refusal_reason"]
    assert data["citations"] == []
