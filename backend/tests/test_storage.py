"""Tests for conversation persistence, including exact-ID matching regressions."""

import storage


def _make_record(record_id: str, query: str = "test query"):
    return {
        "id": record_id,
        "conversation_id": "conv-" + record_id,
        "query": query,
        "timestamp": "2026-07-22T00:00:00+00:00",
        "llm_mode": "simulated",
        "grounded": True,
        "tldr": "A short grounded answer. " * 20,
        "answer_markdown": "Full answer [1].",
    }


def test_save_and_get_exact_id():
    record = _make_record("11111111-aaaa-bbbb-cccc-000000000001")
    assert storage.save_report(record) is not None
    fetched = storage.get_report(record["id"])
    assert fetched is not None and fetched["id"] == record["id"]


def test_get_by_id_prefix_fails():
    record = _make_record("22222222-aaaa-bbbb-cccc-000000000002")
    storage.save_report(record)
    assert storage.get_report("22222222") is None
    assert storage.get_report("2") is None


def test_delete_requires_exact_id():
    record = _make_record("33333333-aaaa-bbbb-cccc-000000000003")
    storage.save_report(record)
    assert storage.delete_report("3") is False
    assert storage.get_report(record["id"]) is not None
    assert storage.delete_report(record["id"]) is True
    assert storage.get_report(record["id"]) is None


def test_list_reports_summary_shape():
    record = _make_record("44444444-aaaa-bbbb-cccc-000000000004", query="listing test")
    storage.save_report(record)
    summaries = storage.list_reports()
    entry = next(s for s in summaries if s["id"] == record["id"])
    assert entry["query"] == "listing test"
    assert "tldr" in entry and "grounded" in entry
    assert len(entry["tldr"]) <= 181
