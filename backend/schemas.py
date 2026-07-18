"""Pydantic schemas for structured LLM outputs.

These are used both to instruct the model (JSON schema embedded in the system
prompt) and to VALIDATE what comes back — responses that don't conform are
rejected and replaced with simulated fallback data instead of silently
corrupting the report.
"""

from typing import List

from pydantic import BaseModel, Field


class QueryExpansionOutput(BaseModel):
    queries: List[str] = Field(description="List of 6-10 alternative search queries covering multiple angles.")


class CommentEvaluation(BaseModel):
    index: int = Field(description="The index of the comment being evaluated.")
    is_spam_or_low_effort: bool = Field(description="True if the comment is spam, a joke, bot-like, deleted, or lacks useful substance.")
    quality_score: float = Field(description="Quality score (0.0 to 1.0) based on detail, evidence, and credibility.")
    reason: str = Field(description="Short reason for the score.")


class BatchCommentEvaluation(BaseModel):
    evaluations: List[CommentEvaluation]


class PerspectiveSummary(BaseModel):
    name: str = Field(description="Name of the perspective, e.g. 'Software Engineer', 'Hobbyist'.")
    consensus: str = Field(description="Synthesized opinion of this perspective.")
    supporting_points: List[str] = Field(description="Bullet points detailing their main arguments.")


class PerspectiveAndContradictionOutput(BaseModel):
    perspectives: List[PerspectiveSummary] = Field(description="Different perspective segments present in the discussion.")
    contradictions: List[str] = Field(description="Key disagreements or conflicting opinions found between comments.")


class EntityNode(BaseModel):
    id: str = Field(description="Unique identifier for the node (e.g. 'rtx-4090'). Use lowercase kebab-case.")
    label: str = Field(description="Display label of the node (e.g. 'RTX 4090').")
    type: str = Field(description="Type/category of the node (e.g. 'Hardware', 'Software', 'Concept', 'Organization').")


class EntityEdge(BaseModel):
    source: str = Field(description="The source node id.")
    target: str = Field(description="The target node id.")
    label: str = Field(description="The relationship description (e.g. 'runs', 'alternative to', 'requires').")


class KnowledgeGraphOutput(BaseModel):
    nodes: List[EntityNode] = Field(description="Entities mentioned in the discussions.")
    edges: List[EntityEdge] = Field(description="Relationships between those entities.")


class FactCheckClaim(BaseModel):
    claim: str = Field(description="The key technical claim made in the comments.")
    status: str = Field(description="Verification status: 'Verified', 'Disputed', 'Debunked', or 'Unverified'.")
    explanation: str = Field(description="Explanation verifying or debunking the claim based on search evidence.")
    source_link: str = Field(default="", description="URL to the page confirming or disputing this claim.")


class FactCheckOutput(BaseModel):
    facts_checked: List[FactCheckClaim]


class IntelligenceReport(BaseModel):
    consensus_summary: str = Field(description="The primary community consensus across all comments, as one comprehensive paragraph.")
    confidence_score: float = Field(description="Confidence score (0.0 to 1.0) based on source strength and agreement.")
    detailed_synthesis: str = Field(description="Thorough markdown-formatted synthesis detailing insights, evidence, and contrary opinions.")
