"""
Output Validation Guardrails — SENTINEL Layer

Validates system-generated responses for:
  - Groundedness (claims backed by sources)
  - Data freshness (preventing stale information)
  - Citation accuracy and completeness
  - Response format compliance
  - Confidence score validity

Zero-hallucination policy: all claims must be grounded in retrieved data.
"""

from typing import Optional
from datetime import datetime, timedelta
from config.constants import WEATHER_FRESHNESS_HOURS
from models.pydantic_io import (
    EIRAResponse,
    SourceCitation,
    ChunkSource,
    GroundednessReport,
)
import logging
import re

logger = logging.getLogger(__name__)


def validate_response_grounding(
    response: EIRAResponse,
    sources: list[Optional[ChunkSource | dict]],
    min_confidence: float = 0.75,
) -> GroundednessReport:
    """
    Validate that all claims in response are grounded in sources.

    Implements SENTINEL layer zero-hallucination policy.

    Args:
        response: Generated EIRAResponse to validate
        sources: List of source citations backing the response
        min_confidence: Minimum acceptable confidence score

    Returns:
        GroundednessReport with validation results
    """
    ungrounded_claims = []
    citations = response.sources if response.sources else []

    # ────────────────────────────────────────────────────────────────────
    # 1. Check Response Has Sources
    # ────────────────────────────────────────────────────────────────────
    if not citations or len(citations) == 0:
        ungrounded_claims.append("Response has no source citations")
        passes = False
    else:
        passes = True

    # ────────────────────────────────────────────────────────────────────
    # 2. Extract Claims from Response
    # ────────────────────────────────────────────────────────────────────
    claim_sentences = _extract_claims(response.answer)

    # ────────────────────────────────────────────────────────────────────
    # 3. Validate Each Claim Against Sources
    # ────────────────────────────────────────────────────────────────────
    for claim in claim_sentences:
        is_grounded = False

        for citation in citations:
            if isinstance(citation, dict):
                citation = SourceCitation(**citation)

            # Check if claim is referenced in citation evidence
            if citation.evidence_ref in claim or claim in citation.claim:
                is_grounded = citation.grounded
                break

        if not is_grounded:
            ungrounded_claims.append(claim)
            passes = False

    # ────────────────────────────────────────────────────────────────────
    # 4. Check Confidence Threshold
    # ────────────────────────────────────────────────────────────────────
    confidence_ok = response.confidence >= min_confidence
    if not confidence_ok:
        passes = False

    # ────────────────────────────────────────────────────────────────────
    # 5. Check All Citations Have Confidence Scores
    # ────────────────────────────────────────────────────────────────────
    for citation in citations:
        if isinstance(citation, SourceCitation):
            if not (0.0 <= citation.grounded <= 1.0):
                ungrounded_claims.append(f"Invalid confidence in citation: {citation.evidence_ref}")
                passes = False

    logger.info(
        "Response grounding validation",
        extra={
            "passes": passes,
            "ungrounded_count": len(ungrounded_claims),
            "citation_count": len(citations),
            "confidence": response.confidence,
        }
    )

    return GroundednessReport(
        confidence=response.confidence,
        ungrounded_claims=ungrounded_claims,
        passes=passes and confidence_ok,
        freshness_ok=True,  # Checked separately
        citations=citations,
    )


def check_data_freshness(
    fetched_at: datetime,
    data_type: str = "weather",
    max_age_hours: Optional[int] = None,
) -> tuple[bool, Optional[str], int]:
    """
    Check if retrieved data is fresh (not stale).

    Args:
        fetched_at: Timestamp when data was retrieved
        data_type: Type of data (weather, news, sql)
        max_age_hours: Override maximum age (defaults from config)

    Returns:
        (is_fresh, reason_if_stale, hours_old)
    """
    if max_age_hours is None:
        # Use defaults based on data type
        if data_type == "weather":
            max_age_hours = WEATHER_FRESHNESS_HOURS
        elif data_type == "news":
            max_age_hours = 24
        elif data_type == "sql":
            max_age_hours = 0  # SQL data is always fresh
        else:
            max_age_hours = 6

    now = datetime.now(fetched_at.tzinfo) if fetched_at.tzinfo else datetime.now()

    try:
        age = now - fetched_at
        hours_old = int(age.total_seconds() / 3600)

        if hours_old > max_age_hours:
            reason = f"Data is {hours_old} hours old (max: {max_age_hours}h)"
            return False, reason, hours_old
        else:
            return True, None, hours_old

    except (TypeError, AttributeError) as e:
        logger.error(f"Freshness check error: {e}")
        return False, "Could not determine data age", -1


def validate_citations(
    citations: list[SourceCitation],
    require_all_grounded: bool = True,
) -> tuple[bool, list[str]]:
    """
    Validate citation format and completeness.

    Args:
        citations: List of citations to validate
        require_all_grounded: If True, all citations must be grounded=True

    Returns:
        (is_valid, list_of_errors)
    """
    errors = []

    # ────────────────────────────────────────────────────────────────────
    # 1. Check Citations Exist
    # ────────────────────────────────────────────────────────────────────
    if not citations:
        return False, ["Response must have at least one citation"]

    # ────────────────────────────────────────────────────────────────────
    # 2. Validate Each Citation
    # ────────────────────────────────────────────────────────────────────
    for i, citation in enumerate(citations):
        citation_errors = []

        # Check required fields
        if not citation.claim or len(citation.claim.strip()) == 0:
            citation_errors.append(f"Citation {i}: claim is empty")

        if not citation.evidence_ref or len(citation.evidence_ref.strip()) == 0:
            citation_errors.append(f"Citation {i}: evidence_ref is empty")

        # Check evidence_ref format
        if citation.evidence_ref:
            if not _is_valid_reference(citation.evidence_ref):
                citation_errors.append(f"Citation {i}: invalid reference format")

        # Check grounded flag
        if isinstance(citation.grounded, bool):
            if require_all_grounded and not citation.grounded:
                citation_errors.append(f"Citation {i}: not grounded (require_all_grounded=True)")
        else:
            citation_errors.append(f"Citation {i}: grounded must be boolean")

        errors.extend(citation_errors)

    # ────────────────────────────────────────────────────────────────────
    # 3. Check for Duplicate Citations
    # ────────────────────────────────────────────────────────────────────
    refs = [c.evidence_ref for c in citations]
    duplicates = [ref for ref in set(refs) if refs.count(ref) > 1]
    if duplicates:
        for dup in duplicates:
            errors.append(f"Duplicate citation: {dup}")

    logger.info(
        "Citations validated",
        extra={
            "citation_count": len(citations),
            "is_valid": len(errors) == 0,
            "error_count": len(errors),
        }
    )

    return len(errors) == 0, errors


def validate_response_format(response: EIRAResponse) -> tuple[bool, list[str]]:
    """
    Validate EIRAResponse format compliance.

    Returns:
        (is_valid, list_of_errors)
    """
    errors = []

    # ────────────────────────────────────────────────────────────────────
    # 1. Check Required Fields
    # ────────────────────────────────────────────────────────────────────
    if not response.answer or len(response.answer.strip()) == 0:
        errors.append("Response answer cannot be empty")

    # ────────────────────────────────────────────────────────────────────
    # 2. Check Answer Length
    # ────────────────────────────────────────────────────────────────────
    if len(response.answer) > 10000:
        errors.append("Response answer exceeds maximum length (10000 chars)")

    # ────────────────────────────────────────────────────────────────────
    # 3. Check Confidence
    # ────────────────────────────────────────────────────────────────────
    if not isinstance(response.confidence, (int, float)):
        errors.append("Confidence must be numeric")
    elif not (0.0 <= response.confidence <= 1.0):
        errors.append("Confidence must be between 0.0 and 1.0")

    # ────────────────────────────────────────────────────────────────────
    # 4. Check Model Used (if set)
    # ────────────────────────────────────────────────────────────────────
    if response.model_used:
        valid_models = {"claude-3-5-sonnet-20241022", "gpt-4o"}
        if response.model_used not in valid_models:
            errors.append(f"Unknown model: {response.model_used}")

    # ────────────────────────────────────────────────────────────────────
    # 5. Check Sources (if present)
    # ────────────────────────────────────────────────────────────────────
    if response.sources:
        sources_valid, source_errors = validate_citations(response.sources)
        errors.extend(source_errors)

    return len(errors) == 0, errors


# ────────────────────────────────────────────────────────────────────────
# Helper Functions
# ────────────────────────────────────────────────────────────────────────

def _extract_claims(text: str) -> list[str]:
    """
    Extract claim sentences from response text.

    Simple heuristic: split on periods and question marks, filter short fragments.
    """
    # Split on sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text)

    # Filter: remove very short fragments
    claims = [s.strip() for s in sentences if len(s.strip()) > 10]

    return claims


def _is_valid_reference(reference: str) -> bool:
    """
    Validate reference format.

    Accepted formats:
      - chunk_<uuid>: Chroma chunk ID
      - sql:employee_id:<id>: SQL record reference
    """
    valid_patterns = [
        r"^chunk_[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$",
        r"^sql:employee_id:\d+$",
    ]

    for pattern in valid_patterns:
        if re.match(pattern, reference):
            return True

    return False
