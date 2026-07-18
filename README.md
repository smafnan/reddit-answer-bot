# Reddit Intelligence Engine

[![CI](https://github.com/smafnan/reddit-answer-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/smafnan/reddit-answer-bot/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.139%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react)](https://react.dev)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A multi-agent system that synthesizes community consensus from Reddit discussions. Ask any question and get an intelligence report — perspectives, fact-checks, contradictions, an entity graph, and a confidence-scored synthesis.

---

## Pipeline Architecture

Seven agents run as a compiled **LangGraph** `StateGraph`. The three analysis agents execute as a **parallel fan-out** in a single superstep, then fan back in to the synthesizer:

```
query_expansion → retrieval → spam_filtering ─┬─ perspective_extraction ─┐
                                              ├─ knowledge_graph_builder ├─→ synthesizer
                                              └─ fact_checking ──────────┘
```

| # | Agent | Function |
|---|-------|----------|
| 1 | **Query Expansion** | Generates 6–10 search angles covering multiple perspectives |
| 2 | **Reddit Retrieval** | Fetches comments via PRAW → DuckDuckGo → old.reddit scraping → mock fallback |
| 3 | **Spam & Quality Filter** | 2-stage: fast heuristics, then batched LLM evaluation |
| 4 | **Perspective Analysis** ⚡ | Extracts competing viewpoints and contradictions *(parallel)* |
| 5 | **Knowledge Graph** ⚡ | Maps entities and relationships into a semantic network *(parallel)* |
| 6 | **Fact-Check** ⚡ | Verifies claims against live web search *(parallel)* |
| 7 | **Consensus Synthesis** | Combines all outputs into a confidence-scored report |

Every LLM response is validated against a Pydantic schema; scraped content is delimited as untrusted data in prompts to resist prompt injection; a failed agent degrades gracefully instead of aborting the run.

---

## Features

- **Real LangGraph orchestration** with a parallel analysis fan-out and SSE progress streaming
- **Live knowledge graph** — interactive, force-directed, dependency-free
- **Three themes** — Dark, Light, and a full **Windows 98 desktop** simulation
- **Bring-your-own-key or server keys** — Groq, Gemini, OpenAI, Anthropic, or any OpenAI-compatible endpoint; keys travel in the POST body, never in URLs
- **Honest demo mode** — without any API key, the engine returns clearly-labelled simulated sample data (badged in the UI; fact-checks are marked `[Demo sample]` and never fabricate verification verdicts)
- **Hardened API** — per-IP rate limiting, input length caps, exact-ID report operations, optional admin token for destructive endpoints

---

## Quick Start

### Backend

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.template .env      # optional: add a GROQ_API_KEY (or Gemini/OpenAI/Anthropic)
python main.py             # serves http://localhost:8000
```

Server-side keys in `.env` are picked up automatically; users can also paste a key in the UI, which overrides the server key for that request. With no key at all, the engine runs in labelled demo mode.

### Frontend

```bash
cd frontend
npm install
npm run dev                # opens http://localhost:5173
```

### Tests

```bash
pip install -r backend/requirements-dev.txt
python -m pytest backend/tests -v
```

The suite runs entirely offline (simulated mode) and is enforced in CI along with frontend lint + build.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `POST` | `/api/query` | SSE stream of agent progress → final report. Body: `{q, api_key?, provider?, model?}` |
| `POST` | `/api/query-sync` | Same pipeline, single JSON response |
| `GET` | `/api/query?q=…` | Streaming demo variant for curl (server keys / demo mode only — **no** `api_key` param by design) |
| `GET` | `/api/reports` | List saved report summaries |
| `GET` | `/api/reports/{id}` | Get a report (exact ID match) |
| `DELETE` | `/api/reports/{id}` | Delete a report (requires `X-Admin-Token` if `ADMIN_TOKEN` is set) |
| `DELETE` | `/api/reports` | Delete all reports (same admin guard) |

```bash
curl -N -X POST http://localhost:8000/api/query \
  -H 'Content-Type: application/json' \
  -d '{"q": "Is a CS degree worth it?"}'
```

Streamed events: `{"step": "<node>", "status": "running|done", "message", "details"}` per agent, then `{"step": "completed", "data": {…report…}}`. The report includes `llm_mode: "live" | "simulated"` so clients can badge demo data.

---

## Configuration

All variables are optional (see `backend/.env.template`):

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` / `GEMINI_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | Server-side LLM keys; first one found is used when a request doesn't supply its own |
| `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` | Enables PRAW retrieval (otherwise DuckDuckGo + reddit `.json` fallback) |
| `RATE_LIMIT` | Query rate limit per client IP, e.g. `20/60` (20 requests / 60 s) |
| `ADMIN_TOKEN` | If set, destructive report endpoints require this in `X-Admin-Token` |
| `DATA_DIR` | Report storage directory (auto-falls back to the OS temp dir on read-only hosts) |
| `PORT` | Server port (default 8000) |

---

## Deployment

### Option A — All on Netlify (demo)

The backend runs as a Netlify Function via Mangum. Serverless constraints apply: the function filesystem is read-only (reports persist to `/tmp`, which is ephemeral) and the free tier has a ~10 s timeout — fine for demo mode, tight for live LLM runs. The frontend auto-detects production and uses the one-shot `/api/query-sync` endpoint.

| Setting | Value |
|---------|-------|
| Build command | *(from `netlify.toml`)* |
| Publish directory | `frontend/dist` |
| Functions directory | `netlify/functions` |
| Env vars | `GROQ_API_KEY` (optional — enables live analysis server-side) |

### Option B — Frontend on Netlify, backend on Render (recommended for live use)

Render has no request timeout and a persistent-enough disk for report storage.

1. [dashboard.render.com](https://dashboard.render.com) → **New +** → **Web Service** → connect this repo
2. Root directory `backend`, build `pip install -r requirements.txt`, start `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. Add env var `GROQ_API_KEY` (and optionally `ADMIN_TOKEN`)
4. In Netlify, set `VITE_API_URL` to your Render URL

> Render's free tier spins down after inactivity; the first request after idle takes ~30 s.

---

## Tech Stack

**Backend** — FastAPI · LangGraph (compiled StateGraph, parallel supersteps) · Groq / Gemini / OpenAI / Anthropic SDKs · PRAW · DuckDuckGo Search · Pydantic-validated structured outputs

**Frontend** — React 19 + TypeScript · Vite · custom force-directed physics graph (no chart libraries) · CSS-only theming

---

## License

MIT — see [LICENSE](LICENSE).
