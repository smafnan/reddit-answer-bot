# Reddit Intelligence Engine

[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react)](https://react.dev)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![GitHub release](https://img.shields.io/badge/release-v1.0.0-blue?logo=github)](https://github.com/smafnan/reddit-answer-bot/releases/tag/v1.0.0)

A multi-agent system that synthesizes community consensus from Reddit discussions. Ask any question and get an intelligence report — complete with perspectives, fact-checks, contradictions, entity graphs, and a confidence-scored synthesis.

---

## Pipeline Architecture

The system runs **7 specialized agents** in sequence, with three agents running in parallel for maximum efficiency:

<p align="center">
  <img src="./reddit_intelligence_pipeline.svg" alt="7-Agent Pipeline Architecture" width="100%"/>
</p>

| # | Agent | Function |
|---|-------|----------|
| 1 | **Query Expansion** | Generates 8–10 search angles covering multiple perspectives |
| 2 | **Reddit Retrieval** | Fetches comments via PRAW → DuckDuckGo → Scraping → Mock fallback |
| 3 | **Spam & Quality Filter** | 2-stage heuristics + LLM evaluation; removes bots, low-effort, deleted posts |
| 4 | **Perspective Analysis** | Extracts competing viewpoints and identifies contradictions |
| 5 | **Knowledge Graph** | Maps entities and relationships into a semantic network |
| 6 | **Fact-Check** | Verifies claims against live web search; marks Verified/Disputed/Debunked |
| 7 | **Consensus Synthesis** | Combines all outputs into a unified, confidence-scored intelligence report |

---

## Features

- **7-Agent LangGraph pipeline** with real-time SSE streaming
- **Live knowledge graph** — interactive, force-directed, perpetually floating nodes
- **Three themes** — Dark Mode, Light Mode, and a nostalgic **Windows 98 desktop**
- **Fully responsive** — works on iOS, Android, tablets, and desktop
- **Collapsible panels** — collapse the sidebar and source threads for focused reading
- **Multiple retrieval backends** — PRAW, DuckDuckGo search, old.reddit.com scraping
- **Hybrid LLM support** — Groq (default) with Gemini fallback
- **Works without API keys** — falls back to intelligent simulated responses

---

## Quick Start

### Backend

```bash
cd backend
pip install -r requirements.txt

# Copy and configure environment
cp .env.template .env
# Edit .env with your API keys (Groq or Gemini)

python main.py
```

The API server starts at `http://localhost:8000`.

### Frontend

**Option A — Direct HTML (no setup):**
Just open `INTERACTIVE_UI.html` in your browser while the backend runs.

**Option B — React app:**

```bash
cd frontend
npm install
npm run dev
```

Opens at `http://localhost:5173`.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/api/query?q=QUESTION` | SSE stream of agent progress → final report |
| `GET` | `/api/reports` | List all saved reports |
| `GET` | `/api/reports/{id}` | Get a specific report |
| `DELETE` | `/api/reports/{id}` | Delete a report |
| `DELETE` | `/api/reports` | Delete all reports |

### Example query

```bash
curl -N "http://localhost:8000/api/query?q=Is%20a%20CS%20degree%20worth%20it?"
```

Returns a Server-Sent Events stream:

```
data: {"step": "query_expansion", "message": "Generating alternative search angles..."}
data: {"step": "retrieval", "message": "Querying Reddit discussions..."}
...
data: {"step": "completed", "data": { "... full report ..." }}
```

---

## Themes

The UI supports three themes selectable from the sidebar footer:

| Theme | Description |
|-------|-------------|
| **Dark Mode** | Sleek, modern dark UI with neon violet/cyan accents |
| **Light Mode** | Clean light theme with improved contrast for readability |
| **Windows 98** | Full retro desktop simulation — start menu, taskbar, window frames, classic grey palette |

> **Tip:** In Dark or Light mode, a nostalgic prompt suggests trying Windows 98 mode. Dismiss it to never see it again.

---

## Configuration

Copy `backend/.env.template` to `backend/.env` and set these optional keys:

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | No (fallback to simulated) | Groq LLM (fast, free tier available) |
| `GEMINI_API_KEY` | No | Google Gemini LLM |
| `REDDIT_CLIENT_ID` | No | Reddit API client ID |
| `REDDIT_CLIENT_SECRET` | No | Reddit API client secret |
| `PORT` | No | Server port (default: 8000) |

Without API keys, the system uses intelligent simulated responses for testing and demo.

---

## Tech Stack

**Backend**
- FastAPI + Uvicorn
- LangGraph (agent orchestration)
- Groq / Google GenerativeAI
- PRAW / DuckDuckGo-Search / Requests

**Frontend**
- React 19 + TypeScript
- Vite 8
- Custom force-directed physics graph (no external libs)
- CSS-only theming system

---

## Deployment

### Why the live site can't reach the backend

Netlify free-tier functions have a **10-second timeout** and don't support Server-Sent Events (SSE) streaming properly. The pipeline needs 2–5 seconds in simulated mode or 15–30 seconds with a real LLM. The frontend now auto-detects the environment:

| Environment | Endpoint | Behaviour |
|-------------|----------|-----------|
| `localhost` (dev) | `/api/query` (SSE) | Real-time streaming with progress steps |
| Production | `/api/query-sync` (JSON) | One-shot fetch — show report when done |

### Option A — All on Netlify (recommended for demo)

The backend runs as a Netlify Function via Mangum. Use the sync endpoint — works within the 10 s timeout for simulated mode.

**Settings:**

| Setting | Value |
|---------|-------|
| **Branch to deploy** | `main` |
| **Base directory** | *(leave empty)* |
| **Build command** | `cd frontend && npm ci && npm run build` |
| **Publish directory** | `frontend/dist` |
| **Functions directory** | `netlify/functions` |

**Environment variables** (Netlify → Site settings → Environment variables):

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | No (simulated fallback) | Get one free at [console.groq.com](https://console.groq.com) |

### Option B — Frontend on Netlify, Backend on Render (recommended for production)

Deploy the backend on [Render](https://render.com) (free tier — 512 MB RAM, no request timeout) for faster real-LLM responses without the 10 s function limit.

**Backend (Render):**

1. Go to [dashboard.render.com](https://dashboard.render.com) → **New +** → **Web Service**
2. Connect your GitHub repo (`smafnan/reddit-answer-bot`)
3. Use these settings:

| Setting | Value |
|---------|-------|
| **Name** | `reddit-intelligence-api` |
| **Branch** | `main` |
| **Root Directory** | `backend` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| **Plan** | **Free** |

4. Add environment variable: `GROQ_API_KEY` (same key from your `.env`)
5. Deploy — Render gives you a URL like `https://reddit-intelligence-api.onrender.com`

**Frontend (Netlify):**

Add an environment variable in **Netlify → Site settings → Environment variables**:

| Key | Value |
|-----|-------|
| `VITE_API_URL` | `https://reddit-intelligence-api.onrender.com` |

The frontend will read this variable and send API calls to your Render backend automatically.

> **Tip:** Render's free tier spins down after 15 minutes of inactivity. The first request after idle takes ~30 seconds to wake up. Subsequent requests are instant.

---

## License

MIT License — see [LICENSE](LICENSE).
