"""LangGraph pipeline: understand -> retrieve -> answer, with an honest gate.

    understand (1 LLM call) ─┬─ greeting/off_topic/needs_clarification ─→ direct reply (no retrieval)
                             └─ answerable/follow_up ─→ retrieve (Reddit) ─→ rank
                                     ├─ coverage gate FAIL ─→ honest refusal (0 LLM calls)
                                     └─ gate PASS ─→ answer (1 LLM call) ─→ validate citations

The compiled StateGraph is genuinely executed via `compiled_graph.stream`.
Mock comments appear ONLY in demo mode (no LLM key) — never as a fallback that
papers over empty live retrieval.
"""

import datetime
import logging
import uuid
from typing import Any, Dict, Generator, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

import storage
from agents import answer_agent, understand_query_agent
from grounding import build_citations, coverage_gate, validate_citations
from llm import LLMClient
from ranking import rank_and_select
from retrieval import RetrievalResult, search_reddit
from schemas import AnswerOutput, QueryPlan
from simulated import get_mock_retrieved_comments

logger = logging.getLogger(__name__)

SHORT_CIRCUIT_INTENTS = ("greeting", "off_topic", "needs_clarification")


class AgentState(TypedDict):
    llm: Any
    reddit_creds: Optional[Dict[str, str]]
    messages: List[Dict[str, str]]
    plan: QueryPlan
    retrieval: Any
    pack: List[Dict[str, Any]]
    signals: Dict[str, float]
    answer: AnswerOutput


# --- Nodes ---

def understand_node(state: AgentState) -> Dict[str, Any]:
    logger.info("understand_node")
    try:
        return {"plan": understand_query_agent(state["llm"], state["messages"])}
    except Exception as exc:
        logger.error("understand failed: %s", exc)
        q = state["messages"][-1]["content"] if state["messages"] else ""
        return {"plan": QueryPlan(intent="answerable", standalone_question=q, search_queries=[q])}


def retrieve_node(state: AgentState) -> Dict[str, Any]:
    logger.info("retrieve_node")
    plan = state["plan"]
    if plan.intent in SHORT_CIRCUIT_INTENTS or not plan.is_reddit_suitable:
        return {}  # short-circuit; answer_node handles the direct reply
    if not state["llm"].active:
        # Demo mode: mock comments ONLY when no LLM key. Never a live-empty fallback.
        # Feed the search queries too, so topic detection survives context-free
        # follow-ups ("what about the depreciation?") whose standalone text lost the keyword.
        topic_hint = " ".join([plan.standalone_question] + (plan.search_queries or []))
        result = RetrievalResult("demo", get_mock_retrieved_comments(topic_hint))
    else:
        result = search_reddit(plan, state["reddit_creds"])
    pack, signals = rank_and_select(plan, result)
    return {"retrieval": result, "pack": pack, "signals": signals}


def answer_node(state: AgentState) -> Dict[str, Any]:
    logger.info("answer_node")
    plan = state["plan"]
    if plan.intent in SHORT_CIRCUIT_INTENTS or not plan.is_reddit_suitable:
        reply = plan.direct_reply or "I can only answer things Reddit communities discuss."
        return {"answer": AnswerOutput(answer_markdown=reply, tldr=reply, grounded=False,
                                       refusal_reason=f"intent={plan.intent}")}
    gate = coverage_gate(state.get("retrieval"), state.get("signals", {}))
    if gate is not None:
        return {"answer": gate}  # honest refusal, 0 LLM calls
    try:
        ans = answer_agent(state["llm"], plan.standalone_question, state["pack"], state["messages"][:-1])
    except Exception as exc:
        logger.error("answer failed: %s", exc)
        return {"answer": AnswerOutput(answer_markdown="Something went wrong composing the answer.",
                                       grounded=False, refusal_reason="internal_error")}
    return {"answer": validate_citations(ans, state["pack"])}


# --- Assemble graph ---

workflow = StateGraph(AgentState)
workflow.add_node("understand", understand_node)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("answer", answer_node)
workflow.set_entry_point("understand")
workflow.add_edge("understand", "retrieve")
workflow.add_edge("retrieve", "answer")
workflow.add_edge("answer", END)
compiled_graph = workflow.compile()


NODE_MESSAGES = {
    "understand": "Understanding your question…",
    "retrieve": "Searching Reddit…",
    "answer": "Reading threads and answering…",
}


def _node_details(node: str, state: Dict[str, Any]) -> str:
    plan = state.get("plan")
    if node == "understand" and plan is not None:
        if plan.intent in SHORT_CIRCUIT_INTENTS:
            return f"Intent: {plan.intent}."
        return f"Intent: {plan.intent}. Looking for: '{plan.standalone_question}'"
    if node == "retrieve":
        result = state.get("retrieval")
        status = getattr(result, "status", None)
        pack = state.get("pack", [])
        if status in ("no_credentials", "error", "empty"):
            return f"Reddit status: {status}."
        n_threads = int(state.get("signals", {}).get("n_threads", 0))
        return f"Read {len(pack)} comments across {n_threads} threads."
    if node == "answer":
        ans = state.get("answer")
        if ans is not None and not ans.grounded:
            return "No confident Reddit coverage — answering honestly."
        return "Answer grounded in Reddit."
    return ""


class RedditAnswerEngine:
    """Runs the compiled LangGraph and streams progress, ending with a grounded answer."""

    def __init__(
        self,
        messages: List[Dict[str, str]],
        api_key: str = None,
        provider: str = None,
        model: str = None,
        reddit_creds: Optional[Dict[str, str]] = None,
        conversation_id: str = None,
    ):
        self.messages = messages
        self.conversation_id = conversation_id or str(uuid.uuid4())
        self.llm = LLMClient(provider=provider, api_key=api_key, model=model)
        self.reddit_creds = reddit_creds

    def run(self) -> Generator[Dict[str, Any], None, None]:
        state: Dict[str, Any] = {
            "llm": self.llm,
            "reddit_creds": self.reddit_creds,
            "messages": self.messages,
            "plan": None,
            "retrieval": None,
            "pack": [],
            "signals": {},
            "answer": None,
        }

        yield {"step": "understand", "status": "running",
               "message": NODE_MESSAGES["understand"], "details": "Reading your message…"}

        try:
            for update in compiled_graph.stream(state, stream_mode="updates"):
                for node_name, node_output in update.items():
                    if node_name == "__end__":
                        continue
                    state.update(node_output or {})
                    yield {"step": node_name, "status": "done",
                           "message": NODE_MESSAGES.get(node_name, node_name),
                           "details": _node_details(node_name, state)}
        except Exception as exc:
            logger.exception("Pipeline execution failed")
            yield {"step": "failed", "message": "Pipeline execution failed.", "details": str(exc)}
            return

        try:
            answer_data = self._build_answer(state)
        except Exception as exc:
            logger.exception("Failed to compile answer")
            yield {"step": "failed", "message": "Failed to compile the answer.", "details": str(exc)}
            return

        storage.save_report(answer_data)  # non-fatal if persistence unavailable
        yield {"step": "completed", "status": "done", "message": "Done.",
               "details": "Answer ready.", "data": answer_data}

    def _build_answer(self, state: Dict[str, Any]) -> Dict[str, Any]:
        ans: AnswerOutput = state["answer"]
        plan: QueryPlan = state["plan"]
        pack = state.get("pack", [])
        used = ans.used_citation_indices if ans.grounded else []
        citations = [c.model_dump() for c in build_citations(used, pack)]

        seen_urls, sources = set(), []
        if ans.grounded:
            for c in pack:
                url = c.get("post_url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    sources.append({"title": c.get("post_title") or "Reddit thread",
                                    "url": url, "subreddit": c.get("subreddit", "")})

        return {
            "id": str(uuid.uuid4()),
            "conversation_id": self.conversation_id,
            "query": self.messages[-1]["content"] if self.messages else "",
            "standalone_question": plan.standalone_question,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "llm_mode": "live" if self.llm.active else "simulated",
            "provider": self.llm.provider,
            "intent": plan.intent,
            "grounded": ans.grounded,
            "answer_markdown": ans.answer_markdown,
            "tldr": ans.tldr,
            "refusal_reason": ans.refusal_reason,
            "citations": citations,
            "sources": sources,
            "suggested_followups": ans.suggested_followups,
            "retrieval_status": getattr(state.get("retrieval"), "status", "demo"),
        }


if __name__ == "__main__":
    engine = RedditAnswerEngine([{"role": "user", "content": "Is a Tesla Model Y worth it?"}])
    for progress in engine.run():
        print(progress["step"], "-", progress.get("message", ""))
