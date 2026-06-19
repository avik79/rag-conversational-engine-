"""Human-in-the-Loop gate tool"""
from typing import Any
from models.pydantic_io import HITLDecision, HITLContext


async def hitl_gate(
    trigger_reason: str,
    context_data: dict[str, Any],
    needs_approval: bool = True,
) -> dict[str, Any]:
    """Block execution pending human approval"""
    # In Phase 5 (Streamlit UI), this will be replaced with
    # actual human interaction via sidebar approval panel.
    # For now, return decision object with pending status.

    decision = HITLDecision(
        decision_id=None,  # Will be assigned by Streamlit session
        trigger_reason=trigger_reason,
        context=HITLContext(**context_data) if context_data else None,
        approved=False,
        approval_reason=None,
        timestamp=None,  # Will be set by Streamlit
    )

    return {
        "blocked": True,
        "reason": trigger_reason,
        "pending_approval": True,
        "decision": decision.model_dump(),
    }
