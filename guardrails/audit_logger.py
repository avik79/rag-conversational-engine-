"""
Audit Logger — Compliance & Security Logging

Logs all security-relevant events for audit trails:
  - Query validation (passed/blocked)
  - Data access patterns
  - Errors and exceptions
  - Guardrail triggers
  - HITL decisions

Structured logging format enables compliance reporting and security analysis.
"""

import logging
import json
from datetime import datetime
from typing import Any, Optional, Dict
from enum import Enum


class EventType(str, Enum):
    """Audit event types"""
    QUERY_VALIDATED = "query_validated"
    QUERY_BLOCKED = "query_blocked"
    INPUT_SANITIZED = "input_sanitized"
    INJECTION_ATTEMPT = "injection_attempt"
    VALIDATION_FAILED = "validation_failed"
    RESPONSE_GROUNDED = "response_grounded"
    RESPONSE_UNGROUNDED = "response_ungrounded"
    FRESHNESS_CHECK = "freshness_check"
    HITL_TRIGGERED = "hitl_triggered"
    DATA_ACCESS = "data_access"
    ERROR = "error"


class Severity(str, Enum):
    """Event severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditLogger:
    """
    Structured audit logger for security events.

    Usage:
        audit_log = AuditLogger(__name__)
        audit_log.log_event(
            event_type=EventType.QUERY_BLOCKED,
            severity=Severity.WARNING,
            query_hash="abc123...",
            reason="Dangerous keyword detected"
        )
    """

    def __init__(self, module_name: str):
        """Initialize audit logger for module"""
        self.logger = logging.getLogger(f"audit.{module_name}")
        self.module_name = module_name

    def log_event(
        self,
        event_type: EventType,
        severity: Severity,
        details: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """
        Log structured audit event.

        Args:
            event_type: Type of security event
            severity: Severity level
            details: Additional event details
            **kwargs: Additional fields (will be included in log)
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type.value,
            "severity": severity.value,
            "module": self.module_name,
            **kwargs,
        }

        if details:
            event["details"] = details

        # Log based on severity
        if severity == Severity.CRITICAL:
            self.logger.critical(json.dumps(event))
        elif severity == Severity.ERROR:
            self.logger.error(json.dumps(event))
        elif severity == Severity.WARNING:
            self.logger.warning(json.dumps(event))
        else:
            self.logger.info(json.dumps(event))

    def log_query_validation(
        self,
        is_valid: bool,
        is_blocked: bool,
        query_hash: str,
        issues: Optional[list[str]] = None,
    ) -> None:
        """Log query validation result"""
        event_type = EventType.QUERY_VALIDATED if is_valid else EventType.QUERY_BLOCKED

        severity = Severity.WARNING if is_blocked else Severity.INFO

        self.log_event(
            event_type=event_type,
            severity=severity,
            query_hash=query_hash,
            is_valid=is_valid,
            is_blocked=is_blocked,
            issues=issues or [],
        )

    def log_injection_attempt(
        self,
        pattern_detected: str,
        input_sample: str,
        context: str,
    ) -> None:
        """Log suspected injection attempt"""
        self.log_event(
            event_type=EventType.INJECTION_ATTEMPT,
            severity=Severity.CRITICAL,
            pattern_detected=pattern_detected,
            input_hash=hash(input_sample),  # Hash for privacy
            context=context,
        )

    def log_input_sanitization(
        self,
        original_length: int,
        sanitized_length: int,
        warnings: Optional[list[str]] = None,
        context: str = "unknown",
    ) -> None:
        """Log input sanitization operation"""
        self.log_event(
            event_type=EventType.INPUT_SANITIZED,
            severity=Severity.INFO,
            original_length=original_length,
            sanitized_length=sanitized_length,
            warnings_count=len(warnings) if warnings else 0,
            warnings=warnings or [],
            context=context,
        )

    def log_validation_failure(
        self,
        validation_type: str,
        errors: list[str],
        context: str = "unknown",
    ) -> None:
        """Log validation failure"""
        severity = Severity.WARNING if len(errors) < 3 else Severity.ERROR

        self.log_event(
            event_type=EventType.VALIDATION_FAILED,
            severity=severity,
            validation_type=validation_type,
            error_count=len(errors),
            errors=errors,
            context=context,
        )

    def log_response_grounding(
        self,
        is_grounded: bool,
        confidence: float,
        ungrounded_claims: Optional[list[str]] = None,
        citation_count: int = 0,
    ) -> None:
        """Log response grounding check (SENTINEL layer)"""
        event_type = (
            EventType.RESPONSE_GROUNDED
            if is_grounded
            else EventType.RESPONSE_UNGROUNDED
        )

        severity = Severity.WARNING if not is_grounded else Severity.INFO

        self.log_event(
            event_type=event_type,
            severity=severity,
            is_grounded=is_grounded,
            confidence=confidence,
            ungrounded_claims_count=len(ungrounded_claims) if ungrounded_claims else 0,
            ungrounded_claims=ungrounded_claims or [],
            citation_count=citation_count,
        )

    def log_freshness_check(
        self,
        is_fresh: bool,
        data_type: str,
        hours_old: int,
        max_age_hours: int,
    ) -> None:
        """Log data freshness check"""
        severity = Severity.WARNING if not is_fresh else Severity.INFO

        self.log_event(
            event_type=EventType.FRESHNESS_CHECK,
            severity=severity,
            is_fresh=is_fresh,
            data_type=data_type,
            hours_old=hours_old,
            max_age_hours=max_age_hours,
        )

    def log_hitl_trigger(
        self,
        trigger_reason: str,
        agent_name: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log human-in-the-loop approval trigger"""
        self.log_event(
            event_type=EventType.HITL_TRIGGERED,
            severity=Severity.WARNING,
            trigger_reason=trigger_reason,
            agent_name=agent_name,
            session_id=session_id,
            context=context or {},
        )

    def log_data_access(
        self,
        access_type: str,  # "select", "insert", "update", "delete"
        resource: str,      # Table/collection name
        row_count: int,
        filters_applied: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log data access pattern"""
        self.log_event(
            event_type=EventType.DATA_ACCESS,
            severity=Severity.INFO,
            access_type=access_type,
            resource=resource,
            row_count=row_count,
            filters_applied=filters_applied or {},
        )

    def log_error(
        self,
        error_message: str,
        error_type: str,
        context: str = "unknown",
        traceback: Optional[str] = None,
    ) -> None:
        """Log error with context"""
        self.log_event(
            event_type=EventType.ERROR,
            severity=Severity.ERROR,
            error_message=error_message,
            error_type=error_type,
            context=context,
            traceback=traceback,
        )


# ────────────────────────────────────────────────────────────────────────
# Module-level convenience functions
# ────────────────────────────────────────────────────────────────────────

# Create module-level loggers for common components
sql_safety_audit = AuditLogger("sql_safety")
input_validation_audit = AuditLogger("input_validation")
output_validation_audit = AuditLogger("output_validation")
schema_enforcement_audit = AuditLogger("schema_enforcement")
