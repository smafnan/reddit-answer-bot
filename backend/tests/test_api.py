"""API tests via FastAPI TestClient (simulated mode, no network)."""

import json


def test_health(client):
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_query_sync_post(client):
    res = client.post("/api/query-sync", json={"q": "Best laptop for local LLMs and Ollama?"})
    assert res.status_code == 200
    report = res.json()
    assert report["llm_mode"] == "simulated"
    assert report["synthesis"]["consensus_summary"]
    assert isinstance(report["facts_checked"], list)


def test_query_validation(client):
    assert client.post("/api/query-sync", json={"q": "hi"}).status_code == 422  # too short
    assert client.post("/api/query-sync", json={"q": "x" * 501}).status_code == 422  # too long


def test_sse_stream_post(client):
    with client.stream("POST", "/api/query", json={"q": "Is a CS degree worth it?"}) as res:
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/event-stream")
        events = []
        for line in res.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[len("data: "):]))
    steps = [e["step"] for e in events]
    assert steps[0] == "query_expansion"
    assert "completed" in steps
    assert events[-1]["data"]["llm_mode"] == "simulated"


def test_get_query_rejects_api_key_leak(client):
    # The GET endpoints deliberately have no api_key parameter; passing one is
    # simply ignored and never reaches the pipeline or the logs as a credential.
    res = client.get("/api/query-sync", params={"q": "Should I buy a Tesla Model Y?", "api_key": "sk-should-be-ignored"})
    assert res.status_code == 200
    assert res.json()["llm_mode"] == "simulated"


def test_reports_crud_exact_match(client):
    report = client.post("/api/query-sync", json={"q": "React vs Vue in 2026 tech stack choices"}).json()
    report_id = report["id"]

    listed = client.get("/api/reports").json()
    assert any(r["id"] == report_id for r in listed)

    assert client.get(f"/api/reports/{report_id}").status_code == 200
    assert client.get(f"/api/reports/{report_id[:8]}").status_code == 404  # prefix must NOT match

    assert client.delete(f"/api/reports/{report_id[:8]}").status_code == 404
    assert client.delete(f"/api/reports/{report_id}").status_code == 200
    assert client.get(f"/api/reports/{report_id}").status_code == 404


def test_admin_token_protects_destructive_endpoints(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "secret-token")
    assert client.delete("/api/reports").status_code == 403
    assert client.delete("/api/reports", headers={"X-Admin-Token": "wrong"}).status_code == 403
    assert client.delete("/api/reports", headers={"X-Admin-Token": "secret-token"}).status_code == 200


def test_rate_limit(client, monkeypatch):
    import main

    monkeypatch.setattr(main, "_RATE_COUNT", 3)
    headers = {"x-forwarded-for": "203.0.113.99"}
    for _ in range(3):
        assert client.post("/api/query-sync", json={"q": "Is a CS degree worth it?"}, headers=headers).status_code == 200
    assert client.post("/api/query-sync", json={"q": "Is a CS degree worth it?"}, headers=headers).status_code == 429
