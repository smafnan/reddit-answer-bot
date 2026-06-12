from agents.llm import llm_call


def expand_query(query: str) -> list:
    system = """You are a Reddit search strategist. Generate diverse alternative search queries to maximize recall of useful Reddit discussions.

Return ONLY a JSON array of strings, no other text. Example:
["query 1", "query 2", "query 3"]"""

    user = f"""Original query: "{query}"

Generate 8 alternative search queries covering:
- beginner angle
- advanced/pro angle
- budget angle
- comparison angle
- troubleshooting angle
- recommendation angle
- experience/review angle
- common mistakes angle

Return as JSON array only."""

    result = llm_call(system, user, max_tokens=800, temperature=0.7)
    try:
        import json
        expanded = json.loads(result.strip())
        return [query] + expanded
    except:
        return [query]
