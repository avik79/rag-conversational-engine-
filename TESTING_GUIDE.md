# Interactive Testing Guide

## Starting the App

```bash
cd /c/Users/vmuser/Documents/rag-conversational-engine
source .venv/Scripts/activate
streamlit run app/main.py
```

The app will start at: **http://localhost:8501**

---

## Test Scenarios

### Test 1: SQL-Only Query (VEGA Path)

**What to test**: Employee database queries

**Steps**:
1. Open http://localhost:8501
2. In chat input, type: `"Find engineers in Seattle"`
3. Expected behavior:
   - Chat shows user message (👤 avatar)
   - Assistant starts thinking (⏳)
   - Response appears with engineering employees from Seattle
   - Confidence badge shows (green if >75%)
   - Tool traces expandable in details

**What's happening**:
```
User Query
  ↓
EIRA (intent classification) → sql_only
  ↓
AXIOM (validate query) → safe_to_execute=True
  ↓
VEGA (SQL specialist)
  ├─ Generate SQLAlchemy query
  ├─ execute_employee_query(department="Engineering", office_location="Seattle, WA")
  └─ Returns employee records
  ↓
SENTINEL (validate groundedness) → confidence=0.95
  ↓
Response rendered with sources
```

---

### Test 2: RAG-Only Query (NOVA Path)

**What to test**: Weather/news retrieval

**Steps**:
1. Type: `"What's the weather in Austin right now?"`
2. Expected behavior:
   - EIRA routes to RAG path
   - NOVA searches weather_embeddings collection
   - Response shows weather snapshot
   - Freshness indicator displays (🟢 if <6h old)

**What's happening**:
```
User Query
  ↓
EIRA (intent) → rag_only
  ↓
NOVA (RAG specialist)
  ├─ search_weather_embeddings("Austin weather")
  ├─ Returns chunks with metadata
  └─ Checks freshness_ok
  ↓
Response with sources
```

---

### Test 3: Cross-Domain Query (VEGA → KIRA → NOVA)

**What to test**: Combining employee data with weather

**Steps**:
1. Type: `"What's the weather where our Austin office employees are based?"`
2. Expected behavior:
   - EIRA classifies as cross_domain
   - VEGA finds Austin employees
   - KIRA resolves location to canonical city
   - NOVA fetches weather for that location
   - Complete response with both datasets

**What's happening**:
```
User Query
  ↓
EIRA (intent) → cross_domain
  ↓
VEGA: "Find employees in Austin"
  └─ Returns list with office_location="Austin, TX"
  ↓
KIRA: "Resolve 'Austin, TX' to Chroma key"
  ├─ Exact match → confidence=1.0 ✓
  └─ Returns canonical_key
  ↓
NOVA: "Get weather for Austin, TX"
  ├─ search_weather_embeddings(..., location_filter="Austin, TX")
  └─ Returns weather context
  ↓
Response combines both (employees + weather)
```

---

### Test 4: HITL Gate Triggers

**What to test**: Human approval gates

#### 4A: Ambiguous Name Match (VEGA_AMBIGUOUS)

**Steps**:
1. Type: `"Tell me about Alex"`
2. Expected:
   - If >1 employee named Alex exists
   - 🚨 HITL gate appears in sidebar
   - Title: "VEGA_AMBIGUOUS"
   - Details show matching rows
   - Approve/Deny buttons available

**What to do**:
- Click "Approve" → Query continues, returns all Alexes
- Click "Deny" → Query halted, message shows "Denied by user"

#### 4B: Location Clarification (KIRA_CLARIFICATION)

**Steps**:
1. Type: `"Weather for employees at the North Campus"`
2. Expected:
   - If "North Campus" location unknown
   - 🚨 HITL gate: "KIRA_CLARIFICATION"
   - Confidence score < 0.80
   - Sidebar shows gate with "More Info" option

**What to do**:
- Click "More Info" → Shows resolution attempt
- Click "Approve" → Best guess proceeds
- Click "Deny" → Asks for clarification

#### 4C: SQL Injection Attempt (AXIOM_BLOCKED)

**Steps**:
1. Type: `"'; DROP TABLE employees; --"`
2. Expected:
   - AXIOM detects dangerous pattern
   - 🚨 HITL gate: "AXIOM_BLOCKED"
   - Reason: "Detected dangerous pattern: DROP"
   - Options: Approve (unlikely) or Deny

---

### Test 5: Tool Traces

**What to test**: See what tools were called under the hood

**Steps**:
1. Execute any query
2. After response appears, look for expandable "Tool calls" section
3. Expand it to see:
   - Tool names executed
   - Status (success/blocked)
   - Execution flow

**What you'll see**:
```
Tool calls
  ├─ query_employees (VEGA tool): SUCCESS
  ├─ resolve_location (KIRA tool): SUCCESS  
  └─ retrieve_rag_context (NOVA tool): SUCCESS
```

---

### Test 6: Session Persistence

**What to test**: Chat history and metrics persist

**Steps**:
1. Send 3 different queries
2. Check sidebar:
   - Turn Count increments (1 → 2 → 3)
   - Message count increases
   - Tool Traces list grows
3. Close chat details and re-open
   - All history still present ✓

---

### Test 7: Settings Panel

**What to test**: User configuration

**Steps**:
1. In sidebar, scroll to "⚙️ Settings"
2. Change "User Name" from "User" to "Alice"
3. Send a query
4. Check that Alice is logged in session_state

---

### Test 8: Error Handling

**What to test**: Graceful failure modes

#### 8A: Invalid Input

**Steps**:
1. Type: `""` (empty message)
2. Expected: Nothing sent (Streamlit blocks empty input)

#### 8B: Ambiguous Query

**Steps**:
1. Type: `"hello"`
2. Expected:
   - EIRA classifies as "unclear"
   - Response: "I need more context. Are you asking about employees, weather, or news?"

---

## Visual Components to Inspect

### Chat Interface
```
┌─────────────────────────────────────┐
│  RAG Conversational Engine          │
│  🧠 [title]                          │
├─────────────────────────────────────┤
│                                      │
│  👤 What's the weather in Austin?   │ (user message)
│                                      │
│  🧠 [Response with sources]         │ (assistant message)
│     Confidence: ▯▯▯▯▯ 85%          │
│     [Tool calls ▼]                   │
│                                      │
│  [Chat input field]                  │
│  "Ask me about employees..."        │
│                                      │
└─────────────────────────────────────┘
```

### Sidebar
```
┌──────────────────────────┐
│  🚨 Human-in-the-Loop    │ (if gate triggered)
│  Gate: VEGA_AMBIGUOUS    │
│  Found 3 employees named │
│  "Alex"                  │
│  [Approve] [Deny]        │
├──────────────────────────┤
│  ⚙️ Settings             │
│  User Name: [User      ] │
├──────────────────────────┤
│  📊 Session Info         │
│  Turn Count: 2           │
│  Tool Traces: 4          │
│  ☑ Show tool traces      │
├──────────────────────────┤
│  [Clear Session]         │
└──────────────────────────┘
```

---

## Expected Behaviors

| Test | Expected Result | Success Criteria |
|------|-----------------|------------------|
| SQL query | Employee results | Name, age, dept appear |
| RAG query | Weather text | "°F", "mph", location |
| Cross-domain | Combined data | Employees + weather both shown |
| HITL gate | Approve/Deny buttons | Can click either button |
| Tool traces | Expandable list | Tool names visible |
| Session | Persistent history | Messages stay after refresh |
| Empty input | No action | Message not sent |
| Invalid query | Clarification | Bot asks for details |

---

## Known Limitations in Dev

### Will require real API keys to fully work:
1. **OpenAI API** — Embeddings generation
2. **Tavily API** — Live weather/news fetching
3. **Anthropic API** — LLM responses (using placeholder now)

### Current workarounds:
- Pre-seeded employee data (500 rows) — ✅ Works without API
- Chroma validation — ✅ Works without API
- Tool routing logic — ✅ Works without API
- HITL gates — ✅ Works without API

### To test with real data:
```bash
# Update .env with real keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=...

# Restart app
streamlit run app/main.py
```

---

## Troubleshooting

### App won't start
```bash
# Check if port 8501 is in use
lsof -i :8501

# Kill existing process
kill -9 <PID>

# Restart
streamlit run app/main.py
```

### ScriptRunContext warning
- Normal in bare mode, ignore it
- Won't appear in production

### Chat not responding
- Check browser console (F12) for errors
- Verify .env has dummy API keys set
- Check terminal for Python stack traces

---

## Test Checklist

- [ ] SQL-only query works
- [ ] RAG-only query works
- [ ] Cross-domain query works
- [ ] HITL gate appears (ambiguous match)
- [ ] Can approve/deny gate
- [ ] Tool traces visible
- [ ] Session persists (turn count increments)
- [ ] Settings update user name
- [ ] Error handling graceful
- [ ] All messages show confidence badge

Once all pass, UI is working correctly!
