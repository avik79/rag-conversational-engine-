"""HITL audit logging and decision tracking"""
from datetime import datetime
from typing import Any, Optional
import json
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class HITLAuditLog:
    """Audit log for HITL decisions and gate triggers"""

    def __init__(self, log_dir: str = "./logs/hitl"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.session_log_file = self._get_session_log_path()

    def _get_session_log_path(self) -> Path:
        """Get today's session log file path"""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        return self.log_dir / f"hitl_audit_{today}.jsonl"

    def log_gate_triggered(
        self,
        gate_id: str,
        trigger_reason: str,
        severity: str,
        details: dict,
        context_data: Optional[dict] = None,
    ) -> None:
        """Log when a HITL gate is triggered"""
        entry = {
            "event_type": "gate_triggered",
            "timestamp": datetime.utcnow().isoformat(),
            "gate_id": gate_id,
            "trigger_reason": trigger_reason,
            "severity": severity,
            "details": details,
            "context_data": context_data,
        }
        self._write_log(entry)
        logger.info(f"HITL gate logged: {trigger_reason} (severity: {severity})")

    def log_decision_made(
        self,
        gate_id: str,
        trigger_reason: str,
        approved: bool,
        reviewer_id: Optional[str] = None,
        reviewer_note: Optional[str] = None,
    ) -> None:
        """Log human decision on a HITL gate"""
        entry = {
            "event_type": "decision_made",
            "timestamp": datetime.utcnow().isoformat(),
            "gate_id": gate_id,
            "trigger_reason": trigger_reason,
            "approved": approved,
            "reviewer_id": reviewer_id,
            "reviewer_note": reviewer_note,
        }
        self._write_log(entry)
        status = "approved" if approved else "denied"
        logger.info(f"HITL decision logged: {trigger_reason} - {status}")

    def log_auto_approved(
        self,
        gate_id: str,
        trigger_reason: str,
        reason: str,
    ) -> None:
        """Log auto-approval of a HITL gate"""
        entry = {
            "event_type": "auto_approved",
            "timestamp": datetime.utcnow().isoformat(),
            "gate_id": gate_id,
            "trigger_reason": trigger_reason,
            "reason": reason,
        }
        self._write_log(entry)
        logger.info(f"HITL auto-approved: {trigger_reason} - {reason}")

    def log_auto_denied(
        self,
        gate_id: str,
        trigger_reason: str,
        reason: str,
    ) -> None:
        """Log auto-denial of a HITL gate"""
        entry = {
            "event_type": "auto_denied",
            "timestamp": datetime.utcnow().isoformat(),
            "gate_id": gate_id,
            "trigger_reason": trigger_reason,
            "reason": reason,
        }
        self._write_log(entry)
        logger.error(f"HITL auto-denied: {trigger_reason} - {reason}")

    def _write_log(self, entry: dict) -> None:
        """Write entry to JSONL log file"""
        try:
            with open(self.session_log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write HITL audit log: {e}")

    def get_session_summary(self) -> dict[str, Any]:
        """Get summary of today's HITL activity"""
        summary = {
            "gates_triggered": 0,
            "decisions_made": 0,
            "approved": 0,
            "denied": 0,
            "auto_approved": 0,
            "auto_denied": 0,
            "triggers_by_reason": {},
        }

        if not self.session_log_file.exists():
            return summary

        try:
            with open(self.session_log_file, "r") as f:
                for line in f:
                    entry = json.loads(line)
                    event_type = entry.get("event_type")

                    if event_type == "gate_triggered":
                        summary["gates_triggered"] += 1
                        reason = entry.get("trigger_reason")
                        summary["triggers_by_reason"][reason] = (
                            summary["triggers_by_reason"].get(reason, 0) + 1
                        )
                    elif event_type == "decision_made":
                        summary["decisions_made"] += 1
                        if entry.get("approved"):
                            summary["approved"] += 1
                        else:
                            summary["denied"] += 1
                    elif event_type == "auto_approved":
                        summary["auto_approved"] += 1
                    elif event_type == "auto_denied":
                        summary["auto_denied"] += 1

        except Exception as e:
            logger.error(f"Failed to read HITL audit log: {e}")

        return summary

    def get_gate_decision_rate(self) -> dict[str, Any]:
        """Get approval/denial rate by gate type"""
        rates = {}

        if not self.session_log_file.exists():
            return rates

        gate_stats = {}

        try:
            with open(self.session_log_file, "r") as f:
                for line in f:
                    entry = json.loads(line)
                    if entry.get("event_type") == "decision_made":
                        reason = entry.get("trigger_reason")
                        if reason not in gate_stats:
                            gate_stats[reason] = {"approved": 0, "denied": 0}

                        if entry.get("approved"):
                            gate_stats[reason]["approved"] += 1
                        else:
                            gate_stats[reason]["denied"] += 1

            for reason, stats in gate_stats.items():
                total = stats["approved"] + stats["denied"]
                rates[reason] = {
                    "total": total,
                    "approved": stats["approved"],
                    "denied": stats["denied"],
                    "approval_rate": stats["approved"] / total if total > 0 else 0,
                }

        except Exception as e:
            logger.error(f"Failed to calculate decision rates: {e}")

        return rates


# Global audit log instance
_audit_log: Optional[HITLAuditLog] = None


def get_audit_log() -> HITLAuditLog:
    """Get or create global audit log instance"""
    global _audit_log
    if _audit_log is None:
        _audit_log = HITLAuditLog()
    return _audit_log
