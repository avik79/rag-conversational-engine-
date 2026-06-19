# Quick Start Guide

## 1-Minute Setup

### Requirements
- Python 3.10+
- Git

### Install & Run

```bash
# Clone/navigate to project
cd /c/Users/vmuser/Documents/rag-conversational-engine

# Create virtual environment
python -m venv .venv
source .venv/Scripts/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
uv pip install -r requirements.txt

# Initialize databases
python scripts/init_databases.py

# Start the app
streamlit run app/main.py
```

Open: **http://localhost:8501**

---

## Example Queries

### SQL-Only (Employee Data)
```
"Find all engineers"
"Who works in Seattle?"
"Show me employees between 25 and 35 years old"
"Which department is the largest?"
```

### RAG-Only (Weather/News)
```
"What's the weather in Austin?"
"Tell me about tech news today"
"Current conditions in New York"
```

### Cross-Domain (Both)
```
"What's the weather where our Austin office employees work?"
"News relevant to our employees in Seattle"
"Weather forecast for all our office locations"
```

---

## What You'll See

### Successful SQL Query
```
Q: "Find engineers"
A: 125 employees found (departments Engineering)
   - Name, Age, Department, Location
   - Confidence: ✅ 95%
```

### HITL Gate Example
```
Q: "Tell me about Alex"
A: ⚠️ Found 3 employees named Alex
   [Approve] [Deny] [More Info]
   (Sidebar shows all 3 matching rows)
```

### Tool Tracing
```
[Tool calls ▼]
  query_employees (VEGA)
  resolve_location (KIRA)
  retrieve_rag_context (NOVA)
```

---

## Architecture in 60 Seconds

```
Streamlit UI
    ↓
EIRA Router (intent classification)
    ├─ SQL-only → VEGA (employee specialist)
    ├─ RAG-only → NOVA (weather/news specialist)
    └─ Both → VEGA → KIRA → NOVA (chained)
    ↓
Validators
    ├─ AXIOM (pre-execution)
    └─ SENTINEL (post-generation)
    ↓
HITL Gates (human approval if needed)
    ↓
Execution
    ├─ SQLite (500 employees)
    └─ Chroma (weather/news vectors)
```

---

## File Structure

```
rag-conversational-engine/
├── app/
│   ├── main.py           # Streamlit UI entry point
│   ├── integration.py     # Agent runner
│   ├── components.py      # UI widgets
│   └── wire_tools.py      # Tool initialization
├── agent_definitions/
│   ├── eira.py           # Orchestrator
│   ├── vega.py           # SQL specialist
│   ├── nova.py           # RAG specialist
│   ├── kira.py           # Location resolver
│   ├── axiom.py          # Pre-validator
│   ├── sentinel.py       # Post-validator
│   └── iris.py           # Ingestion
├── tools/
│   ├── sql_tools.py      # Query execution
│   ├── chroma_tools.py   # Vector search
│   ├── embedding_tools.py
│   ├── tavily_tools.py
│   └── hitl_tools.py
├── models/
│   ├── pydantic_io.py    # I/O schemas
│   └── employee.py       # ORM model
├── db/
│   ├── engine.py         # SQLite connection
│   └── seed.py           # 500 employee seeding
├── chroma/
│   └── client.py         # Vector store
├── config/
│   ├── constants.py      # Cities, departments
│   └── llm_config.py     # Model configuration
├── hooks/
│   ├── preprocessing.py  # PreToolUse hooks
│   └── postprocessing.py # PostToolUse hooks
├── scripts/
│   ├── init_databases.py
│   └── test_e2e.py       # E2E tests (88.9% pass)
└── .env                  # API keys (template)
```

---

## API Keys Needed (Optional)

For full functionality with real data:

```
.env file:
──────────
# LLM (primary)
ANTHROPIC_API_KEY=sk-ant-...

# LLM fallback + embeddings
OPENAI_API_KEY=sk-...

# Weather/news fetching
TAVILY_API_KEY=...
```

Without keys: App works with seed data + Chroma vectors (sufficient for demo).

---

## Dashboard Metrics

### Session Info (Sidebar)
- **Turn Count**: How many queries sent
- **Tool Traces**: Number of tool calls executed
- **Messages**: Total conversation messages

### Response Quality
- **Confidence**: ✅ Green (>75%) | ⚠️ Yellow (50-75%) | ❌ Red (<50%)
- **Freshness**: Weather data age (warns if >6h old)
- **Sources**: Citations for RAG results

---

## Common Tasks

### Test SQL Query
```
Input: "Find engineers"
Expected: 125 results with names, ages, locations
HITL gates: None (unless >1 match on name filter)
```

### Test RAG Query
```
Input: "Weather in Austin"
Expected: Current conditions from Chroma
Freshness: Shows age of data
```

### Trigger HITL Gate
```
Input: "Tell me about Alex"  (if multiple Alexes exist)
Expected: Sidebar gate with Approve/Deny buttons
Action: Click Approve to continue query
```

### Check Tool Traces
```
After any query:
  Click [Tool calls ▼] to expand
  Shows: query_employees, resolve_location, retrieve_rag_context
  Each with success/failure status
```

---

## Testing Without APIs

### What Works Out of Box
- ✅ SQL queries (500 seeded employees)
- ✅ Chroma validation (location contracts)
- ✅ HITL gate logic
- ✅ Tool routing verification
- ✅ Schema validation
- ✅ Session state management

### What Needs APIs
- ❌ Embedding generation (needs OpenAI key)
- ❌ Live weather/news (needs Tavily key)
- ❌ Full LLM responses (needs Anthropic key)

### Workaround
- Pre-seeded database covers employee queries
- Chroma mock data covers validation tests
- Tool orchestration works with dummy values

---

## Monitoring

### Session State (Sidebar)
```
Turn Count: 3
Tool Traces: 7
Messages: 6

[Show tool traces ☑]
  → Expands list of recent 5 tool calls
```

### Console Logs
- PreToolUse: "PRE_TOOL_USE: tool=query_employees, args_keys=[...]"
- PostToolUse: "POST_TOOL_USE: tool=query_employees, latency_ms=45"
- HITL trigger: "HITL_TRIGGERS_DETECTED: 1 gate(s) activated"

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Port 8501 busy | Kill process: `lsof -i :8501 \| kill` |
| No employees found | Run: `python scripts/init_databases.py` |
| Empty responses | Check API keys in .env (or use seed data) |
| ScriptRunContext warning | Normal in bare mode, ignore |
| Chat not responding | Check browser console (F12) for errors |

---

## What's Next

### For Development
- Modify queries in `test_e2e.py` and run
- Edit agent instructions in `agent_definitions/`
- Add new tools in `tools/` directory

### For Production
- Set real API keys in `.env`
- Run load tests: `python scripts/test_e2e.py`
- Monitor with observability stack (Phase 7)

---

## Support

### Check Logs
```bash
# Start with verbose logging
streamlit run app/main.py --logger.level=debug
```

### Run Tests
```bash
python scripts/test_e2e.py
# Should see 8/9 tests passing
```

### Read Documentation
- `PROJECT_STATUS.md` — Full project overview
- `PHASE_6_RESULTS.md` — Test results
- `TESTING_GUIDE.md` — Detailed test scenarios

---

## One-Line Summary

**RAG Conversational Engine**: Ask questions about employees or weather → AI routes to specialists (SQL/RAG) → Human approves if needed → Get grounded answers with citations.

🚀 Ready to try it? Run: `streamlit run app/main.py`
