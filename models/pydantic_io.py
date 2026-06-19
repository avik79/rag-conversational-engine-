"""
Pydantic I/O Schemas — All Agent Input/Output Models

All structured outputs defined once, imported by all agents.
These schemas enforce type safety and enable JSON schema validation.

Reference: handoff.md §1.3
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime


# ── EIRA (Executive Intelligence Routing Agent) ──────────────────────

class IntentClassification(BaseModel):
    """EIRA's intent classification of user query"""
    intent: Literal["sql_only", "rag_only", "cross_domain", "meta", "unclear"]
    sql_subquery: Optional[str] = None  # NL sub-query for VEGA
    rag_subquery: Optional[str] = None  # NL sub-query for NOVA
    requires_hitl: bool = False
    reasoning: str  # EIRA's chain-of-thought (not shown to user)


class SourceCitation(BaseModel):
    """Citation of evidence for a claim"""
    claim: str
    evidence_ref: str  # chunk_id or "sql:employee_id:{id}"
    grounded: bool


class EIRAResponse(BaseModel):
    """Final orchestrated response to user"""
    answer: str
    sources: list[SourceCitation]
    confidence: float = Field(ge=0.0, le=1.0)
    hitl_triggered: bool = False
    model_used: str  # "claude-sonnet-4-5" or "gpt-4o"


# ── VEGA (Verified Employee & Geo-data Agent) ────────────────────────

class EmployeeRow(BaseModel):
    """Single employee record"""
    employee_id: int
    name: str
    age: int
    department: str
    office_location: str  # canonical city string


class EmployeeQueryResult(BaseModel):
    """Result of SQL query against employee table"""
    employees: list[EmployeeRow]
    query_sql: str  # the generated SQL (for audit)
    row_count: int
    confidence: float = Field(ge=0.0, le=1.0)
    ambiguous_match: bool = False  # True if >1 employee matched name


# ── NOVA (Neural Observation & Vector Analysis Agent) ───────────────

class ChunkSource(BaseModel):
    """Citation of a vector chunk for grounding"""
    chunk_id: str
    collection: Literal["weather_embeddings", "news_embeddings"]
    location_normalized: Optional[str] = None  # None for news
    fetched_at: datetime
    relevance_score: float


class RAGResponse(BaseModel):
    """Grounded RAG synthesis with citations"""
    synthesis: str
    sources: list[ChunkSource]
    freshness_ok: bool  # False if fetched_at > 6h old
    confidence: float = Field(ge=0.0, le=1.0)


# ── KIRA (Knowledge & Intent Resolution Agent) ───────────────────────

class LocationResolution(BaseModel):
    """Result of location resolution (exact/fuzzy/semantic)"""
    raw_input: str
    canonical_key: str  # e.g. "Austin, TX"
    confidence: float = Field(ge=0.0, le=1.0)
    match_method: Literal["exact", "fuzzy", "semantic", "failed"]
    needs_clarification: bool = False


# ── AXIOM (Automated Query Integrity & Oversight Monitor) ──────────

class ValidationResult(BaseModel):
    """Pre-execution query validation result"""
    is_valid: bool
    is_blocked: bool
    issues: list[str]
    safe_to_execute: bool
    query_type: Literal["sql", "chroma_filter"]


# ── SENTINEL (Semantic Evidence & Narrative Truth Integrity Evaluator) ──

class GroundednessReport(BaseModel):
    """Post-generation response validation"""
    confidence: float = Field(ge=0.0, le=1.0)
    ungrounded_claims: list[str]
    passes: bool
    freshness_ok: bool
    citations: list[SourceCitation]


# ── HITL Gate ────────────────────────────────────────────────────────

class HITLContext(BaseModel):
    """Context for human-in-the-loop approval"""
    trigger_reason: Literal[
        "low_confidence",
        "location_unresolved",
        "stale_data",
        "ambiguous_match",
        "sql_blocked",
        "ungrounded_response",
        "reingestion_overwrite",
    ]
    draft_response: Optional[str] = None
    ungrounded_claims: list[str] = []
    agent_name: str
    session_id: str


class HITLDecision(BaseModel):
    """Human reviewer's decision"""
    approved: bool
    reviewer_note: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    reviewer_id: Optional[str] = None


class HITLApprovalRequest(BaseModel):
    """Human approval request with full context"""
    gate_id: str
    trigger_reason: str
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    details: dict
    timestamp: datetime
    pending: bool = True
    decision: Optional[HITLDecision] = None
    context_data: Optional[dict] = None


# ── IRIS (Ingestion & Real-time Intelligence Sync Agent) ────────────

class EmbeddingChunk(BaseModel):
    """Vector embedding chunk for ingestion"""
    chunk_id: str
    text: str
    embedding: list[float]
    collection: Literal["weather_embeddings", "news_embeddings"]
    metadata: dict  # must include location_normalized for weather


class IngestionReport(BaseModel):
    """Report on ingestion batch results"""
    chunks_ingested: int
    chunks_rejected: int
    rejection_reasons: list[str]
    location_contract_violations: list[str]
    ingestion_timestamp: datetime


# ── VERIFIER (Verification & Validation Agent) ────────────────────────

class ValidationIssue(BaseModel):
    """Single validation issue found by VERIFIER"""
    issue_type: str                    # e.g., "incomplete_coverage", "low_confidence"
    severity: Literal["critical", "high", "medium", "low"]
    description: str                   # Human-readable explanation
    suggestion: str                    # How to fix the issue
    affected_area: Optional[str] = None


class VerificationReport(BaseModel):
    """Complete VERIFIER validation report"""
    passes: bool                                        # Overall validation result
    timestamp: datetime = Field(default_factory=datetime.now)

    # Core quality metrics (0.0-1.0)
    semantic_relevance_score: float = Field(ge=0.0, le=1.0)
    completeness_score: float = Field(ge=0.0, le=1.0)
    citation_coverage_score: float = Field(ge=0.0, le=1.0)
    coherence_score: float = Field(ge=0.0, le=1.0)
    overall_quality_score: float = Field(ge=0.0, le=1.0)

    # Issues and recommendations
    issues: list[ValidationIssue] = []
    verification_attempts: int = 1
    recommended_action: Literal["accept", "re_iterate", "clarify_user"]

    # Traceability
    question_hash: Optional[str] = None
    response_hash: Optional[str] = None
