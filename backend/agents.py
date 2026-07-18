"""The seven analysis agents.

Every agent takes the request-scoped ``LLMClient`` explicitly — there is no
module-level LLM state. Scraped Reddit content is always wrapped in
<untrusted> tags so the model treats it as data, never as instructions.
In simulated demo mode (no API key) the agents make no network calls at all.
"""

import json
import logging
import re
from typing import Any, Dict, List

from duckduckgo_search import DDGS

from llm import LLMClient
from schemas import (
    BatchCommentEvaluation,
    FactCheckClaim,
    FactCheckOutput,
    IntelligenceReport,
    KnowledgeGraphOutput,
    PerspectiveAndContradictionOutput,
    QueryExpansionOutput,
)
from simulated import get_simulated_claims, get_simulated_response

logger = logging.getLogger(__name__)


def _untrusted(text: str) -> str:
    return f"<untrusted>\n{text}\n</untrusted>"


def query_expansion_agent(llm: LLMClient, query: str) -> List[str]:
    """Expands a search query into multiple variations suitable for Reddit search."""
    prompt = f"""
    You are an expert search strategist analyzing search behaviors on Reddit.
    We need to expand the user's search query to get high-quality discussion threads.

    User query: "{query}"

    Generate alternative Reddit search queries covering:
    - beginner angle
    - advanced angle
    - budget angle
    - professional angle
    - comparison angle
    - common mistakes/pitfalls

    Return the queries in the requested structured JSON format.
    """
    data = llm.call_structured(prompt, QueryExpansionOutput)
    return data.get("queries") or [query]


def spam_and_quality_agent(llm: LLMClient, comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """2-stage filter: fast heuristics, then a batched LLM quality evaluation."""
    if not comments:
        return []

    # --- Stage 1: fast heuristics ---
    heuristic_passed = []
    seen_bodies = set()
    for c in comments:
        body = c.get("body", "")
        if body in seen_bodies:
            continue
        seen_bodies.add(body)
        if len(body) < 30:
            continue
        lower_body = body.lower()
        if any(w in lower_body for w in ["[deleted]", "[removed]", "troll comment", "spam link"]):
            continue
        ups = c.get("ups", 1)
        upvote_score = min(max(ups, 0), 100) / 100.0
        length_score = min(len(body), 1000) / 1000.0
        c["quality_score"] = round(0.5 * upvote_score + 0.5 * length_score, 2)
        heuristic_passed.append(c)

    heuristic_passed.sort(key=lambda x: x.get("quality_score", 0.0), reverse=True)
    candidates = heuristic_passed[:20]
    if not candidates:
        return []

    if not llm.active:
        for c in candidates:
            c["is_spam"] = False
            c["quality_reason"] = "Scored via local heuristics (upvotes and comment length)."
        return candidates

    # --- Stage 2: batched LLM evaluation ---
    comments_input = [
        {
            "index": idx,
            "author": c.get("author", "anonymous"),
            "ups": c.get("ups", 0),
            "body": c.get("body", "")[:400],  # truncate to keep the prompt small
        }
        for idx, c in enumerate(candidates)
    ]

    prompt = f"""
    You are a Spam Detection and Content Credibility Agent.
    Evaluate the following Reddit comments. Identify spam, low-effort jokes, sarcasm,
    deleted posts, bots, or uninformative text. For high-quality comments, assign a high
    quality score based on relevance, detail, evidence, facts, and benchmarks.

    Comments to evaluate:
    {_untrusted(json.dumps(comments_input, indent=2))}

    Output a structured JSON matching BatchCommentEvaluation.
    """

    data = llm.call_structured(prompt, BatchCommentEvaluation)
    evals_by_idx = {e["index"]: e for e in data.get("evaluations", [])}

    filtered_comments = []
    for idx, c in enumerate(candidates):
        evaluation = evals_by_idx.get(idx)
        if evaluation:
            score = evaluation.get("quality_score", c["quality_score"])
            if evaluation.get("is_spam_or_low_effort", False) or score < 0.3:
                continue
            c["quality_score"] = score
            c["quality_reason"] = evaluation.get("reason", "Evaluated by AI.")
        else:
            c["quality_reason"] = "Evaluated via fallback score."
        c["is_spam"] = False
        filtered_comments.append(c)

    filtered_comments.sort(key=lambda x: x.get("quality_score", 0.0), reverse=True)
    return filtered_comments or candidates


def perspective_contradiction_agent(llm: LLMClient, query: str, comments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Extracts user perspectives and conflicting viewpoints from filtered comments."""
    if not comments:
        return {"perspectives": [], "contradictions": []}

    formatted = ""
    for c in comments:
        formatted += f"--- COMMENT (Subreddit: r/{c.get('subreddit')}, Upvotes: {c.get('ups')}) ---\n{c.get('body')}\n\n"

    prompt = f"""
    You are a Perspective and Disagreement Analysis Agent.
    Review the following Reddit comments regarding: "{query}".

    Your task:
    1. Group comments by user segments/perspectives (e.g. 'Experienced Developers', 'Budget Buyers').
       Provide the perspective name, a summary consensus, and key supporting points.
    2. Extract key contradictions, debates, or core arguments where users explicitly disagree.

    Comments:
    {_untrusted(formatted)}

    Output a structured JSON matching PerspectiveAndContradictionOutput.
    """
    return llm.call_structured(prompt, PerspectiveAndContradictionOutput)


def knowledge_graph_agent(llm: LLMClient, query: str, comments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Extracts entities and relationships from the discussions."""
    if not comments:
        return {"nodes": [], "edges": []}

    formatted = "".join(f"Comment: {c.get('body')}\n\n" for c in comments)

    prompt = f"""
    You are a Knowledge Graph Engineer.
    Analyze the discussions about "{query}" and extract a relationship graph.
    Identify key entities (Hardware, Software, Concepts, Organizations) and the
    connections between them. Keep the nodes concise and use unique kebab-case IDs.

    Discussions:
    {_untrusted(formatted)}

    Output a structured JSON matching KnowledgeGraphOutput.
    """
    return llm.call_structured(prompt, KnowledgeGraphOutput)


def fact_checking_agent(llm: LLMClient, query: str, comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Identifies key technical claims, searches the web, and verifies them.

    In demo mode this performs no web searches and returns clearly-labelled
    sample data — it never fabricates a verification verdict.
    """
    if not comments:
        return []

    if not llm.active:
        claims = get_simulated_claims(query)
        sim_facts = get_simulated_response(f'verify claims regarding: "{query}"', FactCheckOutput).get("facts_checked", [])
        by_claim = {f.get("claim"): f for f in sim_facts}
        return [
            by_claim.get(
                claim,
                {
                    "claim": claim,
                    "status": "Unverified",
                    "explanation": "[Demo sample] No live verification was performed — connect an API key for real analysis.",
                    "source_link": "",
                },
            )
            for claim in claims
        ]

    # --- Step 1: identify checkable claims ---
    formatted = "".join(f"Comment {idx}: {c.get('body')}\n\n" for idx, c in enumerate(comments[:8]))
    identify_prompt = f"""
    Identify the top 2 key technical claims or factual assertions made in these comments
    regarding: "{query}".
    Return them as a simple JSON list of strings, for example: ["claim 1", "claim 2"].
    Only return technical or factual assertions that can be checked
    (e.g. 'RTX 4090 laptop has 16GB VRAM'). Do not return general opinions.

    Comments:
    {_untrusted(formatted)}
    """

    claims: List[str] = []
    try:
        res_text = llm.call(identify_prompt)
        match = re.search(r"\[.*\]", res_text.replace("\n", " "))
        if match:
            parsed = json.loads(match.group(0))
            claims = [c for c in parsed if isinstance(c, str) and c.strip()]
    except Exception as exc:
        logger.error("Error identifying claims: %s", exc)
    if not claims:
        return []

    # --- Step 2: search the web and verify each claim ---
    checked_facts = []
    for claim in claims[:3]:
        logger.info("Fact checking claim: '%s'", claim)
        search_snippets = ""
        source_url = ""
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(claim, max_results=3))
                if results:
                    source_url = results[0].get("href", "")
                    for r in results:
                        search_snippets += f"- Title: {r.get('title')}\n  Snippet: {r.get('body')}\n\n"
        except Exception as search_err:
            logger.error("Search error during fact-checking: %s", search_err)
        if not search_snippets:
            search_snippets = "No search results available."

        verify_prompt = f"""
        You are an elite Fact-Checking Agent.
        Analyze this claim: "{claim}"

        Here are search engine results for this claim:
        {_untrusted(search_snippets)}

        Evaluate whether the claim is:
        - "Verified": supported fully by search results.
        - "Debunked": contradicted by search results.
        - "Disputed": supported by some but contradicted by others.
        - "Unverified": not enough information to confirm.

        Provide the output in the requested JSON structure.
        """
        fact_obj = llm.call_structured(verify_prompt, FactCheckClaim)
        fact_obj["claim"] = claim
        if source_url:
            fact_obj["source_link"] = source_url
        checked_facts.append(fact_obj)

    return checked_facts


def consensus_synthesis_agent(
    llm: LLMClient,
    query: str,
    comments: List[Dict[str, Any]],
    perspectives: List[Dict[str, Any]],
    contradictions: List[str],
    facts: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Combines all agent results into a final structured intelligence report."""
    if not comments:
        return {
            "consensus_summary": "No discussions retrieved.",
            "confidence_score": 0.0,
            "detailed_synthesis": "No detailed synthesis available.",
        }

    formatted_comments = "".join(
        f"Comment: {c.get('body')} (Upvotes: {c.get('ups')})\n" for c in comments[:6]
    )

    prompt = f"""
    You are a Knowledge Synthesizer and Content Strategist.
    We are generating a Reddit Intelligence Report for the query: "{query}"

    We have already extracted the following structured data:

    1. Perspectives:
    {json.dumps(perspectives, indent=2)}

    2. Contradictions & Debates:
    {json.dumps(contradictions, indent=2)}

    3. Checked Facts:
    {json.dumps(facts, indent=2)}

    4. Top Comments:
    {_untrusted(formatted_comments)}

    Your task:
    - Create a comprehensive paragraph summarizing the community consensus.
    - Rate our overall confidence score (0.0 to 1.0) based on comment quality, source volume, and agreement levels.
    - Write a detailed markdown synthesis breaking down the core topics, arguments, and tradeoffs. Use clear headers and bullet points.

    Output a structured JSON matching IntelligenceReport.
    """
    return llm.call_structured(prompt, IntelligenceReport)
