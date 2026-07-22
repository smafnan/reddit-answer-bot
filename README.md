# Reddit Answers

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.139%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react)](https://react.dev)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**Ask anything and get a direct answer grounded only in real Reddit discussion — with citations.**

Reddit Answers is a chat/search engine that works out what you actually mean (like a good search engine), reads the relevant Reddit threads, and answers from them — quoting specific comments. When Reddit doesn't clearly cover something, it says so instead of guessing.

```
you: is the rtx 4080 worth it for 1440p?
→  understands intent, searches Reddit, reads threads
←  "For 1440p, owners overwhelmingly say the 4080 is plenty [1]; the 4090 is
    only worth it for 4K or heavy ML [2]. A minority regret the price vs a
    4070 Ti Super [3]."   + the 3 Reddit comments it cited
```

---

## How it works

Three steps, run as a compiled LangGraph pipeline and streamed to the UI:

```
understand ──► retrieve ──► answer
(intent +      (real Reddit  (grounded answer with [n] citations,
 query plan)    via API)      or an honest refusal)
```

1. **Understand** — one LLM call turns your message (and prior turns) into an explicit information need: it resolves follow-ups ("is the cheaper one any good?" → the specific thing you meant), classifies the question, and writes 3–6 Reddit-optimized search queries plus likely subreddits.
2. **Retrieve** — searches the **official Reddit API** (read-only) across those queries, pulls the top comments from the strongest threads, and normalizes them.
3. **Rank & answer** — a deterministic ranker (relevance + upvotes + cross-query agreement + recency, with near-duplicate removal) builds a small numbered evidence pack; a second LLM call answers using **only** that pack, and every factual sentence must cite `[n]`.

### The honesty guarantee

Two deterministic checks — not the LLM's goodwill — make "grounded in Reddit" real:

- A **coverage gate** refuses before spending an LLM call when there aren't enough relevant comments, and gives *distinct* honest messages for "no coverage", "couldn't reach Reddit (retry)", and "no credentials configured".
- A **citation validator** runs after the answer: any `[n]` that doesn't map to a real retrieved comment downgrades the whole answer to an honest refusal. The model literally cannot cite a source that isn't there.

Scraped comment text is always wrapped as untrusted data in prompts, so a comment can't inject instructions.

---

## What you need to run it

**One LLM key. That's it.** Set any of NVIDIA (free, OpenAI-compatible), Groq, Gemini, OpenAI, or Anthropic — in `backend/.env` or pasted into the app's Settings (sent only in the POST body). Without a key the engine runs in clearly-labelled **demo mode** (sample answers for a few topics, honest refusals otherwise — it never fabricates sources).

**Reddit access needs no credentials by default.** The engine reads public Reddit directly — `search.rss` for thread discovery and `old.reddit.com` for comments, both of which still respond to unauthenticated clients (the JSON API is 403'd). This path is polite and low-volume (spaced requests, caching, backoff) and is best-effort: it can be rate-limited under load, and some datacenter IPs are blocked by Reddit.

**Optional upgrade:** add a free Reddit "script" app ([reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) → type **script**, redirect URI `http://localhost:8080`) as `REDDIT_CLIENT_ID`/`REDDIT_CLIENT_SECRET` (or in Settings). When present, retrieval uses the official Reddit API (PRAW, read-only) — faster, higher-volume, and more reliable, especially on cloud hosts.

---

## Quick start

**Backend**
```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.template .env      # add one LLM key (NVIDIA free / Groq / Gemini / OpenAI / Anthropic)
python main.py             # http://localhost:8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev                # http://localhost:5173
```

**Tests** (offline, no network/keys — enforced in CI)
```bash
pip install -r backend/requirements-dev.txt
python -m pytest backend/tests -v
```

---

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | SSE stream of `understand → retrieve → answer`, then the answer. Body: `{messages, api_key?, provider?, model?, reddit?}` |
| `POST` | `/api/chat-sync` | Same pipeline, one JSON response (used in production) |
| `GET` | `/api/chat-sync?q=…` | curl/demo variant — **no** secrets accepted in the query string |
| `GET` | `/api/reports` | Conversation history (summaries) |
| `GET`/`DELETE` | `/api/reports/{id}` | Get / delete by exact ID (delete needs `X-Admin-Token` if `ADMIN_TOKEN` set) |

```bash
curl -N -X POST http://localhost:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"Is a CS degree worth it?"}]}'
```

The answer object includes `grounded`, `tldr`, `answer_markdown` (with `[n]` markers), `citations[]` (comment-level permalinks + verbatim snippets), `sources[]`, `suggested_followups[]`, `intent`, `retrieval_status`, and `llm_mode` (`live`/`simulated`).

Secrets travel in the POST body only. Endpoints are rate-limited per IP.

---

## Tech stack

**Backend** — FastAPI · LangGraph · public Reddit retrieval (search.rss + old.reddit) with optional official API (PRAW, read-only) · NVIDIA / Groq / Gemini / OpenAI / Anthropic · Pydantic-validated structured outputs · deterministic ranking & citation validation (no vector DB, no heavy deps)

**Frontend** — React 19 + TypeScript · Vite · streaming chat UI with citation chips, source cards, honest-refusal cards, and follow-ups · dark/light themes

---

## License

MIT — see [LICENSE](LICENSE).
