from agents.llm import llm_call


def summarize_findings(query: str, posts: list, contradictions: dict) -> dict:
    """Create structured summary of Reddit findings."""
    posts_text = ""
    for i, p in enumerate(posts[:8]):
        posts_text += f"\n[Post {i}] (Credibility: {p.get('credibility', 'N/A')}/10) {p['title']}\n"
        posts_text += f"    Subreddit: {p['subreddit']}\n"
        posts_text += f"    Text: {p['text'][:300]}\n"

    system = """You are a Reddit research synthesizer. Create a structured findings report.

Return a JSON object:
{
  "consensus": "Overall what Reddit says about this topic in 2-3 sentences",
  "key_insights": ["Insight 1", "Insight 2", "Insight 3"],
  "positive_points": ["Point 1", "Point 2"],
  "negative_points": ["Point 1", "Point 2"],
  "recommendations": ["Recommendation 1", "Recommendation 2"],
  "caveats": ["Important caveats or warnings"],
  "confidence": "high/medium/low",
  "conflicting_views": ["View A", "View B"]
}"""

    user = f"""Question: {query}

Contradiction analysis: {contradictions.get('consensus', 'N/A')}

Reddit posts:
{posts_text}

Create structured findings JSON."""

    result = llm_call(system, user, max_tokens=1200, temperature=0.2)
    try:
        import json
        return json.loads(result.strip())
    except:
        return {"consensus": "Could not synthesize", "key_insights": [], "confidence": "low"}
