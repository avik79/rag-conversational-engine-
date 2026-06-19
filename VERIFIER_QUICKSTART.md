# VERIFIER Quick Start — 5 Minute Integration

## TL;DR

VERIFIER validates that responses answer the original question. If validation fails, it provides feedback to re-query.

```python
from agents.verifier import verifier

passes, response, report = await verifier.verify_response(
    original_question="What's the avg age?",
    response=eira_response,
    intent_classification=intent,
)

if passes:
    return response  # ✅ Good response
else:
    feedback = await get_re_iteration_feedback(report, question)
    improved = await eira.re_query(question, feedback)  # 🔄 Re-query
    return await verifier.verify_response(improved)
```

---

## One-Liners

### Check if response is good
```python
passes, _, report = await verifier.verify_response(q, resp, intent)
assert passes  # ✅ Accepted
```

### Get quality score
```python
_, _, report = await verifier.verify_response(q, resp, intent)
print(f"Quality: {report.overall_quality_score:.1%}")  # e.g., 84%
```

### Get issues
```python
_, _, report = await verifier.verify_response(q, resp, intent)
for issue in report.issues:
    print(f"[{issue.severity}] {issue.description}")
```

### Get feedback for re-query
```python
feedback = await get_re_iteration_feedback(report, original_question)
print(feedback)  # Specific issues to fix
```

### Quick quality check
```python
metrics = await verifier.check_response_quality(response)
print(f"Quality OK: {metrics['quality_ok']}")  # True/False
```

---

## 3-Step Integration

### Step 1: Import
```python
from agents.verifier import verifier
from tools.verifier_tools import get_re_iteration_feedback
```

### Step 2: After EIRA Response
```python
# In app/integration.py after agents execute:
passes, response, report = await verifier.verify_response(
    original_question=user_query,
    response=eira_response,
    intent_classification=intent,
    attempt=1,
)
```

### Step 3: Handle Results
```python
if passes:
    return response  # Success
else:
    # Get feedback and re-query
    feedback = await get_re_iteration_feedback(report, user_query)
    return await re_query(user_query, feedback)
```

---

## Validation Metrics (What Gets Checked)

| Metric | Weight | What? |
|--------|--------|-------|
| Semantic Relevance | 30% | Does it answer? |
| Completeness | 25% | All parts covered? |
| Citation Coverage | 25% | Properly sourced? |
| Coherence | 15% | Logically structured? |
| Confidence Match | 5% | Confidence realistic? |

**Pass if:** Overall ≥ 0.75 AND no critical issues

---

## Decision Tree

```
validate_response_against_question()
    ↓
[Calculate 5 metrics]
[Find issues by severity]
    ↓
    ├─→ Score ≥ 0.75 + No critical issues?
    │   ├─ YES → ✅ ACCEPT (passes=True)
    │   └─ NO  → Continue
    │
    └─→ Critical issues present?
        ├─ YES → Attempt < max?
        │   ├─ YES → 🔄 RE-ITERATE (passes=False)
        │   └─ NO  → Return with penalty
        └─ NO  → Ask user to clarify
```

---

## Issue Types & Severity

### 🔴 CRITICAL (Blocks)
- No source citations
- Off-topic response
- Completely wrong intent

### 🟠 HIGH (Recommends re-iterate)
- Response too brief
- Single source not enough
- Overconfident

### 🟡 MEDIUM (Advisory)
- Missing conclusion
- Topic drift

### 🔵 LOW (Informational)
- Long sentences
- Minor improvements

---

## Common Patterns

### Pattern 1: Validate & Return
```python
passes, resp, report = await verifier.verify_response(q, eira_resp, intent)
return resp if passes else error_response()
```

### Pattern 2: Validate & Re-iterate
```python
for attempt in range(1, 3):
    passes, resp, report = await verifier.verify_response(
        q, current_resp, intent, attempt
    )
    if passes:
        return resp
    
    feedback = await get_re_iteration_feedback(report, q)
    current_resp = await eira.re_query(q, feedback)
```

### Pattern 3: Validate & Get User Feedback
```python
passes, resp, report = await verifier.verify_response(q, eira_resp, intent)
if not passes:
    feedback = await get_re_iteration_feedback(report, q)
    return f"Please clarify: {feedback}"
return resp
```

### Pattern 4: Monitor Quality
```python
_, _, report = await verifier.verify_response(q, resp, intent)
metrics = {
    "score": report.overall_quality_score,
    "passed": report.passes,
    "issues": len(report.issues),
}
log_to_dashboard(metrics)
```

---

## Configuration

Add to `config/constants.py`:

```python
VERIFIER_PASS_THRESHOLD = 0.75
VERIFIER_MAX_RE_ITERATIONS = 2
VERIFIER_MIN_SOURCES = 1
```

---

## Testing

```python
# Simple test
passes, _, _ = await verifier.verify_response(q, resp, intent)
assert passes

# With quality check
_, _, report = await verifier.verify_response(q, resp, intent)
assert report.overall_quality_score >= 0.75
assert len(report.issues) == 0
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Too many rejections | Lower VERIFIER_PASS_THRESHOLD |
| Takes too long | Response is being re-iterated (normal) |
| Wrong metrics | Adjust weights in _calculate_overall_score() |
| Specific issues | Check report.issues for details |

---

## Files to Know

- **tools/verifier_tools.py** — The validation engine
- **agents/verifier.py** — The agent class
- **VERIFIER_GUIDE.md** — Detailed reference
- **VERIFIER_INTEGRATION_EXAMPLE.md** — Code examples
- **VERIFIER_SUMMARY.md** — Full overview

---

## Next: Full Integration

1. Update `app/integration.py` with verifier calls
2. Modify `coordinate_agents()` to handle verifier_feedback
3. Add to Streamlit UI
4. Monitor quality metrics

See **VERIFIER_INTEGRATION_EXAMPLE.md** for complete code.

---

## Help

- **How do I...?** → See VERIFIER_INTEGRATION_EXAMPLE.md
- **What does [metric] mean?** → See VERIFIER_GUIDE.md
- **Why did it fail?** → Check report.issues
- **How do I re-iterate?** → See Pattern 2 above
