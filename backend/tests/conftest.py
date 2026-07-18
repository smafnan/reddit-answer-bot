import os
import sys
import tempfile

# Make backend modules importable and point report storage at a temp dir
# BEFORE any backend module is imported.
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BACKEND_DIR)
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="reddit-intel-test-"))

import pytest  # noqa: E402

LLM_ENV_KEYS = ["GROQ_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Force deterministic simulated mode: no ambient API keys, no admin token."""
    for key in LLM_ENV_KEYS + ["ADMIN_TOKEN"]:
        monkeypatch.delenv(key, raising=False)


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    import main

    return TestClient(main.app)
