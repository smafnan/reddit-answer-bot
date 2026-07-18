"""Tests for report persistence, including exact-ID matching regressions."""

import storage


def _make_report(report_id: str, query: str = "test query"):
    return {
        "id": report_id,
        "query": query,
        "timestamp": "2026-07-18T00:00:00+00:00",
        "llm_mode": "simulated",
        "synthesis": {"consensus_summary": "summary " * 40, "confidence_score": 0.5},
    }


def test_save_and_get_exact_id():
    report = _make_report("11111111-aaaa-bbbb-cccc-000000000001")
    assert storage.save_report(report) is not None
    fetched = storage.get_report(report["id"])
    assert fetched is not None
    assert fetched["id"] == report["id"]


def test_get_by_id_prefix_fails():
    # Regression: the old lookup matched report_id[:8] as a filename substring,
    # so a prefix (or a single letter) could return the wrong report.
    report = _make_report("22222222-aaaa-bbbb-cccc-000000000002")
    storage.save_report(report)
    assert storage.get_report("22222222") is None
    assert storage.get_report("2") is None


def test_delete_requires_exact_id():
    report = _make_report("33333333-aaaa-bbbb-cccc-000000000003")
    storage.save_report(report)
    assert storage.delete_report("3") is False
    assert storage.get_report(report["id"]) is not None
    assert storage.delete_report(report["id"]) is True
    assert storage.get_report(report["id"]) is None


def test_list_reports_summary_shape():
    report = _make_report("44444444-aaaa-bbbb-cccc-000000000004", query="listing test")
    storage.save_report(report)
    summaries = storage.list_reports()
    entry = next(s for s in summaries if s["id"] == report["id"])
    assert entry["query"] == "listing test"
    assert "confidence_score" in entry
    assert len(entry["consensus_summary"]) <= 181
