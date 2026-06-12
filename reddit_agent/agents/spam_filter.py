import json
from agents.llm import llm_call


def filter_spam(posts: list) -> list:
    if not posts:
        return []

    posts_text = ""
    for i, p in enumerate(posts):
        posts_text += f"\n[{i}] Title: {p['title']}\n    Text: {p.get('text', '')[:300]}\n    Subreddit: {p.get('subreddit', '')}\n"

    system = """You are a quality filter for Reddit content. Evaluate each post and return ONLY a JSON array of indices to KEEP.

Rules for keeping a post:
- Title is descriptive and relevant (not clickbait or low-effort)
- Has meaningful text content
- Looks like a genuine discussion (not spam or self-promotion)
- Is on-topic

Return format: [0, 2, 4]"""

    user = f"""Posts to evaluate:
{posts_text}

Return JSON array of indices to KEEP."""

    result = llm_call(system, user, max_tokens=300, temperature=0.1)
    if not result:
        return posts
    try:
        keep = json.loads(result.strip())
        return [posts[i] for i in keep if i < len(posts)]
    except:
        return posts
