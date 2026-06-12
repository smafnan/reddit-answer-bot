import json
from agents.llm import llm_call


def extract_knowledge_graph(posts: list) -> dict:
    if not posts:
        return {"nodes": [], "edges": []}

    posts_text = ""
    for p in posts[:5]:
        posts_text += f"\n---\n{p.get('title', '')}. {p.get('text', '')[:400]}\n"

    system = """You are a knowledge graph extractor. From discussions, identify key entities and relationships.

Return a JSON object:
{
  "nodes": [
    {"id": "rtx-4090", "label": "RTX 4090", "type": "Hardware"},
    {"id": "ollama", "label": "Ollama", "type": "Software"},
    {"id": "vram", "label": "VRAM", "type": "Concept"}
  ],
  "edges": [
    {"source": "rtx-4090", "target": "vram", "label": "has 24GB"},
    {"source": "ollama", "target": "rtx-4090", "label": "runs on"}
  ]
}

Node types: Hardware, Software, Concept, Organization
Return ONLY JSON."""

    user = f"""Extract knowledge graph from these discussions:
{posts_text}

Return ONLY JSON."""

    result = llm_call(system, user, max_tokens=1000, temperature=0.2)
    if not result:
        return {"nodes": [], "edges": []}
    try:
        return json.loads(result.strip())
    except:
        return {"nodes": [], "edges": []}
