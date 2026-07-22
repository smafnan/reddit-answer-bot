"""The two hot-path agents: understand the question, then answer from Reddit.

Both take the request-scoped LLMClient explicitly (no module-level LLM state).
Scraped Reddit content is wrapped in <untrusted> tags so the model treats it as
data, never as instructions.
"""

from typing import Any, Dict, List

from llm import LLMClient
from prompts import ANSWER_SYSTEM, PLAN_FEWSHOTS, PLAN_SYSTEM
from schemas import AnswerOutput, QueryPlan


def _untrusted(text: str) -> str:
    return f"<untrusted>\n{text}\n</untrusted>"


def _render_history(history: List[Dict[str, str]]) -> str:
    if not history:
        return "(no prior turns)"
    lines = []
    for m in history[-6:]:
        role = "User" if m.get("role") == "user" else "Assistant"
        lines.append(f"{role}: {m.get('content', '')}")
    return "\n".join(lines)


def understand_query_agent(llm: LLMClient, messages: List[Dict[str, str]]) -> QueryPlan:
    """Turn the latest message (+ history) into a retrieval plan (the 'understand' step)."""
    history = messages[:-1]
    current = messages[-1]["content"] if messages else ""
    user = (
        f"{PLAN_FEWSHOTS}\n\n"
        f"Conversation so far:\n{_render_history(history)}\n\n"
        f"Current user message: {current!r}\n\n"
        f"Return a QueryPlan JSON."
    )
    data = llm.call_structured(PLAN_SYSTEM + "\n\n" + user, QueryPlan)
    return QueryPlan(**data)


def answer_agent(
    llm: LLMClient,
    standalone_question: str,
    pack: List[Dict[str, Any]],
    history: List[Dict[str, str]],
) -> AnswerOutput:
    """Answer strictly from the numbered evidence pack (the 'answer' step)."""
    numbered = "\n\n".join(
        f"[{c['index']}] (r/{c['subreddit']}, {c['ups']} upvotes)\n{c['body']}" for c in pack
    )
    context = f"Conversation so far:\n{_render_history(history)}\n\n" if history else ""
    user = (
        f"{context}Question: {standalone_question}\n\n"
        f"Numbered Reddit comments:\n{_untrusted(numbered)}\n\n"
        f"Answer using ONLY these comments, with inline [n] citations. Return an AnswerOutput JSON."
    )
    data = llm.call_structured(ANSWER_SYSTEM + "\n\n" + user, AnswerOutput)
    return AnswerOutput(**data)
