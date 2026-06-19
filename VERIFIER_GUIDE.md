# VERIFIER Agent — Implementation & Integration Guide

## Overview

**VERIFIER** is the quality assurance gate in the EIRA pipeline. It validates that final responses adequately address the original user question through comprehensive quality scoring and issue detection.

```
User Question
    ↓
[EIRA Orchestrator] → VEGA, NOVA, KIRA, AXIOM
    ↓
[VERIFIER] ← Validation & Quality Checks
    ↓
    ├─→ ✅ ACCEPT → Return to user
    ├─→ 🔄 RE-ITERATE → Request improved response
    └─→ ❓ CLARIFY → Ask user for clarification
```

---

## Architecture

### VERIFIER Components

```
verifier/
├── tools/verifier_tools.py
│   ├── validate_response_against_question()
│   ├── get_re_iteration_feedback()
│   ├── _check_semantic_relevance()
│   ├── _check_completeness()
│   ├── _check_citation_coverage()
│   ├── _check_coherence()
│   ├── _check_confidence_consistency()
│   └── VerificationReport (Pydantic model)
│
├── agents/verifier.py
│   ├── VERIFIERAgent class
│   ├── verify_response()
│   ├── check_response_quality()
│   └── get_validation_summary()
│
└── models/pydantic_io.py (updated)
    ├── ValidationIssue
    └── VerificationReport
```

---

## Validation Metrics

The VERIFIER evaluates responses across 5 dimensions:

### 1. **Semantic Relevance** (30% weight)
Does the response answer match the semantic intent of the question?

**Checks:**
- ✅ Response length (20–5000 chars)
- ✅ Off-topic signals ("I don't know", "unable to")
- ✅ Intent-specific validation:
  - SQL queries: mentions employee/department data
  - RAG queries: substantive synthesis (≥30 words)
  - Cross-domain: integrates both SQL and RAG results

**Score Range:** 0.0–1.0

---

### 2. **Completeness** (25% weight)
Are all aspects of the question covered?

**Checks:**
- ✅ Source citations provided (minimum 1)
- ✅ Multi-part questions addressed structurally (separate paragraphs)
- ✅ Concluding summary present
- ✅ Citation count proportional to claims

**Score Range:** 0.0–1.0

---

### 3. **Citation Coverage** (25% weight)
Is the response adequately grounded in sources?

**Checks:**
- ✅ Sources exist (critical if missing)
- ✅ Citation-to-claim ratio ≥ 0.4
- ✅ All citations marked as grounded (no ungrounded claims)
- ✅ Source count (≥1, ideally ≥3)

**Score Range:** 0.0–1.0

---

### 4. **Coherence** (15% weight)
Is the response logically structured and easy to follow?

**Checks:**
- ✅ Complete sentences (no fragments)
- ✅ Sentence length variation (avoid run-ons >40 words)
- ✅ Topic consistency (keyword overlap between sentences)
- ✅ Logical flow

**Score Range:** 0.0–1.0

---

### 5. **Confidence Consistency** (5% weight)
Does reported confidence align with actual response quality?

**Checks:**
- ✅ Confidence drift < 0.3 from average quality
- ✅ Not overconfident (confidence > quality)
- ✅ Not underconfident (confidence << quality)

**Score Range:** 0.0–1.0

---

## Validation Decision Logic

### Pass Criteria
✅ **ACCEPT** if:
- Overall quality score ≥ 0.75 AND
- No CRITICAL issues

### Fail Criteria
🔴 **RE-ITERATE** if:
- CRITICAL issues present OR
- ≥2 HIGH priority issues OR
- Overall quality < 0.60

### Clarify Criteria
❓ **CLARIFY** if:
- Validation fails but not due to response quality
- Recommendation: ask user to rephrase question

---

## Issue Severity Levels

| Severity | Triggers Re-iteration | Example |
|----------|----------------------|---------|
| **CRITICAL** | Immediately | No citations, off-topic, intent mismatch |
| **HIGH** | If ≥2 found | Low citation ratio, too short |
| **MEDIUM** | Advisory | Single source, no conclusion |
| **LOW** | Informational | Long sentences, minor improvements |

---

## Core Functions

### 1. Main Validation

```python
from agents.verifier import verifier
from models.pydantic_io import EIRAResponse, IntentClassification

# Validate response
passes, response_or_feedback, report = await verifier.verify_response(
    original_question="What's the average age of engineers?",
    response=eira_response,
    intent_classification=intent,
    attempt=1,
)

if passes:
    print("✅ Response accepted")
else:
    print("🔄 Re-iteration needed:")
    print(response_or_feedback.answer)  # Feedback for re-query
```

### 2. Quick Quality Check

```python
# Check response quality without full validation
metrics = await verifier.check_response_quality(eira_response)

print(f"Has sources: {metrics['has_sources']}")
print(f"Quality OK: {metrics['quality_ok']}")
print(f"Confidence: {metrics['confidence_score']:.2f}")
```

### 3. Generate Summary

```python
# User-friendly validation summary
summary = await verifier.get_validation_summary(report)
print(summary)

# Output:
# ════════════════════════════════════════
# RESPONSE QUALITY ASSESSMENT
# ════════════════════════════════════════
# Overall Quality Score: 82.5%
# Status: ✅ PASSED
#
# Detailed Scores:
#   • Semantic Relevance:   85.0%
#   • Completeness:         80.0%
#   • Citation Coverage:    90.0%
#   • Coherence:            85.0%
# ════════════════════════════════════════
```

### 4. Tool-Level Validation

```python
from tools.verifier_tools import (
    validate_response_against_question,
    get_re_iteration_feedback,
)

# Detailed validation
report = await validate_response_against_question(
    original_question=user_query,
    response=eira_response,
    intent_classification=intent,
)

# Get feedback for re-iteration
if not report.passes:
    feedback = await get_re_iteration_feedback(report, user_query)
    print(feedback)
```

---

## Integration with EIRA Pipeline

### Modified app/integration.py Flow

```python
from agents.verifier import verifier

async def run_eira_with_verification(user_query: str) -> EIRAResponse:
    """EIRA pipeline with VERIFIER quality gate"""

    # ────────────────────────────────────────────────────────────────
    # 1. EIRA Orchestration (existing)
    # ────────────────────────────────────────────────────────────────
    intent = await classify_intent(user_query)
    eira_response = await coordinate_agents(user_query, intent)

    # ────────────────────────────────────────────────────────────────
    # 2. VERIFIER Validation (NEW)
    # ────────────────────────────────────────────────────────────────
    passes, validated_response, report = await verifier.verify_response(
        original_question=user_query,
        response=eira_response,
        intent_classification=intent,
        attempt=1,
    )

    if passes:
        # ✅ Validation passed
        logger.info(f"VERIFIER: Response accepted (score: {report.overall_quality_score})")
        return validated_response

    else:
        # 🔄 Validation failed - Handle re-iteration
        logger.warning(f"VERIFIER: Validation failed (score: {report.overall_quality_score})")

        # Get feedback
        feedback = await get_re_iteration_feedback(report, user_query)

        # Option 1: Return feedback asking EIRA to re-query
        if report.recommended_action == "re_iterate":
            logger.info("VERIFIER: Requesting re-iteration")

            # Re-iterate with feedback context
            re_iterated = await coordinate_agents(
                user_query=user_query,
                intent=intent,
                verifier_feedback=feedback,
                attempt=2,
            )

            # Validate again (but limit attempts to 2)
            passes2, final_response, report2 = await verifier.verify_response(
                original_question=user_query,
                response=re_iterated,
                intent_classification=intent,
                attempt=2,
            )

            if passes2:
                logger.info("VERIFIER: Re-iteration succeeded")
                return final_response
            else:
                logger.warning("VERIFIER: Re-iteration still failed, returning with reduced confidence")
                # Return response with confidence penalty
                re_iterated.confidence = max(0.3, re_iterated.confidence - 0.3)
                return re_iterated

        # Option 2: Ask user for clarification
        elif report.recommended_action == "clarify_user":
            return EIRAResponse(
                answer="Could you please clarify your question? " + feedback,
                sources=[],
                confidence=0.0,
                hitl_triggered=True,
                model_used="verifier-clarification",
            )

        else:  # "accept"
            return validated_response
```

---

## Usage Examples

### Example 1: Validate Employee Query

```python
from agents.verifier import verifier
from models.pydantic_io import EIRAResponse, IntentClassification, SourceCitation, EmployeeRow

# Simulate EIRA response
eira_response = EIRAResponse(
    answer="The average age of engineers in Austin is 32.5 years. We queried "
           "the employee database and found 12 engineers in that location. "
           "They range from age 26 to 38.",
    sources=[
        SourceCitation(
            claim="12 engineers in Austin",
            evidence_ref="sql:employee_id:5",
            grounded=True,
        ),
        SourceCitation(
            claim="average age 32.5",
            evidence_ref="sql:employee_id:15",
            grounded=True,
        ),
    ],
    confidence=0.88,
    model_used="claude-3-5-sonnet",
)

intent = IntentClassification(
    intent="sql_only",
    sql_subquery="Get average age of engineers in Austin",
    reasoning="User asked for employee statistics",
)

# Validate
passes, response, report = await verifier.verify_response(
    original_question="What's the average age of engineers in Austin?",
    response=eira_response,
    intent_classification=intent,
)

print(f"Passes: {passes}")
print(f"Score: {report.overall_quality_score:.2f}")
print(f"Issues: {len(report.issues)}")
```

### Example 2: Detect Incomplete Response

```python
# Response missing key information
incomplete_response = EIRAResponse(
    answer="Yes, there are engineers in Austin.",  # Too vague
    sources=[],  # No citations
    confidence=0.92,  # Overconfident!
)

passes, response, report = await verifier.verify_response(
    original_question="What's the average age of engineers in Austin?",
    response=incomplete_response,
    intent_classification=intent,
)

print(f"Passes: {passes}")  # False
print(f"Issues: {len(report.issues)}")  # Multiple

for issue in report.issues:
    print(f"- [{issue.severity}] {issue.description}")
```

Output:
```
Passes: False
Issues: 4
- [critical] Response has no source citations
- [high] Reported confidence (0.92) exceeds quality score (0.3)
- [high] Response is too brief to be meaningful
- [medium] Response appears to drift topics between sentences
```

### Example 3: Handle Re-iteration

```python
# Initial response fails validation
passes, feedback_response, report = await verifier.verify_response(
    original_question="Which departments have people over 50?",
    response=poor_response,
    intent_classification=intent,
    attempt=1,
)

if not passes and report.recommended_action == "re_iterate":
    # Get feedback for re-query
    feedback = await get_re_iteration_feedback(report, original_question)

    print("Validation failed. Feedback for re-iteration:")
    print(feedback)

    # Output:
    # Response validation score: 0.52/1.0
    # Issues found: 3
    #
    # Detailed feedback:
    # ⚠️ CRITICAL Issues (must fix):
    #   - Response has no source citations
    #     Fix: Add citations from retrieved data
    #
    # ⚠️ HIGH Priority Issues:
    #   - Response is too brief to be meaningful
    #     Fix: Provide more detailed answer with context
    #
    # Scores breakdown:
    #   Semantic Relevance: 0.60
    #   Completeness: 0.40
    #   Citation Coverage: 0.00
    #   Coherence: 0.95
    #
    # Recommended action: RE_ITERATE
    # Please re-query with the original question and address the issues above.
```

---

## Testing VERIFIER

```python
import pytest
from agents.verifier import verifier
from models.pydantic_io import EIRAResponse, IntentClassification, SourceCitation

@pytest.mark.asyncio
async def test_verifier_accepts_good_response():
    """Test VERIFIER accepts high-quality response"""
    good_response = EIRAResponse(
        answer="The average age of engineers in Austin is 32 years, based on "
               "13 employees in that location. They range from 26–38 years old.",
        sources=[
            SourceCitation(claim="13 engineers", evidence_ref="sql:employee_id:1", grounded=True),
            SourceCitation(claim="average 32", evidence_ref="sql:employee_id:2", grounded=True),
        ],
        confidence=0.85,
        model_used="claude-sonnet",
    )

    intent = IntentClassification(intent="sql_only", reasoning="Employee query")

    passes, _, report = await verifier.verify_response(
        original_question="What's the average age of engineers in Austin?",
        response=good_response,
        intent_classification=intent,
    )

    assert passes
    assert report.overall_quality_score >= 0.75

@pytest.mark.asyncio
async def test_verifier_rejects_no_citations():
    """Test VERIFIER rejects responses without citations"""
    bad_response = EIRAResponse(
        answer="Yes, there are engineers in Austin.",
        sources=[],
        confidence=0.90,
    )

    intent = IntentClassification(intent="sql_only", reasoning="Employee query")

    passes, _, report = await verifier.verify_response(
        original_question="What's the average age of engineers in Austin?",
        response=bad_response,
        intent_classification=intent,
    )

    assert not passes
    critical = [i for i in report.issues if i.severity == "critical"]
    assert len(critical) > 0
    assert any("citation" in i.description.lower() for i in critical)
```

---

## Configuration

### Tuning Parameters

Located in `config/constants.py` (recommended additions):

```python
# VERIFIER Thresholds
VERIFIER_PASS_THRESHOLD = 0.75         # Overall quality score to accept
VERIFIER_MAX_RE_ITERATIONS = 2         # Max re-query attempts
VERIFIER_MIN_SOURCES = 1               # Minimum source citations
VERIFIER_MIN_CITATION_RATIO = 0.4      # Citation-to-claim ratio
VERIFIER_MIN_ANSWER_LENGTH = 20        # Minimum response length (chars)
VERIFIER_MAX_ANSWER_LENGTH = 5000      # Maximum response length (chars)
VERIFIER_CONFIDENCE_DRIFT_TOLERANCE = 0.3  # Max drift from quality score
```

### Quality Scoring Weights

Change in `tools/verifier_tools.py::_calculate_overall_score()`:

```python
weights = {
    "semantic_relevance": 0.30,      # Most important: does it answer?
    "completeness": 0.25,            # All aspects covered?
    "citation_coverage": 0.25,       # Properly sourced?
    "coherence": 0.15,               # Logically structured?
    "confidence_consistency": 0.05,  # Confidence aligned?
}
```

---

## Audit Logging

VERIFIER integrates with the audit system:

```python
from guardrails.audit_logger import verifier_audit, EventType, Severity

# Logged automatically in validate_response_against_question():
verifier_audit.log_event(
    event_type="response_verified",
    severity="info",
    passes=report.passes,
    overall_score=report.overall_quality_score,
    critical_issues=len(critical_issues),
    recommended_action=report.recommended_action,
)
```

---

## Performance Considerations

### Validation Speed

- Semantic relevance check: ~50ms (string pattern matching)
- Completeness check: ~30ms (simple counting)
- Citation coverage check: ~20ms (list iteration)
- Coherence check: ~100ms (sentence analysis)
- **Total:** ~200ms per validation

### Scaling

For high throughput:
1. Cache validation results by response hash
2. Use async/await throughout
3. Consider batching validations
4. Skip non-critical checks if needed (configuration option)

---

## Best Practices

1. ✅ **Always use VERIFIER** — Final safety gate before user delivery
2. ✅ **Log validation results** — Enable post-hoc analysis
3. ✅ **Limit re-iterations** — Prevent infinite loops (default: 2)
4. ✅ **Adjust thresholds** — Based on use case and domain
5. ✅ **Monitor metrics** — Track pass rate, common issues
6. ✅ **User communication** — Provide validation summary if needed
7. ✅ **Test thoroughly** — Validate behavior with edge cases

---

## Troubleshooting

### High False Rejection Rate
- Lower `VERIFIER_PASS_THRESHOLD` (default 0.75)
- Adjust weight distribution in `_calculate_overall_score()`
- Check citation detection (may be too strict)

### Too Many Re-iterations
- Reduce `VERIFIER_MAX_RE_ITERATIONS` (default 2)
- Provide better feedback to EIRA through verifier_feedback param
- Improve EIRA's initial response quality

### Overconfident Responses
- Add more validation checks
- Lower confidence in high-variance domains
- Improve citation detection

---

## Files

| File | Lines | Purpose |
|------|-------|---------|
| tools/verifier_tools.py | 500+ | Validation logic & metrics |
| agents/verifier.py | 250+ | VERIFIER agent definition |
| models/pydantic_io.py (updated) | +50 | ValidationIssue, VerificationReport |

---

## References

- **CLAUDE.md** § VERIFIER Agent
- **guardrails/GUARDRAILS.md** § Output Validation (SENTINEL)
- **models/pydantic_io.py** § Response schemas
- **config/constants.py** § Tuning parameters
