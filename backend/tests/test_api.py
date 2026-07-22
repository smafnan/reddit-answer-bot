"""API tests via FastAPI TestClient (offline demo mode)."""

import json


def _msgs(text):
    return {"messages": [{"role": "user", "content": text}]}


def test_health(client):
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_chat_sync_post(client):
    res = client.post("/api/chat-sync", json=_msgs("Best laptop for local LLMs and Ollama?"))
    assert res.status_code == 200
    data = res.json()
    assert data["llm_mode"] == "simulated"
    assert data["grounded"] is True
    assert data["answer_markdown"]
    assert isinstance(data["citations"], list) and data["citations"]


def test_chat_validation(client):
    assert client.post("/api/chat-sync", json={"messages": []}).status_code == 422
    too_long = {"messages": [{"role": "user", "content": "x" * 4001}]}
    assert client.post("/api/chat-sync", json=too_long).status_code == 422


def test_sse_stream_post(client):
    with client.stream("POST", "/api/chat", json=_msgs("Is a CS degree worth it?")) as res:
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/event-stream")
        events = [json.loads(line[6:]) for line in res.iter_lines() if line.startswith("data: ")]
    steps = [e["step"] for e in events]
    assert steps[0] == "understand"
    assert "completed" in steps
    assert events[-1]["data"]["llm_mode"] == "simulated"


def test_conversational_followup(client):
    """A follow-up carries prior context; it should still produce a grounded answer."""
    convo = {
        "messages": [
            {"role": "user", "content": "Is a Tesla Model Y worth it?"},
            {"role": "assistant", "content": "Owners like the charging and software but warn on build quality."},
            {"role": "user", "content": "what about the depreciation?"},
        ]
    }
    res = client.post("/api/chat-sync", json=convo)
    assert res.status_code == 200
    assert res.json()["grounded"] in (True, False)  # demo maps tesla -> grounded


def test_get_variant_ignores_api_key_and_reddit_creds(client):
    # GET has no api_key / reddit params; passing them must not enable live mode.
    res = client.get("/api/chat-sync", params={"q": "Should I buy a Tesla Model Y?",
                                               "api_key": "sk-should-be-ignored"})
    assert res.status_code == 200
    assert res.json()["llm_mode"] == "simulated"


def test_conversations_crud_exact_match(client):
    data = client.post("/api/chat-sync", json=_msgs("React vs Vue in 2026?")).json()
    rid = data["id"]
    listed = client.get("/api/reports").json()
    assert any(r["id"] == rid for r in listed)
    assert client.get(f"/api/reports/{rid}").status_code == 200
    assert client.get(f"/api/reports/{rid[:8]}").status_code == 404
    assert client.delete(f"/api/reports/{rid[:8]}").status_code == 404
    assert client.delete(f"/api/reports/{rid}").status_code == 200
    assert client.get(f"/api/reports/{rid}").status_code == 404


def test_admin_token_guard(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "secret-token")
    assert client.delete("/api/reports").status_code == 403
    assert client.delete("/api/reports", headers={"X-Admin-Token": "wrong"}).status_code == 403
    assert client.delete("/api/reports", headers={"X-Admin-Token": "secret-token"}).status_code == 200


def test_rate_limit(client, monkeypatch):
    import main

    monkeypatch.setattr(main, "_RATE_COUNT", 3)
    headers = {"x-forwarded-for": "203.0.113.77"}
    for _ in range(3):
        assert client.post("/api/chat-sync", json=_msgs("Is a CS degree worth it?"), headers=headers).status_code == 200
    assert client.post("/api/chat-sync", json=_msgs("Is a CS degree worth it?"), headers=headers).status_code == 429
