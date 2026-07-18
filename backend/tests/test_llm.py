"""Unit tests for the per-request LLM client."""

from llm import LLMClient, _extract_json
from schemas import QueryExpansionOutput


def test_no_key_means_simulated_mode():
    client = LLMClient()
    assert client.active is False
    assert client.provider is None


def test_key_without_provider_does_not_crash():
    # Regression: the old configure_llm crashed with AttributeError on
    # provider.lower() when a key was supplied without a provider.
    client = LLMClient(provider=None, api_key="fake-key")
    assert client.active is True
    assert client.provider == "groq"  # sensible default


def test_claude_alias_maps_to_anthropic():
    client = LLMClient(provider="claude", api_key="fake-key")
    assert client.provider == "anthropic"


def test_env_key_fallback(monkeypatch):
    # Regression: server-side env keys were previously ignored entirely.
    monkeypatch.setenv("GROQ_API_KEY", "fake-env-key")
    client = LLMClient()
    assert client.active is True
    assert client.provider == "groq"


def test_env_key_fallback_respects_explicit_provider(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake-env-key")
    client = LLMClient(provider="openai")
    assert client.active is True
    assert client.provider == "openai"


def test_simulated_structured_call_is_schema_valid():
    client = LLMClient()
    data = client.call_structured('User query: "best laptop for ollama"', QueryExpansionOutput)
    validated = QueryExpansionOutput.model_validate(data)
    assert len(validated.queries) >= 5


def test_extract_json_strips_markdown_fences():
    assert _extract_json('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert _extract_json('Here you go:\n{"a": 1}\nHope that helps!') == '{"a": 1}'
    assert _extract_json('[1, 2]') == '[1, 2]'
