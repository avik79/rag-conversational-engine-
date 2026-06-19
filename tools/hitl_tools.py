"""Human-in-the-Loop gate tool — Production HITL system"""
from typing import Any, Optional
from datetime import datetime
import uuid
from models.pydantic_io import HITLDecision, HITLContext
import logging

logger = logging.getLogger(__name__)


class HITLGate:
    """Base class for HITL gates"""

    trigger_reason: str
    severity: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW"
    details: dict[str, Any]

    def __init__(self, trigger_reason: str, severity: str = "MEDIUM", details: dict = None):
        self.trigger_reason = trigger_reason
        self.severity = severity
        self.details = details or {}
        self.gate_id = str(uuid.uuid4())[:8]


class LowConfidenceGate(HITLGate):
    """HITL gate for low confidence responses"""
    def __init__(self, confidence: float, threshold: float = 0.75):
        super().__init__(
            trigger_reason="low_confidence",
            severity="HIGH" if confidence < 0.5 else "MEDIUM",
            details={
                "confidence": confidence,
                "threshold": threshold,
                "gap": threshold - confidence
            }
        )


class AmbiguousMatchGate(HITLGate):
    """HITL gate for ambiguous entity matches"""
    def __init__(self, entity_type: str, matches: list, confidence: float):
        super().__init__(
            trigger_reason="ambiguous_match",
            severity="HIGH",
            details={
                "entity_type": entity_type,
                "match_count": len(matches),
                "matches": matches,
                "confidence": confidence
            }
        )


class StaleDataGate(HITLGate):
    """HITL gate for stale data detection"""
    def __init__(self, fetched_at: datetime, age_hours: float, threshold_hours: int = 6):
        super().__init__(
            trigger_reason="stale_data",
            severity="MEDIUM" if age_hours < 24 else "HIGH",
            details={
                "fetched_at": fetched_at.isoformat() if isinstance(fetched_at, datetime) else str(fetched_at),
                "age_hours": age_hours,
                "threshold_hours": threshold_hours,
                "exceeds_by_hours": age_hours - threshold_hours
            }
        )


class LocationUnresolvedGate(HITLGate):
    """HITL gate for unresolved or fuzzy location matching"""
    def __init__(self, raw_location: str, confidence: float, candidates: list = None):
        super().__init__(
            trigger_reason="location_unresolved",
            severity="HIGH",
            details={
                "raw_location": raw_location,
                "confidence": confidence,
                "candidates": candidates or []
            }
        )


class SQLValidationGate(HITLGate):
    """HITL gate for SQL validation failures"""
    def __init__(self, query: str, issues: list[str]):
        super().__init__(
            trigger_reason="sql_blocked",
            severity="CRITICAL",
            details={
                "query": query[:200],
                "issues": issues
            }
        )


class ResponseValidationGate(HITLGate):
    """HITL gate for response validation failures"""
    def __init__(self, ungrounded_claims: list[str], confidence: float):
        super().__init__(
            trigger_reason="ungrounded_response",
            severity="CRITICAL",
            details={
                "ungrounded_claims": ungrounded_claims,
                "confidence": confidence
            }
        )


async def check_confidence_threshold(
    confidence: float,
    threshold: float = 0.75,
) -> Optional[HITLGate]:
    """Check if response confidence is below threshold"""
    if confidence < threshold:
        logger.warning(f"Low confidence detected: {confidence:.2f} < {threshold:.2f}")
        return LowConfidenceGate(confidence, threshold)
    return None


async def check_ambiguous_match(
    entity_type: str,
    matches: list,
    confidence: float,
    threshold: float = 0.85,
) -> Optional[HITLGate]:
    """Check if entity match is ambiguous"""
    if len(matches) > 1 and confidence < threshold:
        logger.warning(f"Ambiguous {entity_type} match: {len(matches)} candidates, confidence {confidence:.2f}")
        return AmbiguousMatchGate(entity_type, matches, confidence)
    return None


async def check_data_freshness(
    fetched_at: datetime,
    threshold_hours: int = 6,
) -> Optional[HITLGate]:
    """Check if data is stale"""
    from datetime import datetime as dt, timezone

    try:
        # Handle both datetime and string inputs
        if isinstance(fetched_at, str):
            fetched = dt.fromisoformat(fetched_at.replace("Z", "+00:00"))
        else:
            fetched = fetched_at

        now = dt.now(timezone.utc)
        if fetched.tzinfo is None:
            fetched = fetched.replace(tzinfo=timezone.utc)

        age_hours = (now - fetched).total_seconds() / 3600

        if age_hours > threshold_hours:
            logger.warning(f"Stale data detected: {age_hours:.1f}h > {threshold_hours}h threshold")
            return StaleDataGate(fetched, age_hours, threshold_hours)
    except Exception as e:
        logger.error(f"Error checking data freshness: {e}")

    return None


async def check_location_resolution(
    raw_location: str,
    confidence: float,
    candidates: list = None,
    threshold: float = 0.80,
) -> Optional[HITLGate]:
    """Check if location resolution needs clarification"""
    if confidence < threshold:
        logger.warning(f"Location resolution confidence low: {raw_location} ({confidence:.2f})")
        return LocationUnresolvedGate(raw_location, confidence, candidates)
    return None


async def check_sql_validation(
    query: str,
    issues: list[str],
) -> Optional[HITLGate]:
    """Check if SQL query has validation issues"""
    if issues:
        logger.error(f"SQL validation failed: {len(issues)} issues found")
        return SQLValidationGate(query, issues)
    return None


async def check_response_grounding(
    ungrounded_claims: list[str],
    confidence: float,
) -> Optional[HITLGate]:
    """Check if response has ungrounded claims"""
    if ungrounded_claims:
        logger.error(f"Ungrounded claims detected: {len(ungrounded_claims)}")
        return ResponseValidationGate(ungrounded_claims, confidence)
    return None


async def create_approval_request(
    gate: HITLGate,
) -> dict[str, Any]:
    """Create a human approval request from a HITL gate"""
    return {
        "gate_id": gate.gate_id,
        "trigger_reason": gate.trigger_reason,
        "severity": gate.severity,
        "details": gate.details,
        "timestamp": datetime.utcnow().isoformat(),
        "pending": True,
        "decision": None,
    }


async def hitl_gate(
    trigger_reason: str,
    context_data: dict[str, Any],
    needs_approval: bool = True,
) -> dict[str, Any]:
    """Legacy function for backward compatibility"""
    logger.info(f"HITL Gate triggered: {trigger_reason}")

    decision = HITLDecision(
        approved=False,
        reviewer_note=None,
    )

    return {
        "blocked": True,
        "reason": trigger_reason,
        "pending_approval": True,
        "decision": decision.model_dump(),
    }
