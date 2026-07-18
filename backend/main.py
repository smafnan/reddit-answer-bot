"""FastAPI application for the Reddit Intelligence Engine.

Security notes:
- API keys travel in the POST body (never in URL query strings, which end up
  in access logs and browser history).
- Query endpoints are rate-limited per client IP (configurable via RATE_LIMIT,
  e.g. "20/60" = 20 requests per 60 seconds).
- If the ADMIN_TOKEN env var is set, destructive report endpoints require an
  ``X-Admin-Token`` header. Unset (local dev), they remain open.
"""

import json
import logging
import os
import threading
import time
from collections import defaultdict, deque
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

import storage
from graph import RedditIntelligencePipeline

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Reddit Intelligence Engine API",
    description="A multi-agent system that synthesizes community consensus from Reddit discussions.",
)

# CORS: wildcard origins are fine for a public, credential-less API.
# (allow_credentials must stay False with a wildcard origin.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------- rate limiting

def _parse_rate_limit() -> tuple:
    raw = os.environ.get("RATE_LIMIT", "20/60")
    try:
        count, window = raw.split("/")
        return max(1, int(count)), max(1, int(window))
    except ValueError:
        return 20, 60


_RATE_COUNT, _RATE_WINDOW = _parse_rate_limit()
_rate_buckets = defaultdict(deque)
_rate_lock = threading.Lock()


def enforce_rate_limit(request: Request):
    client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else "unknown"
    )
    now = time.monotonic()
    with _rate_lock:
        bucket = _rate_buckets[client_ip]
        while bucket and now - bucket[0] > _RATE_WINDOW:
            bucket.popleft()
        if len(bucket) >= _RATE_COUNT:
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait and try again.")
        bucket.append(now)


# ------------------------------------------------------------------ auth guard

def require_admin(x_admin_token: Optional[str]):
    expected = os.environ.get("ADMIN_TOKEN")
    if expected and x_admin_token != expected:
        raise HTTPException(status_code=403, detail="Admin token required for this operation.")


# -------------------------------------------------------------------- schemas

class QueryRequest(BaseModel):
    q: str = Field(min_length=3, max_length=500, description="The user question to research")
    api_key: Optional[str] = Field(default=None, max_length=500, description="LLM provider API key (optional; falls back to server env keys, then demo mode)")
    provider: Optional[str] = Field(default=None, max_length=50, description="LLM provider (groq, gemini, openai, anthropic, or OpenAI-compatible)")
    model: Optional[str] = Field(default=None, max_length=100, description="Model name override")


# ------------------------------------------------------------------ endpoints

@app.get("/")
def read_root():
    return {"status": "healthy", "service": "Reddit Intelligence Engine API"}


def _sse_stream(pipeline: RedditIntelligencePipeline):
    def event_generator():
        try:
            for step_update in pipeline.run():
                yield f"data: {json.dumps(step_update)}\n\n"
        except Exception as exc:  # never let a stream die silently
            logger.exception("Unhandled error in SSE stream")
            yield f"data: {json.dumps({'step': 'failed', 'message': 'Internal error.', 'details': str(exc)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def _run_sync(pipeline: RedditIntelligencePipeline):
    report_data = None
    for step_update in pipeline.run():
        if step_update["step"] == "completed":
            report_data = step_update["data"]
        elif step_update["step"] == "failed":
            raise HTTPException(status_code=500, detail=step_update.get("details", "Pipeline failed"))
    if report_data is None:
        raise HTTPException(status_code=500, detail="Pipeline did not produce a report")
    return report_data


@app.post("/api/query")
def stream_query(body: QueryRequest, request: Request):
    """Streams multi-agent execution progress and the final report via SSE."""
    enforce_rate_limit(request)
    logger.info("Received streaming query request: %s", body.q)
    pipeline = RedditIntelligencePipeline(body.q, api_key=body.api_key, provider=body.provider, model=body.model)
    return _sse_stream(pipeline)


@app.post("/api/query-sync")
def query_sync(body: QueryRequest, request: Request):
    """Runs the full pipeline and returns the report as a single JSON response."""
    enforce_rate_limit(request)
    logger.info("Received sync query request: %s", body.q)
    pipeline = RedditIntelligencePipeline(body.q, api_key=body.api_key, provider=body.provider, model=body.model)
    return _run_sync(pipeline)


@app.get("/api/query")
def stream_query_get(
    request: Request,
    q: str = Query(..., min_length=3, max_length=500, description="The user question to research"),
    provider: Optional[str] = Query(default=None, max_length=50),
    model: Optional[str] = Query(default=None, max_length=100),
):
    """GET variant for curl / simple demos. Deliberately accepts NO api_key —
    keys must never travel in a query string. Uses server env keys or demo mode."""
    enforce_rate_limit(request)
    logger.info("Received GET streaming query request: %s", q)
    pipeline = RedditIntelligencePipeline(q, provider=provider, model=model)
    return _sse_stream(pipeline)


@app.get("/api/query-sync")
def query_sync_get(
    request: Request,
    q: str = Query(..., min_length=3, max_length=500, description="The user question to research"),
    provider: Optional[str] = Query(default=None, max_length=50),
    model: Optional[str] = Query(default=None, max_length=100),
):
    """GET variant for curl / simple demos (no api_key accepted — see above)."""
    enforce_rate_limit(request)
    logger.info("Received GET sync query request: %s", q)
    pipeline = RedditIntelligencePipeline(q, provider=provider, model=model)
    return _run_sync(pipeline)


@app.get("/api/reports")
def list_reports():
    """Lists summaries of all previously generated and saved reports."""
    return storage.list_reports()


@app.get("/api/reports/{report_id}")
def get_report(report_id: str):
    """Retrieves a single full saved report by its exact ID."""
    report = storage.get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@app.delete("/api/reports")
def clear_all_reports(x_admin_token: Optional[str] = Header(default=None)):
    """Deletes all saved reports (requires X-Admin-Token if ADMIN_TOKEN is set)."""
    require_admin(x_admin_token)
    deleted = storage.delete_all_reports()
    return {"status": "success", "message": f"Deleted {deleted} report(s)"}


@app.delete("/api/reports/{report_id}")
def delete_report(report_id: str, x_admin_token: Optional[str] = Header(default=None)):
    """Deletes a single report by its exact ID (requires X-Admin-Token if ADMIN_TOKEN is set)."""
    require_admin(x_admin_token)
    if not storage.delete_report(report_id):
        raise HTTPException(status_code=404, detail="Report not found")
    return {"status": "success", "message": f"Report {report_id} deleted"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
