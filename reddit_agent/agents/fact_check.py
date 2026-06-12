import json
from agents.llm import llm_call


def fact_check(query: str, findings: dict) -> dict:
    consensus = findings.get("consensus", "")
    insights = findings.get("key_insights", [])

    system = """You are a fact-checker. Reddit may contain misinformation. Compare Reddit claims against established facts.

Return a JSON object:
{
  "verified_claims": ["Claim that checks out"],
  "questionable_claims": ["Claim that seems wrong or exaggerated"],
  "corrections": ["What the actual fact is"],
  "overall_assessment": "reddit_is_generally_correct / reddit_has_mixed_accuracy / reddit_is_misleading",
  "recommendation": "What the user should trust",
  "confidence": "high/medium/low"
}"""

    user = f"""Question: {query}
Reddit consensus: {consensus}
Key insights: {'; '.join(insights[:3])}

Fact-check the Reddit claims against known facts. Return JSON."""

    result = llm_call(system, user, max_tokens=800, temperature=0.2)
    if not result:
        return {
            "overall_assessment": "could_not_verify",
            "recommendation": "Verify claims independently",
            "verified_claims": [], "questionable_claims": [], "corrections": [], "confidence": "low"
        }
    try:
        return json.loads(result.strip())
    except:
        return {
            "overall_assessment": "could_not_verify",
            "recommendation": "Verify claims independently",
            "verified_claims": [], "questionable_claims": [], "corrections": [], "confidence": "low"
        }
