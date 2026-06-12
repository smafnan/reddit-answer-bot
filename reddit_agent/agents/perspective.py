import json
from agents.llm import llm_call


def generate_perspectives(query: str) -> list:
    system = """You are a perspective strategist. Identify different stakeholder groups whose perspectives would be valuable.

Return ONLY a JSON array:
[
  {"group": "Beginners", "angle": "What do first-time buyers think?", "consensus": "", "supporting_points": []},
  {"group": "Experts", "angle": "What do experienced professionals recommend?", "consensus": "", "supporting_points": []}
]

Return 4-6 perspectives. Return ONLY JSON."""

    user = f"""Question: "{query}"

Generate useful stakeholder perspectives for researching this on Reddit."""

    result = llm_call(system, user, max_tokens=600, temperature=0.7)
    if not result:
        return [
            {"group": "General Users", "angle": "What do everyday users think?", "consensus": "", "supporting_points": []},
            {"group": "Experts", "angle": "What do professionals recommend?", "consensus": "", "supporting_points": []},
        ]
    try:
        return json.loads(result.strip())
    except:
        return []
