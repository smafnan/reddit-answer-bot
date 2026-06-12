import json
from agents.llm import llm_call


SIMULATED_QUERIES = [
    "reddit experiences and honest reviews",
    "common problems and issues reddit",
    "pros and cons from real users reddit",
    "is it worth buying reddit discussion",
    "alternatives and comparisons reddit",
    "beginner tips and recommendations reddit",
    "long term ownership experience reddit",
    "common mistakes to avoid reddit",
]


def expand_query(query: str) -> list:
    system = """You are a Reddit search strategist. Generate diverse alternative search queries.

Return ONLY a JSON array of strings, no other text. Example: ["query 1", "query 2", "query 3"]"""

    user = f"""Original query: "{query}"

Generate 6-8 alternative search queries covering:
- beginner angle
- advanced/expert angle
- budget angle
- comparison with alternatives
- troubleshooting / problems
- recommendation / "what should I buy"
- experience / "real user review"
- common mistakes

Return as JSON array only."""

    result = llm_call(system, user, max_tokens=800, temperature=0.7)
    if not result:
        return SIMULATED_QUERIES
    try:
        expanded = json.loads(result.strip())
        return [query] + expanded
    except:
        return SIMULATED_QUERIES
