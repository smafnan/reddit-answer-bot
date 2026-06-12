import json
from agents.llm import llm_call


def detect_contradictions(query: str, posts: list) -> dict:
    if not posts:
        return {"has_contradictions": False, "viewpoints": [], "consensus": "No data available", "confidence": "low"}

    posts_text = ""
    for i, p in enumerate(posts):
        posts_text += f"\n[Post {i}] Title: {p['title']}\n    Text: {p.get('text', '')[:400]}\n    Credibility: {p.get('credibility', 'N/A')}/10\n    Subreddit: {p.get('subreddit', '')}\n"

    system = """You are a contradiction analyst. Analyze posts about a topic and identify different viewpoints.

Return a JSON object:
{
  "has_contradictions": true/false,
  "viewpoints": [
    {"stance": "positive", "percentage": 60, "summary": "Most say...", "post_indices": [0, 2]},
    {"stance": "negative", "percentage": 25, "summary": "Some warn that..."},
    {"stance": "nuanced", "percentage": 15, "summary": "A few say it depends..."}
  ],
  "consensus": "Overall, the community leans toward...",
  "confidence": "high/medium/low"
}"""

    user = f"""Question: {query}

Posts:
{posts_text}

Analyze contradictions and return JSON."""

    result = llm_call(system, user, max_tokens=1000, temperature=0.2)
    if not result:
        return {"has_contradictions": False, "viewpoints": [{"stance": "general", "percentage": 100, "summary": "Consensus not analyzed"}], "consensus": "Proceed with general findings", "confidence": "low"}
    try:
        return json.loads(result.strip())
    except:
        return {"has_contradictions": False, "viewpoints": [], "consensus": "Could not analyze contradictions", "confidence": "low"}
