from agents.llm import llm_call


def score_credibility(posts: list) -> list:
    """Score and rank posts by credibility signals."""
    if not posts:
        return []

    posts_text = ""
    for i, p in enumerate(posts):
        posts_text += f"\n[{i}] Title: {p['title']}\n    Text: {p['text'][:300]}\n    Subreddit: {p['subreddit']}\n"

    system = """You are a credibility analyst for Reddit content. Score each post on quality signals.

Rate each post 0-10 on these dimensions:
- technical_detail: Contains specific info, numbers, benchmarks, comparisons
- relevance: Directly addresses the topic
- effort: Shows genuine experience or research
- usefulness: Would help someone making a decision

Return ONLY a JSON array of objects:
[{"index": 0, "score": 8.5, "reason": "detailed benchmarks provided"}, ...]"""

    user = f"""Posts to evaluate:
{posts_text}

Return JSON array with scores."""

    result = llm_call(system, user, max_tokens=800, temperature=0.2)
    try:
        import json
        scores = json.loads(result.strip())
        scored = []
        for s in scores:
            idx = s["index"]
            if idx < len(posts):
                posts[idx]["credibility"] = s.get("score", 5)
                posts[idx]["credibility_reason"] = s.get("reason", "")
                scored.append(posts[idx])
        scored.sort(key=lambda x: x.get("credibility", 0), reverse=True)
        return scored
    except:
        for p in posts:
            p["credibility"] = 5
            p["credibility_reason"] = "default"
        return posts
