# Phase 6: E2E Testing & Validation — PLAN

**Status**: Ready to execute  
**Scope**: End-to-end testing of all query paths and HITL integration

## Test Scenarios

### 6A - SQL-Only Queries (VEGA Path)

**Test Case 1.1**: Simple name search
```
Input: "Find John in our database"
Expected Flow:
  - EIRA: intent=sql_only
  - AXIOM: validates query ✓
  - VEGA: SELECT * WHERE name LIKE '%John%'
  - Response: returns matching employees
  - SENTINEL: validates groundedness ✓
Expected Output: List of Johns with departments, ages, locations
```

**Test Case 1.2**: Department filter
```
Input: "Who are the engineers?"
Expected Flow:
  - EIRA: intent=sql_only
  - VEGA: SELECT * WHERE department='Engineering'
  - Response: engineers with counts
Expected Output: 125 engineers from various offices
```

**Test Case 1.3**: Ambiguous match triggers HITL
```
Input: "Tell me about Alice"
Expected Flow:
  - VEGA finds 3+ rows → ambiguous_match=True
  - HITL triggered → sidebar shows "VEGA_AMBIGUOUS"
  - User clicks "More Info" → can see matching rows
Expected Output: HITL gate in sidebar, awaiting clarification
```

### 6B - RAG-Only Queries (NOVA Path)

**Test Case 2.1**: Weather query
```
Input: "What's the weather in Austin?"
Expected Flow:
  - EIRA: intent=rag_only
  - NOVA: search_weather_embeddings(query, location_filter="Austin, TX")
  - Returns: weather chunks with freshness check
  - SENTINEL: validates sources ✓
Expected Output: Current weather + freshness indicator
```

**Test Case 2.2**: News query
```
Input: "Any tech news today?"
Expected Flow:
  - EIRA: intent=rag_only
  - NOVA: search_news_embeddings(query)
  - Returns: news items with sources
Expected Output: Recent tech news with source citations
```

**Test Case 2.3**: Stale data triggers freshness warning
```
Expected: If weather data >6h old:
  - NOVA sets freshness_ok=False
  - Response includes: ⚠ Data is 8 hours old
Expected Output: Stale data warning in response
```

### 6C - Cross-Domain Queries (VEGA → KIRA → NOVA)

**Test Case 3.1**: Employee + weather aggregate
```
Input: "What's the weather for all Austin employees?"
Expected Flow:
  - EIRA: intent=cross_domain
  - VEGA: SELECT * WHERE office_location="Austin, TX" → 50 employees
  - KIRA: resolve "Austin, TX" → canonical_key="Austin, TX" (confidence=1.0)
  - NOVA: search_weather_embeddings("Austin weather", location="Austin, TX")
  - SENTINEL: validates combined response ✓
Expected Output: Employees + weather snapshot
```

**Test Case 3.2**: Location normalization (KIRA fuzzy match)
```
Input: "Weather for the Austin guys"
Expected Flow:
  - KIRA receives "Austin team office"
  - Exact match fails
  - Fuzzy match: Levenshtein("Austin") → distance=0 ✓
  - Resolves to "Austin, TX" (confidence=0.9)
Expected Output: Successful resolution, weather returned
```

**Test Case 3.3**: KIRA needs clarification
```
Input: "Weather for XYZ facility employees"
Expected Flow:
  - KIRA doesn't recognize "XYZ"
  - Fuzzy match fails (distance > 2)
  - Semantic match returns confidence < 0.80
  - HITL triggered: "KIRA_CLARIFICATION"
Expected Output: HITL gate in sidebar = "Please clarify location"
```

### 6D - HITL Gate Scenarios

**Test Case 4.1**: AXIOM blocks SQL injection
```
Input: "'; DROP TABLE employees; --"
Expected Flow:
  - AXIOM detects DROP, UNION patterns
  - is_blocked=True
  - HITL gate: "AXIOM_BLOCKED"
Expected Output: HITL sidebar shows "Query validation failed"
```

**Test Case 4.2**: SENTINEL low confidence
```
Input: Generic query with unreliable response
Expected Flow:
  - Agent produces response
  - SENTINEL calculates confidence < 0.75
  - HITL gate: "SENTINEL_LOW_CONFIDENCE"
Expected Output: HITL sidebar lists ungrounded claims
```

**Test Case 4.3**: User approves gate
```
Given: HITL gate pending
When: User clicks "Approve"
Expected: Decision logged, execution continues
Result: Response rendered, metrics updated
```

**Test Case 4.4**: User denies gate
```
Given: HITL gate pending
When: User clicks "Deny"
Expected: Decision logged, execution halted
Result: Message: "Query denied by user"
```

### 6E - Hook Execution

**Test Case 5.1**: PreToolUse logs and validates
```
When: Tool invoked
Expected:
  - PreToolUse hook fires
  - log_tool_call() records tool name, args
  - check_pii_leakage() detects SSN/CC (if present)
  - validate_tool_input() enforces required fields
```

**Test Case 5.2**: Tool detects PII
```
Input: Tool called with credit card number
Expected:
  - check_pii_leakage() returns has_pii=True
  - st.warning() shows warning
  - Tool blocked from executing
```

**Test Case 5.3**: PostToolUse detects triggers
```
After: Tool returns result
Expected:
  - log_tool_result() records output + latency
  - detect_hitl_triggers() identifies gates
  - measure_latency() flags if >5s
  - validate_tool_output() checks schema
```

### 6F - Session Persistence

**Test Case 6.1**: Turn count increments
```
Given: New session (turn_count=0)
When: User sends 3 messages
Expected: turn_count progresses 0→1→2→3
```

**Test Case 6.2**: Message history persists
```
When: User interacts with chat
Expected: Messages append to st.session_state.messages
After rerun: History visible in chat
```

**Test Case 6.3**: Tool traces accumulated
```
When: Multiple turns with multiple tools
Expected: tool_traces list grows
Accessible: In sidebar under "Show tool traces"
```

## Test Execution

### Manual Testing (Interactive)
```bash
streamlit run app/main.py
# In browser:
# 1. Type test queries from 6A-6F
# 2. Verify responses
# 3. Check HITL sidebar for gates
# 4. Approve/deny gates
# 5. Check tool traces
```

### Automated Testing (Script)
```bash
python scripts/test_e2e.py  # (to be created in Phase 6)
```

## Success Criteria

- [x] Phase 5 complete (UI + integration layer)
- [ ] All SQL-only queries execute without errors
- [ ] All RAG-only queries return grounded results
- [ ] Cross-domain queries chain VEGA→KIRA→NOVA
- [ ] HITL gates trigger at correct points
- [ ] User can approve/deny gates in UI
- [ ] Tool traces accumulated and visible
- [ ] Session state persists across turns
- [ ] Pre/PostToolUse hooks fire correctly
- [ ] PII detection blocks sensitive inputs
- [ ] Freshness indicators display correctly
- [ ] Error handling graceful (no crashes)

## Estimated Time
- 6A (SQL): 15 min
- 6B (RAG): 15 min
- 6C (Cross-domain): 20 min
- 6D (HITL): 20 min
- 6E (Hooks): 15 min
- 6F (Session): 10 min
- **Total**: ~95 minutes

## Deliverables
- PHASE_6_RESULTS.md (test results + logs)
- scripts/test_e2e.py (automated test suite)
- Bug fixes (if any found)
- Performance notes (latency measurements)

---

**Ready to execute Phase 6?**
