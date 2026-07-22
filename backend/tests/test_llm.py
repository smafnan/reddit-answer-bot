"""Unit tests for the per-request LLM client."""

from llm import LLMClient, _extract_json
from schemas import QueryPlan


def test_no_key_means_simulated_mode():
    client = LLMClient()
    assert client.active is False
    assert client.provider is None


def test_key_without_provider_does_not_crash():
    client = LLMClient(provider=None, api_key="fake-key")
    assert client.active is True
    assert client.provider == "groq"  # sensible default


def test_claude_alias_maps_to_anthropic():
    client = LLMClient(provider="claude", api_key="fake-key")
    assert client.provider == "anthropic"


def test_nvidia_provider_configures_openai_compatible_client():
    client = LLMClient(provider="nvidia", api_key="nvapi-fake")
    assert client.active is True
    assert client.provider == "nvidia"
    assert client.model.startswith("meta/") or "/" in client.model
    # NVIDIA is OpenAI-compatible but not in the json_object allowlist.
    from llm import JSON_MODE_PROVIDERS
    assert "nvidia" not in JSON_MODE_PROVIDERS


def test_nvidia_env_key_fallback(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-fake-env")
    client = LLMClient()
    assert client.active is True
    assert client.provider == "nvidia"


def test_env_key_fallback(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-env-key")
    client = LLMClient()
    assert client.active is True
    assert client.provider == "groq"


def test_simulated_structured_call_returns_valid_plan():
    client = LLMClient()
    data = client.call_structured('Current user message: "is a tesla model y worth it"', QueryPlan)
    plan = QueryPlan.model_validate(data)
    assert plan.intent in ("answerable", "follow_up", "greeting", "off_topic", "needs_clarification")


def test_extract_json_strips_markdown_fences():
    assert _extract_json('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert _extract_json('Here you go:\n{"a": 1}\nHope that helps!') == '{"a": 1}'
    assert _extract_json("[1, 2]") == "[1, 2]"
