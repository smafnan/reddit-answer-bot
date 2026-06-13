# Reddit Intelligence Engine - Setup & Troubleshooting Guide

## Overview

This multi-agent system analyzes Reddit discussions to synthesize community consensus on any topic. It features:

- **Query Expansion Agent**: Generates 8-10 alternative search angles
- **Retrieval Agent**: Fetches Reddit comments via PRAW, DuckDuckGo, or scraping
- **Spam Filter Agent**: Removes low-quality/bot comments
- **Perspective Agent**: Extracts competing viewpoints
- **Knowledge Graph Agent**: Maps entity relationships
- **Fact-Check Agent**: Verifies claims against web sources
- **Synthesis Agent**: Creates final intelligence report

## Prerequisites

- Python 3.8+
- pip (Python package manager)

## Installation

### Step 1: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

**Required packages:**
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `langgraph` - Agent workflow orchestration
- `google-generativeai` - Gemini LLM (or use Groq as fallback)
- `groq` - Groq LLM (optional fallback)
- `praw` - Reddit API client (optional, has fallbacks)
- `duckduckgo-search` - Web search
- `requests` - HTTP client
- `python-dotenv` - Environment configuration
- `pydantic` - Data validation

### Step 2: Configure Environment

Copy `.env.template` to `.env` and fill in your API keys:

```bash
cp .env.template .env
```

Edit `.env`:

```
# REQUIRED: Choose at least one LLM API key

# Option A: Google Gemini (Recommended - free tier available)
GEMINI_API_KEY=your_gemini_api_key_here

# Option B: Groq (Free alternative)
GROQ_API_KEY=your_groq_api_key_here

# OPTIONAL: Reddit API (if omitted, system uses DuckDuckGo + scraping fallback)
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=reddit-intel-engine-v1.0

# Server Configuration
PORT=8000
```

### How to Get API Keys

#### Google Gemini API (Free)
1. Go to https://aistudio.google.com/app/apikeys
2. Click "Create API Key"
3. Copy your key and add to `.env` as `GEMINI_API_KEY`

#### Groq API (Free)
1. Go to https://console.groq.com
2. Sign up and create an API key
3. Add to `.env` as `GROQ_API_KEY`

#### Reddit API (Optional)
1. Go to https://www.reddit.com/prefs/apps
2. Create an app (type: "script")
3. Get `client_id` and `client_secret`
4. Add to `.env`

---

## Running the Server

### Start the FastAPI server:

```bash
python main.py
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Test in another terminal:

```bash
curl "http://localhost:8000/"
```

Should return:
```json
{"status": "healthy", "service": "Reddit Intelligence Engine API"}
```

---

## Testing

### Run the full test suite:

```bash
python test_full_pipeline.py
```

This tests:
- ✓ All imports
- ✓ Query expansion
- ✓ Reddit retrieval
- ✓ Individual agents
- ✓ Full end-to-end pipeline

---

## API Usage

### Query Analysis

```bash
curl -N "http://localhost:8000/api/query?q=Is%20a%20CS%20degree%20worth%20it?"
```

**Response**: Server-Sent Events (SSE) stream with real-time progress:

```json
{"step": "query_expansion", "message": "Generating alternative search angles...", ...}
{"step": "retrieval", "message": "Querying Reddit discussions...", ...}
{"step": "spam_filtering", "message": "Evaluating credibility...", ...}
...
{"step": "completed", "message": "Synthesis complete!", "data": {...full report...}}
```

### List Reports

```bash
curl "http://localhost:8000/api/reports"
```

### Get Specific Report

```bash
curl "http://localhost:8000/api/reports/{report_id}"
```

### Delete Report

```bash
curl -X DELETE "http://localhost:8000/api/reports/{report_id}"
```

### Clear All Reports

```bash
curl -X DELETE "http://localhost:8000/api/reports"
```

---

## Troubleshooting

### Error: `ModuleNotFoundError: No module named 'google'`

**Solution:**
```bash
pip install google-generativeai
```

### Error: `ModuleNotFoundError: No module named 'requests'`

**Solution:**
```bash
pip install requests
```

### Error: `No GEMINI_API_KEY or GOOGLE_API_KEY found`

The system will fall back to **simulated responses** (pre-generated topic-specific data). This is useful for testing without API keys, but quality is limited to predefined topics.

**To use live API:**
1. Set `GEMINI_API_KEY` in `.env`
2. Restart the server
3. Log messages will show `"Initialized Google GenerativeAI client successfully"`

### Error: `PRAW search failed, falling back to DDG + old.reddit scraping`

This is **normal and expected** if Redis credentials aren't set up. The system automatically falls back to:
1. DuckDuckGo web search (`site:reddit.com`)
2. old.reddit.com JSON scraping (no rate limits)

If both fail, the system uses **mock comments** (pre-generated realistic data).

### Error: `Fact-check step failed`

This happens when DuckDuckGo search fails. The fact-check agent still includes the claim but marks it as "Unverified".

### Port Already in Use

Change the port in `.env`:
```
PORT=8001
```

Or kill the process:
```bash
# On Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# On Mac/Linux
lsof -i :8000
kill -9 <PID>
```

---

## Performance Notes

**Without API Keys (Fallback Mode)**
- Response time: ~2-5 seconds
- Quality: Pre-generated topic-specific data
- Best for: Testing, development, demo

**With Gemini API**
- Response time: ~15-30 seconds (includes web search)
- Quality: High (real Reddit + LLM synthesis)
- Cost: Free tier includes 60 requests/minute

**With Reddit API**
- Retrieval is faster (direct API calls vs. web scraping)
- Better reliability
- Requires approval from Reddit

---

## Architecture Explanation

### Data Flow

```
User Query
    ↓
[1] Query Expansion (8-10 search angles)
    ↓
[2] Retrieval (PRAW → DuckDuckGo → old.reddit scraping)
    ↓
[3] Spam Filter (remove bots, low-effort, deleted)
    ↓
[4] Perspective Extraction (group by viewpoints, find contradictions)
    ↓
[5] Knowledge Graph (map entities and relationships)
    ↓
[6] Fact-Checking (verify claims via web search)
    ↓
[7] Consensus Synthesis (combine all insights into report)
    ↓
Final Intelligence Report (JSON)
```

### Agent Responsibilities

| Agent | Input | Output | Fallback |
|-------|-------|--------|----------|
| Query Expansion | User query | 8-10 search angles | Uses original query only |
| Retrieval | Expanded queries | Reddit comments | Mock comments or snippets |
| Spam Filter | Raw comments | High-quality comments | Heuristic scoring (length + upvotes) |
| Perspective | Quality comments | User segments + contradictions | Simulated perspectives |
| Knowledge Graph | Comments | Entities + relationships | Basic nodes (Topic, Alternative, Cost) |
| Fact-Check | Comments | Verified/Disputed claims | Marked as "Unverified" |
| Synthesis | All above data | Final report | Simulated summary |

---

## Development Tips

### Run a Single Query Manually

```python
python
>>> from graph import RedditIntelligencePipeline
>>> pipeline = RedditIntelligencePipeline("best laptop for AI?")
>>> for step in pipeline.run():
...     print(step['step'], step['message'])
```

### Enable Debug Logging

Edit `main.py`:
```python
logging.basicConfig(level=logging.DEBUG)
```

### Test Specific Agent

```python
from agents import query_expansion_agent
queries = query_expansion_agent("Is a CS degree worth it?")
print(queries)
```

---

## Production Deployment

### Using Gunicorn (Recommended)

```bash
pip install gunicorn
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Using Docker

Create `Dockerfile`:
```dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

Build and run:
```bash
docker build -t reddit-intel .
docker run -p 8000:8000 --env-file .env reddit-intel
```

---

## Support & Contribution

- **Issues**: GitHub Issues
- **Feature Requests**: Discussions or PRs
- **API Improvements**: Extend agents with custom logic in `agents.py`

---

## License

MIT License - See LICENSE file

