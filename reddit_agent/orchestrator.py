from agents.query_expander import expand_query
from agents.reddit_retriever import retrieve
from agents.spam_filter import filter_spam
from agents.credibility_scorer import score_credibility
from agents.contradiction import detect_contradictions
from agents.perspective import generate_perspectives
from agents.knowledge_graph import extract_knowledge_graph
from agents.summarizer import summarize_findings
from agents.fact_check import fact_check


def run_pipeline(query: str) -> dict:
    print(f"\n{'='*60}")
    print(f"  REDDIT INTELLIGENCE ENGINE")
    print(f"{'='*60}\n")

    # Agent 1: Query Expansion
    print("[1/9] Expanding query...")
    queries = expand_query(query)
    print(f"       Generated {len(queries)} search queries")

    # Agent 2: Reddit Retrieval
    print("[2/9] Retrieving from Reddit...")
    all_posts = []
    for q in queries[:3]:
        posts = retrieve(q)
        all_posts.extend(posts)
    # Deduplicate
    seen = set()
    unique_posts = []
    for p in all_posts:
        if p["url"] not in seen:
            seen.add(p["url"])
            unique_posts.append(p)
    print(f"       Retrieved {len(unique_posts)} unique posts")

    if not unique_posts:
        return {"error": "No Reddit posts found"}

    # Agent 3: Spam Detection
    print("[3/9] Filtering spam/low-quality...")
    filtered = filter_spam(unique_posts)
    print(f"       Kept {len(filtered)} posts")

    if not filtered:
        return {"error": "All posts filtered as low quality"}

    # Agent 4: Credibility Scoring
    print("[4/9] Scoring credibility...")
    scored = score_credibility(filtered)
    print(f"       Top score: {scored[0].get('credibility', 'N/A')}/10")

    # Agent 5: Contradiction Detection
    print("[5/9] Detecting contradictions...")
    contradictions = detect_contradictions(query, scored)
    if contradictions.get("has_contradictions"):
        print(f"       Found {len(contradictions.get('viewpoints', []))} different viewpoints")
    else:
        print("       No major contradictions found")

    # Agent 6: Perspective Generation
    print("[6/9] Generating perspectives...")
    perspectives = generate_perspectives(query)
    print(f"       Identified {len(perspectives)} stakeholder perspectives")

    # Agent 7: Knowledge Graph
    print("[7/9] Extracting knowledge graph...")
    kg = extract_knowledge_graph(scored[:5])
    print(f"       Found {len(kg.get('entities', []))} entities")

    # Agent 8: Summarization
    print("[8/9] Synthesizing findings...")
    summary = summarize_findings(query, scored, contradictions)
    print("       Summary created")

    # Agent 9: Fact Check
    print("[9/9] Fact-checking...")
    fact_check_result = fact_check(query, summary)
    print(f"       Assessment: {fact_check_result.get('overall_assessment', 'N/A')}")

    return {
        "query": query,
        "expanded_queries": queries,
        "scored_posts": scored,
        "contradictions": contradictions,
        "perspectives": perspectives,
        "knowledge_graph": kg,
        "summary": summary,
        "fact_check": fact_check_result,
    }
