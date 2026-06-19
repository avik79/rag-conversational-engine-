# Human-in-the-Loop (HITL) System Guide

## Overview

The **Human-in-the-Loop (HITL)** system provides production-grade approval workflows for the RAG Conversational Engine. It ensures that responses requiring human judgment are properly reviewed before delivery to end users.

## Key Features

✅ **Automatic gate triggering** based on response quality
✅ **Severity-based prioritization** (CRITICAL/HIGH/MEDIUM/LOW)
✅ **Real-time approval UI** in Streamlit sidebar
✅ **Persistent audit logging** for compliance
✅ **Analytics dashboard** for monitoring and insights
✅ **Flexible threshold configuration**
✅ **One-click approval/denial** with notes
✅ **Auto-approval rules** for safe scenarios

## Architecture

```
User Query
    ↓
EIRA Agent (Intent Routing)
    ↓
Parallel Execution (VEGA/NOVA)
    ↓
Response Generation
    ↓
HITL CHECKS ← ← ← NEW!
  • Confidence threshold
  • Data freshness
  • Location resolution
  • SQL validation
  • Response grounding
    ↓
HITL Decision
    ├─→ Approved: Deliver response
    ├─→ Denied: Request clarification
    └─→ Blocked: Awaiting human review
```

## HITL Gates

### 1. Low Confidence Gate

**Triggers when:** Response confidence < 0.75 (configurable)
**Severity:** HIGH (< 0.5) or MEDIUM (0.5–0.75)
**Example:** Agent returns employee location with 60% confidence

```python
from tools.hitl_tools import check_confidence_threshold

gate = await check_confidence_threshold(
    confidence=0.65,
    threshold=0.75
)
# Returns: LowConfidenceGate(severity="HIGH")
```

**Decision:**
- ✓ Approve: Trust agent's answer despite lower confidence
- ✗ Deny: Request clarification from user
- ❓ Info: View confidence breakdown

### 2. Ambiguous Match Gate

**Triggers when:** Entity match is ambiguous (e.g., multiple employees with same name)
**Severity:** HIGH
**Example:** Query "Find John's location" → Found 3 employees named John

```python
from tools.hitl_tools import check_ambiguous_match

gate = await check_ambiguous_match(
    entity_type="employee",
    matches=["John Smith (ID: 101)", "John Johnson (ID: 205)", "John Lee (ID: 312)"],
    confidence=0.62
)
# Returns: AmbiguousMatchGate with matches list
```

**Decision:**
- ✓ Approve: Use most likely match
- ✗ Deny: Ask user for clarification
- ❓ Info: Show all candidates with scores

### 3. Stale Data Gate

**Triggers when:** Data is older than freshness threshold (default: 6 hours)
**Severity:** MEDIUM (< 24h old) or HIGH (≥ 24h old)
**Example:** Weather data fetched 8 hours ago

```python
from tools.hitl_tools import check_data_freshness
from datetime import datetime, timezone

gate = await check_data_freshness(
    fetched_at=datetime.now(timezone.utc),
    threshold_hours=6
)
# Returns: StaleDataGate if data is older than 6h
```

**Decision:**
- ✓ Approve: Use stale data (user accepts risk)
- ✗ Deny: Request fresh data (refresh API call)
- ❓ Info: Show data age and collection time

### 4. Location Unresolved Gate

**Triggers when:** Location matching confidence < 0.80
**Severity:** HIGH
**Example:** User says "weather in NYC" → Needs canonical city resolution

```python
from tools.hitl_tools import check_location_resolution

gate = await check_location_resolution(
    raw_location="NYC",
    confidence=0.72,
    candidates=["New York, NY", "Newark, NJ"],
    threshold=0.80
)
# Returns: LocationUnresolvedGate with candidates
```

**Decision:**
- ✓ Approve: Use best match
- ✗ Deny: Ask for clarification
- ❓ Info: Show candidates and confidence scores

### 5. SQL Validation Gate

**Triggers when:** SQL query fails validation checks
**Severity:** CRITICAL
**Example:** Query attempts UNION injection, blocked by AXIOM

```python
from tools.hitl_tools import check_sql_validation

gate = await check_sql_validation(
    query="SELECT * FROM employees UNION SELECT * FROM passwords",
    issues=[
        "UNION operator detected (potential injection)",
        "Unauthorized table reference: passwords"
    ]
)
# Returns: SQLValidationGate with issues list
```

**Decision:**
- ✓ Approve: Override safety check (use admin override)
- ✗ Deny: Block query execution
- ❓ Info: Show security analysis

### 6. Ungrounded Response Gate

**Triggers when:** Response contains claims not backed by sources
**Severity:** CRITICAL
**Example:** Agent makes up employee details not in database

```python
from tools.hitl_tools import check_response_grounding

gate = await check_response_grounding(
    ungrounded_claims=[
        "Employee has 15 years of tenure",
        "Located in company headquarters"
    ],
    confidence=0.65
)
# Returns: ResponseValidationGate with ungrounded claims
```

**Decision:**
- ✓ Approve: Caveat response with confidence disclaimer
- ✗ Deny: Re-query with higher grounding requirements
- ❓ Info: Show grounding analysis by claim

## Using HITL in Your Code

### Basic Integration

```python
from app.integration import run_eira_agent
from tools.hitl_tools import check_confidence_threshold

async def my_agent_function(user_input: str):
    # Run agent
    context = await run_eira_agent(user_input)
    
    # Checks are automatically applied
    if context.requires_approval:
        print(f"Awaiting approval: {context.hitl_decisions}")
    else:
        print(f"Response ready: {context.response.answer}")
    
    return context
```

### Adding Custom HITL Checks

```python
from tools.hitl_tools import HITLGate, create_approval_request

class CustomBusinessRuleGate(HITLGate):
    """Custom gate for domain-specific rules"""
    def __init__(self, violation_type: str, details: dict):
        super().__init__(
            trigger_reason="custom_business_rule",
            severity="HIGH",
            details={
                "violation_type": violation_type,
                **details
            }
        )

# In your agent code:
async def my_custom_check(context):
    if context.response.confidence > 0.9 and "sensitive_data" in context.response.answer:
        gate = CustomBusinessRuleGate(
            violation_type="sensitive_data_threshold",
            details={"data_type": "employee_salary"}
        )
        request = await create_approval_request(gate)
        context.hitl_decisions.append(request)
```

### Handling HITL Decisions

```python
from tools.hitl_audit import get_audit_log

async def handle_user_decision(gate_id: str, approved: bool, note: str = None):
    """Process user's HITL decision"""
    audit_log = get_audit_log()
    
    if approved:
        audit_log.log_decision_made(
            gate_id=gate_id,
            trigger_reason="user_approved",
            approved=True,
            reviewer_note=note
        )
        # Continue with response delivery
    else:
        audit_log.log_decision_made(
            gate_id=gate_id,
            trigger_reason="user_denied",
            approved=False,
            reviewer_note=note
        )
        # Re-query or request clarification
```

## Streamlit UI Components

### HITL Panel (Sidebar)

Located in the left sidebar, shows all pending approvals:

```
🚨 Human-in-the-Loop Gates
━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 2 approval(s) pending

🟠 Low Confidence
Gate ID: a42f1e
Confidence: 65.0%
Threshold: 75.0%
[✓ Approve] [✗ Deny] [❓ Info]

🟡 Stale Data
Gate ID: c8d9b2
Data is 8.5h old (threshold: 6h)
[✓ Approve] [✗ Deny] [❓ Info]
```

### Main Chat Area

When approval is pending:

```
⚠️ Response requires human approval - check the HITL Gates panel
```

### HITL Dashboard (Analytics)

Accessible via sidebar analytics section:

```
📊 HITL Analytics
───────────────────────────
Gates Triggered: 42
Decisions Made: 38
✓ Approved: 32
✗ Denied: 6
Approval %: 84.2%

Auto-Decisions:
✓ Auto-Approved: 3
✗ Auto-Denied: 1

📈 By Gate Type:
low_confidence: 20 (80% approved)
stale_data: 12 (67% approved)
ambiguous_match: 8 (75% approved)
```

## Configuration

### Threshold Settings

Edit `config/constants.py`:

```python
# HITL Thresholds
HITL_CONFIDENCE_THRESHOLD = 0.75  # Confidence below this triggers gate
HITL_DATA_FRESHNESS_HOURS = 6     # Data older than this triggers stale gate
HITL_LOCATION_CONFIDENCE = 0.80   # Location match below this requires clarification
HITL_AUTO_APPROVE = True          # Auto-approve low-risk gates
HITL_AUTO_APPROVE_THRESHOLD = 0.88  # Confidence above this auto-approves
```

### Audit Logging

```python
from tools.hitl_audit import get_audit_log

audit_log = get_audit_log()

# View today's summary
summary = audit_log.get_session_summary()
print(f"Gates triggered: {summary['gates_triggered']}")
print(f"Approval rate: {summary['approval_rate']:.1%}")

# Get approval rates by gate type
rates = audit_log.get_gate_decision_rate()
for gate_type, stats in rates.items():
    print(f"{gate_type}: {stats['approval_rate']:.1%} approved")
```

## Severity Levels

| Severity | Color | Action | Example |
|----------|-------|--------|---------|
| **CRITICAL** | 🔴 | Auto-deny (admin override needed) | SQL injection, ungrounded claims |
| **HIGH** | 🟠 | Requires approval | Ambiguous match, low confidence (<0.5) |
| **MEDIUM** | 🟡 | Review requested | Stale data, low confidence (0.5–0.75) |
| **LOW** | 🔵 | Informational | Additional context available |

## Decision Tracking

All HITL decisions are logged to `logs/hitl/hitl_audit_YYYY-MM-DD.jsonl`:

```json
{
  "event_type": "gate_triggered",
  "timestamp": "2026-06-19T14:32:45.123456",
  "gate_id": "a42f1e",
  "trigger_reason": "low_confidence",
  "severity": "HIGH",
  "details": {
    "confidence": 0.65,
    "threshold": 0.75,
    "gap": 0.1
  }
}

{
  "event_type": "decision_made",
  "timestamp": "2026-06-19T14:33:12.654321",
  "gate_id": "a42f1e",
  "trigger_reason": "low_confidence",
  "approved": true,
  "reviewer_id": "user@company.com",
  "reviewer_note": "Confidence gap acceptable for this query type"
}
```

## Best Practices

### 1. Set Appropriate Thresholds

- **Confidence threshold**: 0.75 for general use, 0.85 for high-stakes queries
- **Data freshness**: 6 hours for weather, 24 hours for news
- **Location confidence**: 0.80 for exact match, 0.60 for suggestions

### 2. Use Severity Levels Correctly

- Reserve **CRITICAL** for security issues
- Use **HIGH** for ambiguous or low-confidence scenarios
- Use **MEDIUM** for borderline cases
- Use **LOW** for informational gates

### 3. Monitor Approval Rates

- If approval rate < 50%: Gates too strict, lower thresholds
- If approval rate > 95%: Gates too lenient, raise thresholds
- If spike in denials: User feedback indicates problem

### 4. Provide Context for Decisions

- Always include "reviewer_note" explaining decision
- Link to query/response for audit trail
- Reference confidence scores for future tuning

### 5. Handle CRITICAL Gates Carefully

CRITICAL gates require admin override:

```python
if gate.severity == "CRITICAL" and not context.user_is_admin:
    # Block response, require admin approval
    context.requires_approval = True
    await audit_log.log_decision_made(
        gate_id=gate.gate_id,
        approved=False,
        reason="CRITICAL gate requires admin review"
    )
```

## Testing HITL

### Unit Tests

```bash
# Test HITL gate creation
pytest tests/test_hitl_gates.py -v

# Test audit logging
pytest tests/test_hitl_audit.py -v

# Test UI components
pytest tests/test_hitl_ui.py -v
```

### Integration Tests

```bash
# Simulate HITL workflow end-to-end
pytest tests/test_hitl_integration.py -v -m integration
```

### Manual Testing

```bash
# 1. Launch Streamlit app
streamlit run app/main.py

# 2. Enter query that triggers low confidence: "Show me weather in unknown_city"
# → Should see HITL gate in sidebar

# 3. Click "Approve" → Response delivers
# → Check logs/hitl/hitl_audit_YYYY-MM-DD.jsonl
```

## Troubleshooting

### HITL Panel Not Showing

**Issue:** Sidebar shows "No pending approvals" but queries should trigger gates

**Solution:**
1. Check confidence threshold: `HITL_CONFIDENCE_THRESHOLD` in config
2. Verify gates are being added: Check logs for "HITL gate logged"
3. Ensure `apply_hitl_checks()` is called in `integration.py`

### Audit Log Not Writing

**Issue:** `logs/hitl/hitl_audit_YYYY-MM-DD.jsonl` is empty or doesn't exist

**Solution:**
1. Verify `logs/hitl/` directory is writable
2. Check for permission errors: `ls -la logs/hitl/`
3. Restart Streamlit app to ensure audit log is initialized

### High False Positive Rate

**Issue:** Too many gates triggering inappropriately

**Solution:**
1. Raise confidence threshold: `HITL_CONFIDENCE_THRESHOLD = 0.80`
2. Increase data freshness threshold: `HITL_DATA_FRESHNESS_HOURS = 12`
3. Analyze approval rates: `audit_log.get_gate_decision_rate()`
4. Adjust based on user feedback

## Compliance & Audit Trail

The HITL system maintains a complete audit trail for compliance:

✅ **What is logged:**
- Gate trigger times and reasons
- Approval/denial timestamps
- Reviewer identity and notes
- Full context data
- Decision outcomes

✅ **Audit Report:**

```python
from tools.hitl_audit import get_audit_log

audit_log = get_audit_log()
summary = audit_log.get_session_summary()

# Export for compliance reporting
import json
with open("hitl_compliance_report.json", "w") as f:
    json.dump(summary, f, indent=2)
```

✅ **Retention:**
- Logs stored per-day: `logs/hitl/hitl_audit_YYYY-MM-DD.jsonl`
- Recommended retention: 90+ days for audit purposes
- Archive strategy: Move old logs to cold storage monthly

## Future Enhancements

- [ ] Auto-approval rules (e.g., low-risk gates auto-approve)
- [ ] Reviewer performance scoring
- [ ] Machine learning model to predict approval likelihood
- [ ] Slack integration for urgent CRITICAL gate notifications
- [ ] Batch approval UI for high-volume gates
- [ ] Custom gate templates for domain-specific rules
- [ ] A/B testing for threshold optimization

## References

- **CLAUDE.md** — System architecture overview
- **GUARDRAILS_IMPLEMENTATION.md** — Security layer details
- **VERIFIER_GUIDE.md** — Response quality validation
- **logs/hitl/** — Real-time audit trail

## Support

For questions or issues:
1. Check the logs: `logs/hitl/hitl_audit_*.jsonl`
2. Run dashboard: `app/hitl_dashboard.py`
3. Review test suite: `tests/test_hitl_*.py`
4. Open GitHub issue with logs attached
