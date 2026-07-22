"""FastAPI app for the Reddit Answer Engine — ask anything, answered from Reddit.

Security posture (kept from v2):
- Secrets (LLM key, Reddit client id/secret) travel ONLY in the POST body,
  never in URL query strings (which land in access logs and browser history).
- Query endpoints are rate-limited per client IP (RATE_LIMIT, e.g. "20/60").
- If ADMIN_TOKEN is set, destructive conversation endpoints require X-Admin-Token.
"""

import json
import logging
import os
import threading
import time
from collections import defaultdict, deque
from typing import List, Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

import storage
from graph import RedditAnswerEngine

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Reddit Answer Engine API",
    description="Ask anything and get a direct answer grounded only in real Reddit discussion.",
)

# Wildcard origins are fine for a public, credential-less API.
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


def require_admin(x_admin_token: Optional[str]):
    expected = os.environ.get("ADMIN_TOKEN")
    if expected and x_admin_token != expected:
        raise HTTPException(status_code=403, detail="Admin token required for this operation.")


# -------------------------------------------------------------------- schemas

class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class RedditCreds(BaseModel):
    client_id: str = Field(min_length=1, max_length=100)
    client_secret: str = Field(min_length=1, max_length=100)


class ChatRequest(BaseModel):
    messages: List[Message] = Field(min_length=1, max_length=20)  # last item = current user turn
    conversation_id: Optional[str] = Field(default=None, max_length=64)
    api_key: Optional[str] = Field(default=None, max_length=500)
    provider: Optional[str] = Field(default=None, max_length=50)
    model: Optional[str] = Field(default=None, max_length=100)
    reddit: Optional[RedditCreds] = None  # bring-your-own Reddit creds (POST body only)


# ------------------------------------------------------------------ endpoints

@app.get("/")
def read_root():
    return {"status": "healthy", "service": "Reddit Answer Engine API"}


def _engine_from_request(body: ChatRequest) -> RedditAnswerEngine:
    return RedditAnswerEngine(
        [m.model_dump() for m in body.messages],
        api_key=body.api_key,
        provider=body.provider,
        model=body.model,
        reddit_creds=(body.reddit.model_dump() if body.reddit else None),
        conversation_id=body.conversation_id,
    )


def _sse_stream(engine: RedditAnswerEngine):
    def event_generator():
        try:
            for step_update in engine.run():
                yield f"data: {json.dumps(step_update)}\n\n"
        except Exception as exc:
            logger.exception("Unhandled error in SSE stream")
            yield f"data: {json.dumps({'step': 'failed', 'message': 'Internal error.', 'details': str(exc)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def _run_sync(engine: RedditAnswerEngine):
    answer_data = None
    for step_update in engine.run():
        if step_update["step"] == "completed":
            answer_data = step_update["data"]
        elif step_update["step"] == "failed":
            raise HTTPException(status_code=500, detail=step_update.get("details", "Pipeline failed"))
    if answer_data is None:
        raise HTTPException(status_code=500, detail="Engine did not produce an answer")
    return answer_data


@app.post("/api/chat")
def chat_stream(body: ChatRequest, request: Request):
    """Stream understand -> search -> answer progress, then the grounded answer (SSE)."""
    enforce_rate_limit(request)
    logger.info("chat (stream): %s", body.messages[-1].content[:120])
    return _sse_stream(_engine_from_request(body))


@app.post("/api/chat-sync")
def chat_sync(body: ChatRequest, request: Request):
    """Run the full pipeline and return the grounded answer as one JSON response."""
    enforce_rate_limit(request)
    logger.info("chat (sync): %s", body.messages[-1].content[:120])
    return _run_sync(_engine_from_request(body))


def _engine_from_query(q: str, provider: Optional[str], model: Optional[str]) -> RedditAnswerEngine:
    # GET variants deliberately accept NO api_key and NO reddit creds — secrets
    # must never travel in a query string. Uses server env keys or demo mode.
    return RedditAnswerEngine([{"role": "user", "content": q}], provider=provider, model=model)


@app.get("/api/chat")
def chat_stream_get(
    request: Request,
    q: str = Query(..., min_length=3, max_length=500),
    provider: Optional[str] = Query(default=None, max_length=50),
    model: Optional[str] = Query(default=None, max_length=100),
):
    """GET streaming variant for curl/demos (no secrets accepted)."""
    enforce_rate_limit(request)
    return _sse_stream(_engine_from_query(q, provider, model))


@app.get("/api/chat-sync")
def chat_sync_get(
    request: Request,
    q: str = Query(..., min_length=3, max_length=500),
    provider: Optional[str] = Query(default=None, max_length=50),
    model: Optional[str] = Query(default=None, max_length=100),
):
    """GET one-shot variant for curl/demos (no secrets accepted)."""
    enforce_rate_limit(request)
    return _run_sync(_engine_from_query(q, provider, model))


# ---- Conversation history (kept path names /api/reports for back-compat) ----

@app.get("/api/reports")
def list_conversations():
    return storage.list_reports()


@app.get("/api/reports/{report_id}")
def get_conversation(report_id: str):
    report = storage.get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Not found")
    return report


@app.delete("/api/reports")
def clear_conversations(x_admin_token: Optional[str] = Header(default=None)):
    require_admin(x_admin_token)
    deleted = storage.delete_all_reports()
    return {"status": "success", "message": f"Deleted {deleted} item(s)"}


@app.delete("/api/reports/{report_id}")
def delete_conversation(report_id: str, x_admin_token: Optional[str] = Header(default=None)):
    require_admin(x_admin_token)
    if not storage.delete_report(report_id):
        raise HTTPException(status_code=404, detail="Not found")
    return {"status": "success", "message": f"Deleted {report_id}"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
