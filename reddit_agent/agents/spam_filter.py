from agents.llm import llm_call


def filter_spam(posts: list) -> list:
    """Filter out low-quality posts using LLM evaluation."""
    if not posts:
        return []

    posts_text = ""
    for i, p in enumerate(posts):
        posts_text += f"\n[{i}] Title: {p['title']}\n    Text: {p['text'][:200]}\n    Subreddit: {p['subreddit']}\n"

    system = """You are a quality filter for Reddit content. Evaluate each post and return ONLY a JSON array of indices to KEEP (0-indexed).

Rules for keeping a post:
- Title is descriptive and relevant (not clickbait, not low-effort)
- Has meaningful text content (not just "title says it all")
- Looks like a genuine question/discussion (not spam, not self-promotion)
- Is on-topic and useful

Return format: [0, 2, 4]
Return empty array [] if none are useful."""

    user = f"""Posts to evaluate:
{posts_text}

Return JSON array of indices to KEEP."""

    result = llm_call(system, user, max_tokens=300, temperature=0.1)
    try:
        import json
        keep = json.loads(result.strip())
        return [posts[i] for i in keep if i < len(posts)]
    except:
        return posts
