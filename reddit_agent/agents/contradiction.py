from agents.llm import llm_call


def detect_contradictions(query: str, posts: list) -> dict:
    """Detect contradictory viewpoints across Reddit posts."""
    if not posts:
        return {"has_contradictions": False, "viewpoints": [], "consensus": "No data available"}

    posts_text = ""
    for i, p in enumerate(posts):
        posts_text += f"\n[Post {i}] Title: {p['title']}\n    Text: {p['text'][:300]}\n    Subreddit: {p['subreddit']}\n"

    system = """You are a contradiction analyst. Analyze Reddit posts about a topic and identify different viewpoints.

Return a JSON object:
{
  "has_contradictions": true/false,
  "viewpoints": [
    {"stance": "positive", "percentage": 60, "summary": "Most say...", "post_indices": [0, 2]},
    {"stance": "negative", "percentage": 25, "summary": "Some warn that...", "post_indices": [1]},
    {"stance": "nuanced", "percentage": 15, "summary": "A few say it depends on...", "post_indices": [3]}
  ],
  "consensus": "Overall, the community leans toward...",
  "confidence": "high/medium/low"
}

Percentages should add up to ~100."""

    user = f"""Question: {query}

Posts:
{posts_text}

Analyze contradictions and return JSON."""

    result = llm_call(system, user, max_tokens=1000, temperature=0.2)
    try:
        import json
        return json.loads(result.strip())
    except:
        return {"has_contradictions": False, "viewpoints": [], "consensus": "Could not analyze contradictions", "confidence": "low"}
