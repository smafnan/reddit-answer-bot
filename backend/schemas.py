"""Structured LLM output contracts for the Reddit Answer Engine.

Two shapes on the hot path:
  QueryPlan   — output of the "understand" step (intent + retrieval plan).
  AnswerOutput — output of the "answer" step (grounded answer + citations).

Both are validated against these schemas; anything that doesn't conform is
rejected and replaced with a simulated fallback rather than corrupting a reply.
"""

from typing import List, Literal

from pydantic import BaseModel, Field

Intent = Literal["answerable", "follow_up", "greeting", "off_topic", "needs_clarification"]


class QueryPlan(BaseModel):
    """Turns a raw (possibly follow-up) message into a Reddit retrieval plan.

    'follow_up' is retrieved just like 'answerable', but signals that
    standalone_question was rewritten from prior turns (pronouns/ellipsis
    resolved) — this is the "understand context like Google" step.
    """

    intent: Intent = Field(description="Classification of the user's latest message.")
    standalone_question: str = Field(
        default="",
        description="The information need as a fully self-contained question, with pronouns and ellipsis resolved from conversation history.",
    )
    search_queries: List[str] = Field(
        default_factory=list,
        description="3-6 Reddit search query strings hitting distinct surfaces (literal keywords, natural Reddit phrasing, problem/symptom form, 'X vs Y'). Empty for non-answerable intents.",
    )
    subreddits: List[str] = Field(
        default_factory=list,
        description="0-5 subreddit names (no 'r/' prefix) likely to hold the discussion. Only ones you are confident exist — never invent subreddits.",
    )
    recency_sensitive: bool = Field(
        default=False,
        description="True for products/tech/prices where recent threads matter; False for timeless how-to/advice.",
    )
    is_reddit_suitable: bool = Field(
        default=True,
        description="False when the question cannot meaningfully be answered from community discussion (real-time facts, private/personal data, pure math).",
    )
    direct_reply: str = Field(
        default="",
        description="For greeting/off_topic/needs_clarification only: the short text to return WITHOUT retrieval or fabricated sources.",
    )


class Citation(BaseModel):
    """A single cited Reddit comment, deep-linked when possible."""

    index: int = Field(description="1-based citation number, stable within one answer.")
    thread_title: str = ""
    permalink: str = Field(default="", description="Comment-level deep link when available, else the thread URL.")
    subreddit: str = ""
    author: str = ""
    snippet: str = Field(default="", description="Verbatim excerpt from the cited comment.")
    ups: int = 0
    created_utc: float = 0.0


class AnswerOutput(BaseModel):
    """The answer step's output. grounded/refusal_reason carry the honesty contract."""

    answer_markdown: str = Field(
        default="",
        description="Markdown answer; every factual sentence ends with one or more [n] markers referencing the numbered evidence pack.",
    )
    tldr: str = Field(default="", description="1-2 sentence direct answer, also carrying inline [n] markers.")
    used_citation_indices: List[int] = Field(default_factory=list)
    suggested_followups: List[str] = Field(default_factory=list)
    grounded: bool = Field(
        default=True,
        description="False when the retrieved comments do not actually answer the question.",
    )
    refusal_reason: str = Field(default="")
