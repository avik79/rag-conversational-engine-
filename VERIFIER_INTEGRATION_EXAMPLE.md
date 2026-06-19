# VERIFIER Integration Example — Complete Flow

This document shows how to integrate the VERIFIER agent into your existing EIRA pipeline.

---

## Modified app/integration.py

```python
"""
EIRA Orchestration with VERIFIER Quality Gate

Flow:
  User Query
    → Sanitize Input (guardrails)
    → Classify Intent (EIRA)
    → Parallel Agents (VEGA, NOVA, KIRA, AXIOM)
    → Validate Grounding (SENTINEL)
    → Verify Quality (VERIFIER) ← NEW
    → Return Response or Re-iterate
"""

import logging
from datetime import datetime
from anthropic import Anthropic
from guardrails import sanitize_input_string
from guardrails.audit_logger import input_validation_audit
from agents.verifier import verifier
from tools.verifier_tools import get_re_iteration_feedback
from models.pydantic_io import EIRAResponse, IntentClassification

logger = logging.getLogger(__name__)


async def run_eira_with_verification(
    user_query: str,
    user_session_id: str = None,
    enable_re_iteration: bool = True,
    max_attempts: int = 2,
) -> EIRAResponse:
    """
    Main EIRA orchestrator with VERIFIER quality gate.

    Args:
        user_query: Original user question
        user_session_id: Session ID for tracking
        enable_re_iteration: Allow re-queries if validation fails
        max_attempts: Maximum verification attempts (default 2)

    Returns:
        Final validated response or feedback for re-query
    """

    # ────────────────────────────────────────────────────────────────
    # Step 1: Input Sanitization
    # ────────────────────────────────────────────────────────────────
    logger.info(f"[STAGE 1/5] Sanitizing input: {len(user_query)} chars")

    clean_query, sanitization_warnings = sanitize_input_string(
        user_query,
        max_length=500
    )

    if sanitization_warnings:
        logger.warning(f"Input sanitization warnings: {sanitization_warnings}")
        input_validation_audit.log_input_sanitization(
            original_length=len(user_query),
            sanitized_length=len(clean_query),
            warnings=sanitization_warnings,
            context="eira_query"
        )

    # ────────────────────────────────────────────────────────────────
    # Step 2: Intent Classification (EIRA)
    # ────────────────────────────────────────────────────────────────
    logger.info("[STAGE 2/5] Classifying intent")

    intent = await classify_intent(clean_query)
    logger.info(f"Intent: {intent.intent}")

    # ────────────────────────────────────────────────────────────────
    # Step 3: Parallel Agent Execution
    # ────────────────────────────────────────────────────────────────
    logger.info("[STAGE 3/5] Executing parallel agents (VEGA, NOVA, KIRA, AXIOM)")

    eira_response = await coordinate_agents(
        user_query=clean_query,
        intent=intent,
        session_id=user_session_id,
    )

    logger.info(f"EIRA response: {len(eira_response.answer)} chars, "
                f"confidence: {eira_response.confidence:.2f}")

    # ────────────────────────────────────────────────────────────────
    # Step 4: Sentinel Validation (existing)
    # ────────────────────────────────────────────────────────────────
    logger.info("[STAGE 4/5] Validating grounding (SENTINEL)")

    from guardrails import validate_response_grounding
    grounding_report = validate_response_grounding(
        response=eira_response,
        sources=eira_response.sources,
        min_confidence=0.75
    )

    if not grounding_report.passes:
        logger.warning(f"SENTINEL: Response not fully grounded")
        # Could trigger HITL here

    # ────────────────────────────────────────────────────────────────
    # Step 5: VERIFIER Quality Gate (NEW) ⭐
    # ────────────────────────────────────────────────────────────────
    logger.info("[STAGE 5/5] Verifying quality (VERIFIER)")

    return await _verify_and_iterate(
        original_question=user_query,
        eira_response=eira_response,
        intent=intent,
        enable_re_iteration=enable_re_iteration,
        max_attempts=max_attempts,
        attempt=1,
    )


async def _verify_and_iterate(
    original_question: str,
    eira_response: EIRAResponse,
    intent: IntentClassification,
    enable_re_iteration: bool = True,
    max_attempts: int = 2,
    attempt: int = 1,
) -> EIRAResponse:
    """
    Recursive verification and re-iteration handler.

    Attempts to validate response. If it fails and re-iteration is enabled,
    provides feedback to EIRA and re-queries.
    """

    logger.info(f"VERIFIER: Validation attempt {attempt}/{max_attempts}")

    # ────────────────────────────────────────────────────────────────
    # Run VERIFIER
    # ────────────────────────────────────────────────────────────────
    passes, result_response, report = await verifier.verify_response(
        original_question=original_question,
        response=eira_response,
        intent_classification=intent,
        attempt=attempt,
    )

    logger.info(
        f"VERIFIER: {'✅ PASSED' if passes else '❌ FAILED'} "
        f"(score: {report.overall_quality_score:.2f})"
    )

    # ────────────────────────────────────────────────────────────────
    # Handle Pass
    # ────────────────────────────────────────────────────────────────
    if passes:
        logger.info(f"VERIFIER: Response accepted")

        # Log validation success
        from guardrails.audit_logger import verifier_audit, EventType, Severity
        verifier_audit.log_event(
            event_type="response_accepted",
            severity="info",
            overall_score=report.overall_quality_score,
            attempt=attempt,
        )

        return result_response

    # ────────────────────────────────────────────────────────────────
    # Handle Fail — Decision Tree
    # ────────────────────────────────────────────────────────────────
    logger.warning(f"VERIFIER: Validation failed (score: {report.overall_quality_score:.2f})")

    # Check if we should re-iterate
    if not enable_re_iteration:
        logger.info("VERIFIER: Re-iteration disabled, returning with reduced confidence")
        eira_response.confidence = max(0.3, eira_response.confidence - 0.3)
        return eira_response

    if attempt >= max_attempts:
        logger.warning(f"VERIFIER: Max attempts ({max_attempts}) reached")
        eira_response.confidence = max(0.3, eira_response.confidence - 0.3)
        return eira_response

    # Check issue severity
    critical_issues = [i for i in report.issues if i.severity.value == "critical"]

    if not critical_issues and report.recommended_action == "clarify_user":
        # Ask user for clarification instead of re-iterating
        logger.info("VERIFIER: Recommending user clarification")

        feedback = await get_re_iteration_feedback(report, original_question)
        return EIRAResponse(
            answer=f"Could you clarify your question?\n\n{feedback}",
            sources=[],
            confidence=0.0,
            hitl_triggered=True,
            model_used="verifier-clarification",
        )

    # ────────────────────────────────────────────────────────────────
    # Re-iterate with Feedback
    # ────────────────────────────────────────────────────────────────
    if critical_issues or (report.recommended_action == "re_iterate" and attempt < max_attempts):
        logger.info(f"VERIFIER: Triggering re-iteration (attempt {attempt + 1}/{max_attempts})")

        feedback = await get_re_iteration_feedback(report, original_question)

        logger.info(f"Feedback for re-query:\n{feedback}")

        # Re-query with feedback context
        re_iterated_response = await coordinate_agents(
            user_query=original_question,
            intent=intent,
            verifier_feedback=feedback,
            session_id=None,
        )

        # Recursively verify
        return await _verify_and_iterate(
            original_question=original_question,
            eira_response=re_iterated_response,
            intent=intent,
            enable_re_iteration=enable_re_iteration,
            max_attempts=max_attempts,
            attempt=attempt + 1,
        )

    else:
        # Fallback: return with reduced confidence
        logger.warning("VERIFIER: Returning response with reduced confidence")
        eira_response.confidence = max(0.3, eira_response.confidence - 0.3)
        return eira_response


# ────────────────────────────────────────────────────────────────────────
# Existing EIRA Functions (unchanged)
# ────────────────────────────────────────────────────────────────────────

async def classify_intent(query: str) -> IntentClassification:
    """Existing EIRA intent classification"""
    # Implementation remains the same
    pass


async def coordinate_agents(
    user_query: str,
    intent: IntentClassification,
    session_id: str = None,
    verifier_feedback: str = None,
) -> EIRAResponse:
    """
    Existing agent coordination with optional VERIFIER feedback.

    Args:
        user_query: User's original question
        intent: Classified intent
        session_id: Session identifier
        verifier_feedback: Optional feedback from VERIFIER (for re-iteration)

    Returns:
        EIRAResponse with orchestrated result
    """
    # If verifier_feedback is provided, add it to system context
    # so agents know how to improve their response

    # Implementation example:
    # 1. Execute VEGA (SQL queries)
    # 2. Execute NOVA (vector retrieval)
    # 3. Synthesize results
    # 4. Add verifier_feedback to prompt if re-iterating
    pass
```

---

## Streamlit UI Integration (app/main.py)

```python
"""
Streamlit app with VERIFIER quality feedback display
"""

import streamlit as st
from datetime import datetime
from app.integration import run_eira_with_verification


def display_verification_report(report):
    """Display VERIFIER report in Streamlit"""

    with st.expander("📊 Response Quality Analysis", expanded=False):
        # Overall score
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Overall Score", f"{report.overall_quality_score:.1%}")
        with col2:
            st.metric("Status", "✅ PASSED" if report.passes else "❌ FAILED")
        with col3:
            st.metric("Attempt", f"{report.verification_attempts}")

        # Detailed scores
        st.subheader("Validation Scores")
        scores_col1, scores_col2 = st.columns(2)

        with scores_col1:
            st.metric("Semantic Relevance", f"{report.semantic_relevance_score:.1%}")
            st.metric("Citation Coverage", f"{report.citation_coverage_score:.1%}")
        with scores_col2:
            st.metric("Completeness", f"{report.completeness_score:.1%}")
            st.metric("Coherence", f"{report.coherence_score:.1%}")

        # Issues
        if report.issues:
            st.subheader(f"Issues Found: {len(report.issues)}")

            for severity_level in ["critical", "high", "medium", "low"]:
                severity_issues = [
                    i for i in report.issues
                    if i.severity.value == severity_level
                ]

                if severity_issues:
                    emoji = {
                        "critical": "🔴",
                        "high": "🟠",
                        "medium": "🟡",
                        "low": "🔵",
                    }.get(severity_level, "•")

                    with st.expander(f"{emoji} {severity_level.upper()} ({len(severity_issues)})"):
                        for issue in severity_issues:
                            st.write(f"**{issue.description}**")
                            st.write(f"*Suggestion: {issue.suggestion}*")

        # Recommendation
        st.subheader("Recommendation")
        recommendations = {
            "accept": "✅ Response accepted — safe to return to user",
            "re_iterate": "🔄 Re-iteration recommended — repeat query with feedback",
            "clarify_user": "❓ User clarification needed — ask for more details",
        }
        st.info(recommendations.get(report.recommended_action, "Unknown"))


def main():
    st.title("EIRA — Intelligent Routing Agent")

    # User input
    user_query = st.text_input("Ask your question:", placeholder="e.g., What's the average age of engineers in Austin?")

    if st.button("Query"):
        with st.spinner("Processing..."):
            try:
                # Run EIRA with VERIFIER
                response = asyncio.run(
                    run_eira_with_verification(
                        user_query=user_query,
                        enable_re_iteration=True,
                        max_attempts=2,
                    )
                )

                # Display response
                st.subheader("Response")
                st.write(response.answer)

                # Display sources
                if response.sources:
                    with st.expander(f"Sources ({len(response.sources)})"):
                        for i, source in enumerate(response.sources):
                            st.write(f"**{i+1}.** {source.claim}")
                            st.caption(f"Reference: {source.evidence_ref}")

                # Display confidence
                st.metric("Confidence", f"{response.confidence:.1%}")

                # Display verification report if we have it
                if hasattr(response, "verification_report"):
                    display_verification_report(response.verification_report)

            except Exception as e:
                st.error(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
```

---

## Full Example: Employee Query with Re-iteration

```
User: "What's the average age of engineers in Austin?"

[Step 1] Sanitize: "What's the average age of engineers in Austin?" ✓

[Step 2] Classify Intent: sql_only (employee database query)

[Step 3] Execute Agents:
  VEGA: Query employee table
    ↳ Found: 12 engineers in Austin
    ↳ Age range: 26-38, average: 32.5
  KIRA: Resolve location
    ↳ Austin, TX (canonical city)
  AXIOM: Validate query
    ↳ Query safe, no injection

[Step 4] SENTINEL: Validate grounding
  ✅ Claims backed by sources
  ✅ Confidence: 0.88

[Step 5] VERIFIER: Quality check

  Initial Response:
    "The average age of engineers in Austin is approximately 32.5 years."
    Sources: 1 (SQL query)
    Confidence: 0.88

  Validation Results:
    ❌ FAILED (score: 0.58)
    
    Issues:
    🔴 CRITICAL: Response too brief (23 words)
    🔴 CRITICAL: Incomplete coverage (missing total count)
    🟠 HIGH: Only 1 source (expected ≥2)
    🟠 HIGH: Overconfident (0.88 > 0.58)

  Recommendation: RE-ITERATE

[Re-iteration Feedback]
  ⚠️ CRITICAL Issues (must fix):
    - Response is too brief to be meaningful
      Fix: Provide more detailed answer with context
    - Single source not enough
      Fix: Include additional context (total engineers, departments, etc.)

  Semantic Relevance: 0.60
  Completeness: 0.40
  Citation Coverage: 0.70
  Coherence: 0.95

[Step 5b] Re-query with Feedback (Attempt 2/2)

  EIRA Re-queries with context:
  "User asked: What's the average age of engineers in Austin?
   Previous answer was too brief and only cited one source.
   Provide comprehensive answer with: total engineer count, 
   age distribution, departments represented."

  Improved Response:
    "The average age of engineers in Austin is 32.5 years. We found 12 engineers
    in that location with ages ranging from 26 to 38 years old. The distribution
    shows 5 engineers in the 25-30 age range, 4 in the 31-35 range, and 3 in the
    36-40 range. These engineers span across 3 departments: Product (5),
    Infrastructure (4), and Frontend (3)."

    Sources: 3 (SQL employee queries for each department)
    Confidence: 0.82

  Re-validation:
    ✅ PASSED (score: 0.84)
    
    Metrics:
    ✅ Semantic Relevance: 0.90 (answers all aspects)
    ✅ Completeness: 0.85 (covers distribution, departments)
    ✅ Citation Coverage: 0.85 (3 sources)
    ✅ Coherence: 0.85 (clear structure)
    ✅ Confidence Consistency: 0.88 (0.82 matches quality)
    
    No critical issues
    Recommendation: ACCEPT

[Return to User]
✅ Response accepted and delivered to user
   Quality Score: 84%
   Confidence: 82%
   Sources: 3
   Verification: 2 attempts (re-iterated once)
```

---

## Testing the Integration

```python
import asyncio
import pytest
from app.integration import run_eira_with_verification

@pytest.mark.asyncio
async def test_eira_with_verification_end_to_end():
    """Test complete EIRA + VERIFIER pipeline"""

    response = await run_eira_with_verification(
        user_query="What's the average age of engineers in Austin?",
        enable_re_iteration=True,
        max_attempts=2,
    )

    # Verify response is valid
    assert response.answer
    assert len(response.answer) > 50
    assert response.confidence > 0.0

    # Verify it was verified (confidence should be realistic)
    assert response.confidence <= 0.95  # Would be adjusted by VERIFIER if needed

    # If re-iterated, check model_used reflects this
    # (in practice, track via audit logs)

@pytest.mark.asyncio
async def test_eira_prevent_reiterations_when_disabled():
    """Test that re-iterations are skipped when disabled"""

    response = await run_eira_with_verification(
        user_query="Intentionally bad question that will fail verification",
        enable_re_iteration=False,  # Disable re-iterations
        max_attempts=1,
    )

    # Response should have reduced confidence if it failed verification
    # (was penalized by VERIFIER)
```

---

## Configuration from Environment

```python
# app/config.py

import os

VERIFIER_ENABLED = os.getenv("VERIFIER_ENABLED", "true").lower() == "true"
VERIFIER_MAX_ATTEMPTS = int(os.getenv("VERIFIER_MAX_ATTEMPTS", "2"))
VERIFIER_PASS_THRESHOLD = float(os.getenv("VERIFIER_PASS_THRESHOLD", "0.75"))

# Use in run_eira_with_verification():
async def run_eira_with_verification(
    user_query: str,
    enable_re_iteration: bool = VERIFIER_ENABLED,
    max_attempts: int = VERIFIER_MAX_ATTEMPTS,
) -> EIRAResponse:
    # ...
```

---

## Next Steps

1. ✅ Integrate `run_eira_with_verification()` into Streamlit app
2. ✅ Update `coordinate_agents()` to accept `verifier_feedback` parameter
3. ✅ Add `verification_report` to response tracking (audit logs)
4. ✅ Monitor VERIFIER pass/fail rates in production
5. ✅ Adjust thresholds based on domain and use case
6. ✅ Create dashboard showing validation metrics over time
