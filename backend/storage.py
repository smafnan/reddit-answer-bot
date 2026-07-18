"""Report persistence on the filesystem.

Resolves a writable data directory at import time: ``DATA_DIR`` env override →
``backend/data/`` → the OS temp dir (needed on serverless hosts like Netlify /
AWS Lambda, where the code bundle is read-only). Persistence failures are
never fatal — a report that can't be saved is still returned to the caller.

Lookups and deletions match report IDs exactly; the old substring matching
could return or delete the wrong report.
"""

import json
import logging
import os
import re
import tempfile
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _resolve_data_dir() -> Optional[str]:
    candidates = [
        os.environ.get("DATA_DIR"),
        os.path.join(os.path.dirname(__file__), "data"),
        os.path.join(tempfile.gettempdir(), "reddit-intel-data"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            os.makedirs(candidate, exist_ok=True)
            probe = os.path.join(candidate, ".write-probe")
            with open(probe, "w") as f:
                f.write("ok")
            os.remove(probe)
            return candidate
        except OSError:
            logger.info("Data dir %s is not writable, trying next candidate.", candidate)
    logger.warning("No writable data directory found — reports will not be persisted.")
    return None


DATA_DIR = _resolve_data_dir()


def _report_files() -> List[str]:
    if not DATA_DIR or not os.path.isdir(DATA_DIR):
        return []
    return [os.path.join(DATA_DIR, f) for f in os.listdir(DATA_DIR) if f.endswith(".json")]


def _load(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as exc:
        logger.error("Error reading report file %s: %s", path, exc)
        return None


def save_report(report: Dict[str, Any]) -> Optional[str]:
    """Persist a report. Returns the file path, or None if persistence failed."""
    if not DATA_DIR:
        return None
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", report.get("query", "").lower()).strip("-")[:60] or "query"
    path = os.path.join(DATA_DIR, f"{slug}-{report['id'][:8]}.json")
    try:
        with open(path, "w") as f:
            json.dump(report, f, indent=2)
        return path
    except OSError as exc:
        logger.warning("Could not persist report (%s) — continuing without saving.", exc)
        return None


def list_reports() -> List[Dict[str, Any]]:
    """Summaries of all saved reports, newest first."""
    reports = []
    for path in _report_files():
        data = _load(path)
        if not data:
            continue
        synthesis = data.get("synthesis", {})
        summary = synthesis.get("consensus_summary", "")
        reports.append(
            {
                "id": data.get("id"),
                "query": data.get("query"),
                "timestamp": data.get("timestamp"),
                "confidence_score": synthesis.get("confidence_score", 0.0),
                "consensus_summary": summary[:180] + ("…" if len(summary) > 180 else ""),
                "llm_mode": data.get("llm_mode", "simulated"),
            }
        )
    reports.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
    return reports


def get_report(report_id: str) -> Optional[Dict[str, Any]]:
    for path in _report_files():
        data = _load(path)
        if data and data.get("id") == report_id:
            return data
    return None


def delete_report(report_id: str) -> bool:
    for path in _report_files():
        data = _load(path)
        if data and data.get("id") == report_id:
            try:
                os.remove(path)
                return True
            except OSError as exc:
                logger.error("Could not delete report %s: %s", report_id, exc)
                return False
    return False


def delete_all_reports() -> int:
    deleted = 0
    for path in _report_files():
        try:
            os.remove(path)
            deleted += 1
        except OSError as exc:
            logger.error("Could not delete %s: %s", path, exc)
    return deleted
