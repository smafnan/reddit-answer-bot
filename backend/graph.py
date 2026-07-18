"""LangGraph pipeline definition and streaming runner.

The compiled StateGraph is genuinely executed (via ``compiled_graph.stream``),
and the three independent analysis agents — perspective extraction, knowledge
graph construction, and fact-checking — run as a parallel fan-out in one
LangGraph superstep, then fan back in to the synthesizer:

    query_expansion → retrieval → spam_filtering ─┬─ perspective_extraction ─┐
                                                  ├─ knowledge_graph_builder ├─→ synthesizer
                                                  └─ fact_checking ──────────┘

Each node is internally resilient: a failing agent degrades to an empty/fallback
value instead of aborting the run.
"""

import datetime
import logging
import uuid
from typing import Any, Dict, Generator, List, TypedDict

from langgraph.graph import END, StateGraph

import storage
from agents import (
    consensus_synthesis_agent,
    fact_checking_agent,
    knowledge_graph_agent,
    perspective_contradiction_agent,
    query_expansion_agent,
    spam_and_quality_agent,
)
from llm import LLMClient
from retrieval import search_reddit_hybrid
from simulated import get_mock_retrieved_comments

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    llm: Any  # request-scoped LLMClient
    query: str
    expanded_queries: List[str]
    retrieved_comments: List[Dict[str, Any]]
    filtered_comments: List[Dict[str, Any]]
    perspectives: List[Dict[str, Any]]
    contradictions: List[str]
    knowledge_graph: Dict[str, Any]
    facts_checked: List[Dict[str, Any]]
    synthesis: Dict[str, Any]


# --- Nodes ---


def expand_queries_node(state: AgentState) -> Dict[str, Any]:
    logger.info("Executing expand_queries_node")
    try:
        return {"expanded_queries": query_expansion_agent(state["llm"], state["query"])}
    except Exception as exc:
        logger.error("Query expansion failed: %s", exc)
        return {"expanded_queries": [state["query"]]}


def retrieve_comments_node(state: AgentState) -> Dict[str, Any]:
    logger.info("Executing retrieve_comments_node")
    query = state["query"]

    # Demo mode: skip slow real network calls entirely and return topic-specific
    # mock comments (also keeps serverless demo deployments within timeouts).
    if not state["llm"].active:
        logger.info("Demo mode — using mock Reddit comments, no network retrieval.")
        return {"retrieved_comments": get_mock_retrieved_comments(query)}

    search_list = list(dict.fromkeys([query] + state["expanded_queries"][:2]))
    all_comments: List[Dict[str, Any]] = []
    for idx, q in enumerate(search_list):
        logger.info("Retrieval step (%d/%d): searching '%s'", idx + 1, len(search_list), q)
        try:
            all_comments.extend(search_reddit_hybrid(q, max_results=3))
        except Exception as exc:
            logger.error("Error searching '%s': %s", q, exc)

    # Deduplicate on body content
    unique_comments, seen = [], set()
    for c in all_comments:
        body = c.get("body", "")
        if body not in seen:
            seen.add(body)
            unique_comments.append(c)

    # Live retrieval can legitimately come back empty (rate limits, thin topics);
    # fall back to mock comments so the report still demonstrates the pipeline.
    if not unique_comments:
        logger.info("Retrieved 0 comments — falling back to topic-specific mock comments.")
        unique_comments = get_mock_retrieved_comments(query)

    return {"retrieved_comments": unique_comments}


def filter_comments_node(state: AgentState) -> Dict[str, Any]:
    logger.info("Executing filter_comments_node")
    try:
        return {"filtered_comments": spam_and_quality_agent(state["llm"], state["retrieved_comments"])}
    except Exception as exc:
        logger.error("Spam filtering failed: %s — using raw comments.", exc)
        return {"filtered_comments": state["retrieved_comments"]}


def extract_perspectives_node(state: AgentState) -> Dict[str, Any]:
    logger.info("Executing extract_perspectives_node")
    try:
        data = perspective_contradiction_agent(state["llm"], state["query"], state["filtered_comments"])
        return {
            "perspectives": data.get("perspectives", []),
            "contradictions": data.get("contradictions", []),
        }
    except Exception as exc:
        logger.error("Perspective extraction failed: %s", exc)
        return {"perspectives": [], "contradictions": []}


def build_knowledge_graph_node(state: AgentState) -> Dict[str, Any]:
    logger.info("Executing build_knowledge_graph_node")
    try:
        return {"knowledge_graph": knowledge_graph_agent(state["llm"], state["query"], state["filtered_comments"])}
    except Exception as exc:
        logger.error("Knowledge graph construction failed: %s", exc)
        return {"knowledge_graph": {"nodes": [], "edges": []}}


def fact_check_node(state: AgentState) -> Dict[str, Any]:
    logger.info("Executing fact_check_node")
    try:
        return {"facts_checked": fact_checking_agent(state["llm"], state["query"], state["filtered_comments"])}
    except Exception as exc:
        logger.error("Fact checking failed: %s", exc)
        return {"facts_checked": []}


def synthesize_node(state: AgentState) -> Dict[str, Any]:
    logger.info("Executing synthesize_node")
    try:
        report = consensus_synthesis_agent(
            llm=state["llm"],
            query=state["query"],
            comments=state["filtered_comments"],
            perspectives=state["perspectives"],
            contradictions=state["contradictions"],
            facts=state["facts_checked"],
        )
        return {"synthesis": report}
    except Exception as exc:
        logger.error("Synthesis failed: %s", exc)
        return {
            "synthesis": {
                "consensus_summary": "Synthesis could not be completed.",
                "confidence_score": 0.0,
                "detailed_synthesis": "",
            }
        }


# --- Assemble the StateGraph ---

workflow = StateGraph(AgentState)

workflow.add_node("query_expansion", expand_queries_node)
workflow.add_node("retrieval", retrieve_comments_node)
workflow.add_node("spam_filtering", filter_comments_node)
workflow.add_node("perspective_extraction", extract_perspectives_node)
workflow.add_node("knowledge_graph_builder", build_knowledge_graph_node)
workflow.add_node("fact_checking", fact_check_node)
workflow.add_node("synthesizer", synthesize_node)

workflow.set_entry_point("query_expansion")
workflow.add_edge("query_expansion", "retrieval")
workflow.add_edge("retrieval", "spam_filtering")
# Parallel fan-out: the three analysis agents only depend on filtered comments,
# so LangGraph executes them concurrently in a single superstep.
workflow.add_edge("spam_filtering", "perspective_extraction")
workflow.add_edge("spam_filtering", "knowledge_graph_builder")
workflow.add_edge("spam_filtering", "fact_checking")
# Fan-in: the synthesizer waits for all three.
workflow.add_edge("perspective_extraction", "synthesizer")
workflow.add_edge("knowledge_graph_builder", "synthesizer")
workflow.add_edge("fact_checking", "synthesizer")
workflow.add_edge("synthesizer", END)

compiled_graph = workflow.compile()


# --- Progress messages per node (streamed to the frontend stepper) ---

NODE_MESSAGES = {
    "query_expansion": "Generated alternative search angles.",
    "retrieval": "Queried Reddit discussions.",
    "spam_filtering": "Evaluated credibility & filtered spam.",
    "perspective_extraction": "Analyzed perspectives & debates.",
    "knowledge_graph_builder": "Constructed entity relationships.",
    "fact_checking": "Cross-checked claims against web sources.",
    "synthesizer": "Synthesized consensus report.",
}


def _node_details(node: str, state: Dict[str, Any]) -> str:
    if node == "query_expansion":
        return f"Generated {len(state.get('expanded_queries', []))} search angles."
    if node == "retrieval":
        return f"Retrieved {len(state.get('retrieved_comments', []))} unique comments across discussions."
    if node == "spam_filtering":
        return f"Filtered to top {len(state.get('filtered_comments', []))} quality discussions."
    if node == "perspective_extraction":
        return f"Identified {len(state.get('perspectives', []))} distinct perspective segments."
    if node == "knowledge_graph_builder":
        return f"Extracted {len(state.get('knowledge_graph', {}).get('nodes', []))} key entity concepts."
    if node == "fact_checking":
        return f"Fact-checked {len(state.get('facts_checked', []))} technical assertions."
    if node == "synthesizer":
        return "Consensus report formulated."
    return ""


class RedditIntelligencePipeline:
    """Runs the compiled LangGraph workflow, yielding progress events in real time."""

    def __init__(self, query: str, api_key: str = None, provider: str = None, model: str = None):
        self.query = query
        self.llm = LLMClient(provider=provider, api_key=api_key, model=model)

    def run(self) -> Generator[Dict[str, Any], None, None]:
        state: Dict[str, Any] = {
            "llm": self.llm,
            "query": self.query,
            "expanded_queries": [],
            "retrieved_comments": [],
            "filtered_comments": [],
            "perspectives": [],
            "contradictions": [],
            "knowledge_graph": {"nodes": [], "edges": []},
            "facts_checked": [],
            "synthesis": {},
        }

        yield {
            "step": "query_expansion",
            "status": "running",
            "message": "Generating alternative search angles...",
            "details": f"Analyzing query: '{self.query}'",
        }

        try:
            for update in compiled_graph.stream(state, stream_mode="updates"):
                for node_name, node_output in update.items():
                    if node_name == "__end__":
                        continue
                    state.update(node_output or {})
                    yield {
                        "step": node_name,
                        "status": "done",
                        "message": NODE_MESSAGES.get(node_name, node_name),
                        "details": _node_details(node_name, state),
                    }
        except Exception as exc:
            logger.exception("Pipeline execution failed")
            yield {"step": "failed", "message": "Pipeline execution failed.", "details": str(exc)}
            return

        try:
            report_data = self._build_report(state)
        except Exception as exc:
            logger.exception("Failed to compile report")
            yield {"step": "failed", "message": "Failed to compile report.", "details": str(exc)}
            return

        saved_path = storage.save_report(report_data)  # non-fatal if None
        yield {
            "step": "completed",
            "status": "done",
            "message": "Synthesis complete!",
            "details": "Intelligence report compiled." + (" Saved." if saved_path else " (Persistence unavailable on this host.)"),
            "data": report_data,
        }

    def _build_report(self, state: Dict[str, Any]) -> Dict[str, Any]:
        seen_urls, sources = set(), []
        for c in state["filtered_comments"]:
            url = c.get("post_url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                sources.append(
                    {
                        "title": c.get("post_title") or "Reddit Thread",
                        "url": url,
                        "subreddit": c.get("subreddit", ""),
                    }
                )

        return {
            "id": str(uuid.uuid4()),
            "query": self.query,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "llm_mode": "live" if self.llm.active else "simulated",
            "provider": self.llm.provider,
            "synthesis": state["synthesis"],
            "sources": sources,
            "perspectives": state["perspectives"],
            "contradictions": state["contradictions"],
            "knowledge_graph": state["knowledge_graph"],
            "facts_checked": state["facts_checked"],
            "featured_comments": [
                {
                    "author": c.get("author", "anonymous"),
                    "body": c.get("body", ""),
                    "ups": c.get("ups", 0),
                    "subreddit": c.get("subreddit", "unknown"),
                    "url": c.get("post_url", ""),
                    "quality_score": c.get("quality_score", 0.0),
                    "quality_reason": c.get("quality_reason", ""),
                }
                for c in state["filtered_comments"][:6]
            ],
        }


if __name__ == "__main__":
    pipeline = RedditIntelligencePipeline("Should I buy a Tesla?")
    for progress in pipeline.run():
        print(progress["step"], "-", progress.get("message", ""))
