import json
from agents.llm import llm_call


def summarize_findings(query: str, posts: list, contradictions: dict) -> dict:
    posts_text = ""
    for i, p in enumerate(posts[:8]):
        posts_text += f"\n[Post {i}] (Credibility: {p.get('credibility', 'N/A')}/10) {p.get('title', '')}\n"
        posts_text += f"    Subreddit: {p.get('subreddit', '')}\n"
        posts_text += f"    Text: {p.get('text', '')[:400]}\n"

    system = """You are a Reddit research synthesizer. Create a structured findings report.

Return a JSON object:
{
  "consensus": "Overall what Reddit says in 2-3 sentences",
  "confidence_score": 0.82,
  "key_insights": ["Insight 1", "Insight 2"],
  "positive_points": ["Point 1"],
  "negative_points": ["Point 1"],
  "recommendations": ["Recommendation 1"],
  "caveats": ["Caveat 1"],
  "detailed_synthesis": "## Main Headers\\n\\nDetailed markdown synthesis...",
  "conflicting_views": ["View A", "View B"]
}

confidence_score is 0.0-1.0 based on quality and agreement level.
detailed_synthesis should be a thorough markdown-formatted analysis."""

    user = f"""Question: {query}
Contradiction analysis: {json.dumps(contradictions)}

Reddit posts:
{posts_text}

Create structured findings JSON."""

    result = llm_call(system, user, max_tokens=1500, temperature=0.2)
    if not result:
        return {
            "consensus": "Reddit community insights on this topic.",
            "confidence_score": 0.7,
            "key_insights": ["Review multiple sources before deciding"],
            "positive_points": [], "negative_points": [],
            "recommendations": [], "caveats": [],
            "detailed_synthesis": "## Summary\n\nInsights from Reddit discussions.",
            "conflicting_views": []
        }
    try:
        return json.loads(result.strip())
    except:
        return {
            "consensus": "Reddit community insights on this topic.",
            "confidence_score": 0.7,
            "key_insights": ["Review multiple sources before deciding"],
            "positive_points": [], "negative_points": [],
            "recommendations": [], "caveats": [],
            "detailed_synthesis": "## Summary\n\nInsights from Reddit discussions.",
            "conflicting_views": []
        }
