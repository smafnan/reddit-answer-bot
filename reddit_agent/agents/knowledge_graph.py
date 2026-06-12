from agents.llm import llm_call


def extract_knowledge_graph(posts: list) -> dict:
    """Extract entities and relationships from posts."""
    if not posts:
        return {"entities": [], "relationships": []}

    posts_text = ""
    for p in posts[:5]:
        text = f"{p['title']}. {p['text'][:300]}"
        posts_text += f"\n---\n{text}\n"

    system = """You are a knowledge graph extractor. From Reddit discussions, identify key entities (products, technologies, concepts) and their relationships.

Return a JSON object:
{
  "entities": [
    {"name": "RTX 4090", "type": "product", "mentions": 3, "sentiment": "positive"},
    {"name": "Ollama", "type": "software", "mentions": 2, "sentiment": "positive"}
  ],
  "relationships": [
    {"source": "Ollama", "target": "Llama 3", "relation": "runs", "evidence": "mentioned in post 0"},
    {"source": "RTX 4090", "target": "VRAM", "relation": "provides", "evidence": "multiple mentions"}
  ]
}"""

    user = f"""Extract knowledge graph from these Reddit discussions:
{posts_text}

Return ONLY JSON."""

    result = llm_call(system, user, max_tokens=1000, temperature=0.2)
    try:
        import json
        return json.loads(result.strip())
    except:
        return {"entities": [], "relationships": []}
