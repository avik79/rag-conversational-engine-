"""
VERIFIER Agent Tools — Response Validation & Quality Assurance

The VERIFIER agent validates that the final EIRA response adequately addresses
the original user question through:

  1. Semantic Relevance — Does response content match question intent?
  2. Completeness — Are all question aspects covered?
  3. Citation Coverage — Is response adequately grounded?
  4. Coherence — Is response logically structured?
  5. Confidence — Does confidence score reflect quality?

If validation fails, VERIFIER triggers re-iteration with specific feedback.

Reference: CLAUDE.md § VERIFIER Agent
"""

from typing import Optional, Any, Dict
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from models.pydantic_io import (
    EIRAResponse,
    IntentClassification,
    SourceCitation,
)
from guardrails.audit_logger import AuditLogger
import logging

logger = logging.getLogger(__name__)
verifier_audit = AuditLogger("verifier")


class ValidationSeverity(str, Enum):
    """Severity of validation issues"""
    CRITICAL = "critical"      # Must re-iterate
    HIGH = "high"              # Strong recommendation to re-iterate
    MEDIUM = "medium"          # Consider re-iteration
    LOW = "low"                # Minor issue, not blocking


class ValidationIssue(BaseModel):
    """Single validation issue found"""
    type: str                   # e.g., "incomplete_coverage", "low_confidence"
    severity: ValidationSeverity
    description: str            # Human-readable explanation
    suggestion: str             # How to fix
    affected_area: Optional[str] = None  # What part of response is affected


class VerificationReport(BaseModel):
    """Complete VERIFIER validation report"""
    passes: bool                            # Overall validation result
    timestamp: datetime = Field(default_factory=datetime.now)

    # Core metrics
    semantic_relevance_score: float = Field(ge=0.0, le=1.0)
    completeness_score: float = Field(ge=0.0, le=1.0)
    citation_coverage_score: float = Field(ge=0.0, le=1.0)
    coherence_score: float = Field(ge=0.0, le=1.0)
    overall_quality_score: float = Field(ge=0.0, le=1.0)

    # Issues and recommendations
    issues: list[ValidationIssue]
    verification_attempts: int = 1
    recommended_action: str     # "accept", "re_iterate", "clarify_user"

    # Traceability
    question_hash: Optional[str] = None
    response_hash: Optional[str] = None


# ────────────────────────────────────────────────────────────────────────
# Validation Functions
# ────────────────────────────────────────────────────────────────────────

async def validate_response_against_question(
    original_question: str,
    response: EIRAResponse,
    intent_classification: IntentClassification,
) -> VerificationReport:
    """
    Comprehensive response validation against original question.

    Args:
        original_question: User's original query
        response: EIRA's final response
        intent_classification: EIRA's intent classification

    Returns:
        VerificationReport with validation scores and issues
    """
    issues = []
    scores = {}

    # ────────────────────────────────────────────────────────────────────
    # 1. Semantic Relevance Check
    # ────────────────────────────────────────────────────────────────────
    relevance_score, relevance_issues = await _check_semantic_relevance(
        original_question,
        response.answer,
        intent_classification
    )
    scores["semantic_relevance"] = relevance_score
    issues.extend(relevance_issues)

    # ────────────────────────────────────────────────────────────────────
    # 2. Completeness Check
    # ────────────────────────────────────────────────────────────────────
    completeness_score, completeness_issues = await _check_completeness(
        original_question,
        response.answer,
        response.sources
    )
    scores["completeness"] = completeness_score
    issues.extend(completeness_issues)

    # ────────────────────────────────────────────────────────────────────
    # 3. Citation Coverage Check
    # ────────────────────────────────────────────────────────────────────
    citation_score, citation_issues = await _check_citation_coverage(
        response.answer,
        response.sources
    )
    scores["citation_coverage"] = citation_score
    issues.extend(citation_issues)

    # ────────────────────────────────────────────────────────────────────
    # 4. Coherence Check
    # ────────────────────────────────────────────────────────────────────
    coherence_score, coherence_issues = await _check_coherence(response.answer)
    scores["coherence"] = coherence_score
    issues.extend(coherence_issues)

    # ────────────────────────────────────────────────────────────────────
    # 5. Confidence Consistency Check
    # ────────────────────────────────────────────────────────────────────
    confidence_score, confidence_issues = await _check_confidence_consistency(
        response.confidence,
        scores,
        response.answer
    )
    scores["confidence_consistency"] = confidence_score
    issues.extend(confidence_issues)

    # ────────────────────────────────────────────────────────────────────
    # Calculate Overall Score
    # ────────────────────────────────────────────────────────────────────
    overall_score = _calculate_overall_score(scores)

    # ────────────────────────────────────────────────────────────────────
    # Determine Pass/Fail
    # ────────────────────────────────────────────────────────────────────
    critical_issues = [i for i in issues if i.severity == ValidationSeverity.CRITICAL]
    high_issues = [i for i in issues if i.severity == ValidationSeverity.HIGH]

    passes = len(critical_issues) == 0 and overall_score >= 0.75

    # ────────────────────────────────────────────────────────────────────
    # Recommend Action
    # ────────────────────────────────────────────────────────────────────
    if passes:
        recommended_action = "accept"
    elif len(critical_issues) > 0:
        recommended_action = "re_iterate"
    elif len(high_issues) >= 2:
        recommended_action = "re_iterate"
    elif overall_score < 0.6:
        recommended_action = "re_iterate"
    else:
        recommended_action = "clarify_user"

    # ────────────────────────────────────────────────────────────────────
    # Log Verification
    # ────────────────────────────────────────────────────────────────────
    verifier_audit.log_event(
        event_type="response_verified",
        severity="info",
        passes=passes,
        overall_score=overall_score,
        critical_issues=len(critical_issues),
        high_issues=len(high_issues),
        total_issues=len(issues),
        recommendation=recommended_action,
    )

    return VerificationReport(
        passes=passes,
        semantic_relevance_score=scores.get("semantic_relevance", 0.0),
        completeness_score=scores.get("completeness", 0.0),
        citation_coverage_score=scores.get("citation_coverage", 0.0),
        coherence_score=scores.get("coherence", 0.0),
        overall_quality_score=overall_score,
        issues=issues,
        recommended_action=recommended_action,
        question_hash=str(hash(original_question)),
        response_hash=str(hash(response.answer)),
    )


# ────────────────────────────────────────────────────────────────────────
# Sub-Validation Functions
# ────────────────────────────────────────────────────────────────────────

async def _check_semantic_relevance(
    question: str,
    answer: str,
    intent: IntentClassification,
) -> tuple[float, list[ValidationIssue]]:
    """
    Check if response answer matches the semantic intent of the question.

    Returns:
        (relevance_score: 0.0-1.0, issues: list)
    """
    issues = []

    # ── Basic length check ──
    if len(answer) < 20:
        issues.append(ValidationIssue(
            type="too_short",
            severity=ValidationSeverity.HIGH,
            description="Response is too brief to be meaningful",
            suggestion="Provide more detailed answer with context",
            affected_area="overall"
        ))
        return 0.4, issues

    if len(answer) > 5000:
        issues.append(ValidationIssue(
            type="too_long",
            severity=ValidationSeverity.MEDIUM,
            description="Response exceeds reasonable length",
            suggestion="Summarize and focus on key points",
            affected_area="overall"
        ))
        return 0.6, issues

    # ── Check for off-topic signals ──
    off_topic_signals = [
        "i don't know",
        "not sure",
        "unable to",
        "cannot find",
        "no information",
    ]

    answer_lower = answer.lower()
    off_topic_count = sum(1 for signal in off_topic_signals if signal in answer_lower)

    if off_topic_count > 2:
        issues.append(ValidationIssue(
            type="off_topic",
            severity=ValidationSeverity.CRITICAL,
            description="Response indicates inability to answer the question",
            suggestion="Re-query with different search terms or clarify the question",
            affected_area="overall"
        ))
        return 0.2, issues

    # ── Intent-specific checks ──
    relevance_score = 0.85  # Default good score

    if intent.intent == "sql_only":
        if "employee" not in answer_lower and "department" not in answer_lower:
            issues.append(ValidationIssue(
                type="intent_mismatch",
                severity=ValidationSeverity.HIGH,
                description="SQL query intent not reflected in employee data answer",
                suggestion="Ensure answer discusses retrieved employee records",
                affected_area="overall"
            ))
            relevance_score = 0.5

    elif intent.intent == "rag_only":
        if len(answer.split()) < 30:  # RAG answers should be more substantial
            issues.append(ValidationIssue(
                type="insufficient_synthesis",
                severity=ValidationSeverity.MEDIUM,
                description="RAG answer lacks sufficient synthesis from sources",
                suggestion="Provide more detailed synthesis of retrieved information",
                affected_area="overall"
            ))
            relevance_score = 0.65

    elif intent.intent == "cross_domain":
        # Should synthesize both SQL and RAG data
        has_employee_mention = "employee" in answer_lower or "department" in answer_lower
        has_context_mention = any(w in answer_lower for w in ["weather", "news", "info", "report"])

        if not (has_employee_mention and has_context_mention):
            issues.append(ValidationIssue(
                type="incomplete_domain_coverage",
                severity=ValidationSeverity.MEDIUM,
                description="Cross-domain response missing integration across data sources",
                suggestion="Synthesize both employee and contextual information",
                affected_area="overall"
            ))
            relevance_score = 0.65

    return relevance_score, issues


async def _check_completeness(
    question: str,
    answer: str,
    sources: Optional[list[SourceCitation]] = None,
) -> tuple[float, list[ValidationIssue]]:
    """
    Check if response covers all aspects of the question.

    Returns:
        (completeness_score: 0.0-1.0, issues: list)
    """
    issues = []
    completeness_score = 0.8

    # ── Check for sources ──
    if not sources or len(sources) == 0:
        issues.append(ValidationIssue(
            type="no_sources",
            severity=ValidationSeverity.HIGH,
            description="Response has no source citations",
            suggestion="Add citations from retrieved data",
            affected_area="sources"
        ))
        completeness_score -= 0.3

    elif len(sources) == 1:
        issues.append(ValidationIssue(
            type="single_source",
            severity=ValidationSeverity.MEDIUM,
            description="Response relies on only one source",
            suggestion="Incorporate multiple sources for balanced coverage",
            affected_area="sources"
        ))
        completeness_score -= 0.1

    # ── Check for question mark handling ──
    question_has_multiple_parts = sum(q.count("?") for q in [question]) > 1

    if question_has_multiple_parts:
        # Multi-part questions should be explicitly addressed
        paragraph_count = len(answer.split("\n\n"))
        if paragraph_count < 2:
            issues.append(ValidationIssue(
                type="multi_part_incomplete",
                severity=ValidationSeverity.MEDIUM,
                description="Multi-part question not fully addressed in structured way",
                suggestion="Use separate paragraphs/sections for each question aspect",
                affected_area="structure"
            ))
            completeness_score -= 0.15

    # ── Check for summary/conclusion ──
    answer_sentences = answer.split(".")
    has_conclusion = any(word in answer_sentences[-1].lower()
                        for word in ["summary", "conclusion", "overall", "in summary", "therefore"])

    if not has_conclusion and len(answer_sentences) > 3:
        issues.append(ValidationIssue(
            type="missing_conclusion",
            severity=ValidationSeverity.LOW,
            description="Response lacks concluding summary",
            suggestion="Add brief summary or conclusion at the end",
            affected_area="structure"
        ))
        completeness_score -= 0.05

    return max(0.0, min(1.0, completeness_score)), issues


async def _check_citation_coverage(
    answer: str,
    sources: Optional[list[SourceCitation]] = None,
) -> tuple[float, list[ValidationIssue]]:
    """
    Check if response sources are adequately distributed and properly cited.

    Returns:
        (citation_score: 0.0-1.0, issues: list)
    """
    issues = []
    citation_score = 0.8

    if not sources:
        issues.append(ValidationIssue(
            type="no_citations",
            severity=ValidationSeverity.CRITICAL,
            description="Response has no source citations",
            suggestion="Every claim must have a source",
            affected_area="citations"
        ))
        return 0.0, issues

    # ── Check citation-to-source ratio ──
    claim_sentences = [s.strip() for s in answer.split(".") if len(s.strip()) > 20]
    citation_count = len(sources)

    if citation_count == 0:
        issues.append(ValidationIssue(
            type="zero_citations",
            severity=ValidationSeverity.CRITICAL,
            description="No citation sources provided",
            suggestion="Retrieve and cite sources",
            affected_area="citations"
        ))
        return 0.0, issues

    citation_ratio = min(1.0, citation_count / len(claim_sentences)) if claim_sentences else 0.0

    if citation_ratio < 0.4:
        issues.append(ValidationIssue(
            type="low_citation_ratio",
            severity=ValidationSeverity.HIGH,
            description=f"Only {citation_count} citations for {len(claim_sentences)} claims",
            suggestion="Ensure majority of claims are cited",
            affected_area="citations"
        ))
        citation_score = 0.5

    # ── Check all citations are grounded ──
    ungrounded_count = sum(1 for s in sources if not s.grounded)
    if ungrounded_count > 0:
        issues.append(ValidationIssue(
            type="ungrounded_citations",
            severity=ValidationSeverity.CRITICAL,
            description=f"{ungrounded_count} citations marked as ungrounded",
            suggestion="Remove ungrounded claims",
            affected_area="citations"
        ))
        citation_score = 0.3

    return max(0.0, min(1.0, citation_score)), issues


async def _check_coherence(answer: str) -> tuple[float, list[ValidationIssue]]:
    """
    Check if response is logically structured and coherent.

    Returns:
        (coherence_score: 0.0-1.0, issues: list)
    """
    issues = []
    coherence_score = 0.85

    # ── Check sentence length variation ──
    sentences = [s.strip() for s in answer.split(".") if s.strip()]

    if not sentences:
        issues.append(ValidationIssue(
            type="no_sentences",
            severity=ValidationSeverity.CRITICAL,
            description="Response contains no complete sentences",
            suggestion="Structure response as complete sentences",
            affected_area="structure"
        ))
        return 0.0, issues

    sentence_lengths = [len(s.split()) for s in sentences]
    avg_length = sum(sentence_lengths) / len(sentence_lengths) if sentence_lengths else 0
    max_length = max(sentence_lengths) if sentence_lengths else 0

    # Check for very long run-on sentences
    if max_length > 40:
        issues.append(ValidationIssue(
            type="run_on_sentences",
            severity=ValidationSeverity.LOW,
            description="Some sentences are very long and complex",
            suggestion="Break long sentences into shorter, simpler sentences",
            affected_area="readability"
        ))
        coherence_score -= 0.1

    # Check for topic consistency
    first_sentence = sentences[0].lower()
    middle_sentence = sentences[len(sentences)//2].lower() if len(sentences) > 2 else first_sentence

    # Simple check: do they share keywords?
    first_words = set(first_sentence.split())
    middle_words = set(middle_sentence.split())
    keyword_overlap = len(first_words & middle_words)

    if keyword_overlap < 2 and len(sentences) > 3:
        issues.append(ValidationIssue(
            type="topic_drift",
            severity=ValidationSeverity.MEDIUM,
            description="Response appears to drift topics between sentences",
            suggestion="Maintain focus on central topic throughout",
            affected_area="coherence"
        ))
        coherence_score -= 0.15

    return max(0.0, min(1.0, coherence_score)), issues


async def _check_confidence_consistency(
    reported_confidence: float,
    quality_scores: Dict[str, float],
    answer: str,
) -> tuple[float, list[ValidationIssue]]:
    """
    Check if reported confidence aligns with actual response quality.

    Returns:
        (consistency_score: 0.0-1.0, issues: list)
    """
    issues = []

    # Calculate average quality score
    avg_quality = sum(quality_scores.values()) / len(quality_scores) if quality_scores else 0.5

    # Check for confidence drift
    confidence_drift = abs(reported_confidence - avg_quality)

    consistency_score = 1.0 - confidence_drift

    if confidence_drift > 0.3:
        if reported_confidence > avg_quality:
            issues.append(ValidationIssue(
                type="overconfident",
                severity=ValidationSeverity.MEDIUM,
                description=f"Reported confidence ({reported_confidence:.2f}) exceeds quality score ({avg_quality:.2f})",
                suggestion="Lower confidence score or improve response quality",
                affected_area="confidence"
            ))
        else:
            issues.append(ValidationIssue(
                type="underconfident",
                severity=ValidationSeverity.LOW,
                description=f"Reported confidence ({reported_confidence:.2f}) below quality score ({avg_quality:.2f})",
                suggestion="Consider raising confidence if quality is high",
                affected_area="confidence"
            ))

    return max(0.0, min(1.0, consistency_score)), issues


def _calculate_overall_score(scores: Dict[str, float]) -> float:
    """
    Calculate weighted overall quality score.

    Weights:
      - semantic_relevance: 30% (most important)
      - completeness: 25%
      - citation_coverage: 25%
      - coherence: 15%
      - confidence_consistency: 5%
    """
    weights = {
        "semantic_relevance": 0.30,
        "completeness": 0.25,
        "citation_coverage": 0.25,
        "coherence": 0.15,
        "confidence_consistency": 0.05,
    }

    total = 0.0
    for key, weight in weights.items():
        score = scores.get(key, 0.0)
        total += score * weight

    return round(total, 3)


async def get_re_iteration_feedback(
    report: VerificationReport,
    original_question: str,
) -> str:
    """
    Generate specific feedback for re-iteration based on validation issues.

    Returns:
        Structured feedback string for EIRA to use in re-iteration
    """
    feedback_lines = [
        f"Response validation score: {report.overall_quality_score:.2f}/1.0",
        f"Issues found: {len(report.issues)}",
        "",
        "Detailed feedback:"
    ]

    # Group issues by severity
    critical = [i for i in report.issues if i.severity == ValidationSeverity.CRITICAL]
    high = [i for i in report.issues if i.severity == ValidationSeverity.HIGH]
    medium = [i for i in report.issues if i.severity == ValidationSeverity.MEDIUM]

    if critical:
        feedback_lines.append("\n⚠️ CRITICAL Issues (must fix):")
        for issue in critical:
            feedback_lines.append(f"  - {issue.description}")
            feedback_lines.append(f"    Fix: {issue.suggestion}")

    if high:
        feedback_lines.append("\n⚠️ HIGH Priority Issues:")
        for issue in high:
            feedback_lines.append(f"  - {issue.description}")
            feedback_lines.append(f"    Fix: {issue.suggestion}")

    if medium:
        feedback_lines.append("\n💡 MEDIUM Priority Improvements:")
        for issue in medium:
            feedback_lines.append(f"  - {issue.description}")
            feedback_lines.append(f"    Suggestion: {issue.suggestion}")

    feedback_lines.append(f"\nScores breakdown:")
    feedback_lines.append(f"  Semantic Relevance: {report.semantic_relevance_score:.2f}")
    feedback_lines.append(f"  Completeness: {report.completeness_score:.2f}")
    feedback_lines.append(f"  Citation Coverage: {report.citation_coverage_score:.2f}")
    feedback_lines.append(f"  Coherence: {report.coherence_score:.2f}")

    feedback_lines.append(f"\nRecommended action: {report.recommended_action.upper()}")

    if report.recommended_action == "re_iterate":
        feedback_lines.append(f"\nPlease re-query with the original question and address the issues above.")

    return "\n".join(feedback_lines)
