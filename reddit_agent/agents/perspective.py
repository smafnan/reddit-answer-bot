from agents.llm import llm_call


def generate_perspectives(query: str) -> list:
    """Generate different stakeholder perspectives to explore."""
    system = """You are a perspective strategist. For any question, identify different stakeholder groups whose perspectives would be valuable.

Return ONLY a JSON array of perspective objects:
[
  {"group": "Beginners", "angle": "What do first-time buyers think?"},
  {"group": "Experts", "angle": "What do experienced professionals recommend?"},
  {"group": "Critics", "angle": "What do people who regret their purchase say?"}
]

Generate 4-6 distinct perspectives. Return ONLY JSON."""

    user = f"""Question: "{query}"

Generate useful stakeholder perspectives for researching this on Reddit."""

    result = llm_call(system, user, max_tokens=600, temperature=0.7)
    try:
        import json
        return json.loads(result.strip())
    except:
        return []
