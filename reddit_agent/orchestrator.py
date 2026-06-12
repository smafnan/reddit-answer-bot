import json
from agents.query_expander import expand_query
from agents.reddit_retriever import retrieve
from agents.spam_filter import filter_spam
from agents.credibility_scorer import score_credibility
from agents.contradiction import detect_contradictions
from agents.perspective import generate_perspectives
from agents.knowledge_graph import extract_knowledge_graph
from agents.summarizer import summarize_findings
from agents.fact_check import fact_check


def run_pipeline(query: str):
    yield {"step": "query_expansion", "message": "Expanding query into multiple search angles..."}
    queries = expand_query(query)
    yield {"step": "query_expansion", "message": f"Generated {len(queries)} search queries"}

    yield {"step": "retrieval", "message": "Retrieving Reddit discussions..."}
    all_posts = []
    for q in queries[:4]:
        posts = retrieve(q)
        all_posts.extend(posts)
        if len(all_posts) >= 30:
            break
    seen = set()
    unique_posts = []
    for p in all_posts:
        if p["url"] not in seen:
            seen.add(p["url"])
            unique_posts.append(p)
    yield {"step": "retrieval", "message": f"Found {len(unique_posts)} unique posts"}

    if not unique_posts:
        yield {"step": "failed", "message": "No Reddit posts found", "error": "No posts retrieved"}
        return

    yield {"step": "spam_filtering", "message": "Filtering spam and low-quality content..."}
    filtered = filter_spam(unique_posts)
    yield {"step": "spam_filtering", "message": f"Kept {len(filtered)} quality posts"}

    if not filtered:
        yield {"step": "failed", "message": "All posts filtered as low quality", "error": "No quality posts remain"}
        return

    yield {"step": "credibility_scoring", "message": "Scoring credibility of each post..."}
    scored = score_credibility(filtered)
    yield {"step": "credibility_scoring", "message": f"Top credibility score: {scored[0].get('credibility', 'N/A')}/10"}

    yield {"step": "contradiction_detection", "message": "Detecting contradictions and debates..."}
    contradictions = detect_contradictions(query, scored)
    num_vp = len(contradictions.get("viewpoints", []))
    yield {"step": "contradiction_detection", "message": f"Found {num_vp} different viewpoints" if num_vp else "No major contradictions found"}

    yield {"step": "perspective_generation", "message": "Generating stakeholder perspectives..."}
    perspectives = generate_perspectives(query)
    yield {"step": "perspective_generation", "message": f"Identified {len(perspectives)} stakeholder perspectives"}

    yield {"step": "knowledge_graph", "message": "Extracting knowledge graph entities..."}
    kg = extract_knowledge_graph(scored[:5])
    yield {"step": "knowledge_graph", "message": f"Found {len(kg.get('nodes', []))} entities, {len(kg.get('edges', []))} relationships"}

    yield {"step": "synthesis", "message": "Synthesizing all findings into report..."}
    summary = summarize_findings(query, scored, contradictions)
    yield {"step": "synthesis", "message": "Summary created"}

    yield {"step": "fact_check", "message": "Fact-checking key claims..."}
    fc = fact_check(query, summary)
    yield {"step": "fact_check", "message": f"Assessment: {fc.get('overall_assessment', 'N/A')}"}

    yield {"step": "completed", "message": "Complete!", "data": {
        "query": query,
        "expanded_queries": queries,
        "scored_posts": scored,
        "contradictions": contradictions,
        "perspectives": perspectives,
        "knowledge_graph": kg,
        "summary": summary,
        "fact_check": fc,
    }}
