# HITL System — 5-Minute Quick Start

## What is HITL?

Human-in-the-Loop (HITL) automatically flags responses that might need human review before delivering them to users. It's like a quality control gate that says: "I'm not confident enough about this, check it?"

## Starting the App

```bash
# 1. Install dependencies (if not done)
uv sync

# 2. Set up databases
python -m db.seed
python -c "from chroma.client import init_chroma; init_chroma()"

# 3. Launch Streamlit
streamlit run app/main.py
```

The app opens at **http://localhost:8501**

## Triggering Your First HITL Gate

### Low Confidence Example

In the chat, type a query that returns lower confidence:

```
"Tell me about an employee in a city I don't mention clearly"
```

**What happens:**
1. Agent returns response with ~65% confidence
2. HITL detects: 65% < 75% threshold
3. Gate appears in **HITL Gates** panel (left sidebar)

### You'll See:

```
🚨 Human-in-the-Loop Gates

⚠️ 1 approval(s) pending

🟠 Low Confidence
Gate ID: a42f1e
Confidence: 65.0%
[✓ Approve] [✗ Deny] [❓ Info]
```

## Making Your First Decision

### Option 1: Approve
Click **✓ Approve** to:
- Accept the response as-is
- Log the decision for audit trail
- Continue chatting

### Option 2: Deny
Click **✗ Deny** to:
- Reject the response
- Request clarification from user
- Trigger re-query

### Option 3: More Info
Click **❓ Info** to:
- View full context
- See confidence scores
- Review source data

## Viewing Analytics

In the left sidebar, under **HITL Analytics**:

```
📊 Gates Triggered: 3
Decisions Made: 2
✓ Approved: 2
✗ Denied: 0
Approval %: 100%
```

Click **📈 By Gate Type** to drill down by scenario.

## Common Gate Types (Quick Reference)

| Gate | Triggers When | Color |
|------|---------------|-------|
| **Low Confidence** | Response < 75% confidence | 🟠 |
| **Ambiguous Match** | Multiple matching employees | 🟠 |
| **Stale Data** | Weather older than 6 hours | 🟡 |
| **Location Unresolved** | City resolution < 80% confidence | 🟠 |
| **SQL Blocked** | Query fails security check | 🔴 |
| **Ungrounded Response** | Claims not backed by sources | 🔴 |

## Configuration (2-Minute Setup)

Edit `config/constants.py` to adjust sensitivity:

```python
# Tighter gates (more approvals needed)
HITL_CONFIDENCE_THRESHOLD = 0.80  # Was 0.75

# Relaxed gates (fewer approvals needed)
HITL_CONFIDENCE_THRESHOLD = 0.70  # Was 0.75
```

Restart Streamlit after changes.

## Viewing Audit Trail

Logs are stored in `logs/hitl/hitl_audit_YYYY-MM-DD.jsonl`:

```bash
# View today's logs
cat logs/hitl/hitl_audit_2026-06-19.jsonl | jq .

# Count gate triggers
grep "gate_triggered" logs/hitl/hitl_audit_2026-06-19.jsonl | wc -l

# See approval rate
grep "decision_made" logs/hitl/hitl_audit_2026-06-19.jsonl | grep "approved" | wc -l
```

## Test Cases to Try

### ✓ Should Trigger Gate
1. "What's the weather for John?" → Ambiguous employee name
2. "Tell me about a random city" → Location unresolved
3. "Weather in London 2 weeks ago" → Stale data

### ✗ Should NOT Trigger Gate
1. "What's the weather for Austin?" → Clear, recent data
2. "Show me employees in Denver" → Exact location match
3. "List all departments" → High-confidence data query

## Understanding Decision Breakdown

**Good approval rate**: 70–90%
- Means gates are well-calibrated
- Most flagged responses are legit edge cases

**Too low approval rate** (< 50%): Gates too strict
- Action: Lower `HITL_CONFIDENCE_THRESHOLD`

**Too high approval rate** (> 95%): Gates too relaxed
- Action: Raise `HITL_CONFIDENCE_THRESHOLD`

## Next Steps

1. **Tune your thresholds** based on approval rates
2. **Monitor the dashboard** daily
3. **Review audit logs** weekly
4. **Read full guide**: `HITL_GUIDE.md`
5. **Enable notifications** for CRITICAL gates (future enhancement)

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Clear session | Click "Clear Session" button |
| Toggle tool traces | Check "Show tool traces" box |
| Refresh dashboard | F5 or Cmd+R |

## Troubleshooting

**HITL panel shows "No pending approvals" but I expect a gate?**
- Response confidence is above 75%? Try lowering it
- Check `config/constants.py`: `HITL_CONFIDENCE_THRESHOLD`
- Look for gate in logs: `logs/hitl/hitl_audit_*.jsonl`

**Can't find the HITL Gates panel?**
- It's in the **left sidebar** under "Human-in-the-Loop Gates"
- If sidebar is collapsed, click the `>` arrow at top-left

**How do I reset everything?**
- Click "Clear Session" to reset current chat
- Delete `logs/hitl/` to clear audit trail
- Restart Streamlit: `streamlit run app/main.py`

## FAQ

**Q: What happens if I deny an approval?**
A: The response is not sent. The system can request clarification from the user or re-query with different parameters.

**Q: Are decisions logged for compliance?**
A: Yes! All gates and decisions are logged to `logs/hitl/hitl_audit_*.jsonl` with timestamps and reviewer notes.

**Q: Can I auto-approve certain gates?**
A: Not yet, but it's on the roadmap. For now, all gates require explicit decision.

**Q: Why was a gate triggered for what seems like a good response?**
A: HITL is conservative by design. It flags edge cases. Check the confidence score and adjust thresholds if needed.

**Q: How's HITL different from the VERIFIER agent?**
A: 
- **VERIFIER**: Checks *response quality* (relevance, completeness, citations)
- **HITL**: Checks *confidence, freshness, and grounding*

Both work together for comprehensive quality assurance.

## Video Demo (30 seconds)

```
1. Launch app: streamlit run app/main.py
2. Type: "Weather for someone with an unclear name"
3. Response appears with low confidence
4. HITL gate shows in sidebar
5. Click "✓ Approve" → Response confirmed
6. Check Analytics → See decision logged
```

## Key Metrics to Monitor

- **Gates/Day**: How many gates triggered
- **Approval Rate**: % of approved vs. denied decisions
- **Avg Response Time**: How long reviewers take to decide
- **Gate Distribution**: Which types trigger most

See the full dashboard at: `app/hitl_dashboard.py`

---

**Ready to go?** Start the app and try your first query! 🚀

For detailed docs, see `HITL_GUIDE.md`
