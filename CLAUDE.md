# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**EIRA** (Intelligent Routing Agent) is a production-hardened multi-agent RAG conversational engine that intelligently routes queries across three data domains:
- **Employee data** (SQL queries via SQLAlchemy ORM against 500-row employee database)
- **Weather intelligence** (vector search from Chroma)
- **News retrieval** (vector search from Chroma)

The system uses Claude (claude-3-5-sonnet-20241022) as the primary LLM with GPT-4o fallback, orchestrated via the OpenAI Agents SDK with human-in-the-loop approval gates and zero-hallucination validation.

## Architecture & Data Flow

**Intent Classification → Parallel Execution → Validation → Grounding Check → Quality Gate → Response**

1. **EIRA** (Orchestrator) classifies user intent: SQL-only, RAG-only, or cross-domain query
2. **Parallel Agents Execute:**
   - **VEGA** (SQL specialist) → queries Employee table via `tools/sql_tools.py`
   - **NOVA** (RAG specialist) → vector search via `tools/chroma_tools.py`
   - **KIRA** → resolves fuzzy locations to canonical cities (10-city contract enforced across SQL and Chroma metadata)
3. **AXIOM** → pre-execution query validation (SQL injection checks, filter validation)
4. **SENTINEL** → post-generation groundedness checking (confidence scoring)
5. **VERIFIER** → quality assurance gate (semantic relevance, completeness, citations, coherence) ⭐ NEW
6. **Final Output** → structured EIRAResponse with citations, sources, and confidence scores

**Key Patterns**:
- Structured I/O schemas (pydantic_io.py) define all agent inputs/outputs for type safety
- Stale data, ambiguous matches, or low confidence trigger human approval workflows in `tools/hitl_tools.py`
- VERIFIER validates response against original question (5-metric quality scoring)
- If validation fails, VERIFIER triggers re-iteration with specific feedback

## Project Structure

```
rag-conversational-engine/
├── agents/               # [Phase 3+] Agent definitions (placeholder stubs)
├── tools/               # Function tools (core implementations)
│   ├── sql_tools.py    # ⭐ ORM query wrappers, SQL validation
│   ├── chroma_tools.py # ⭐ Vector search operations
│   ├── tavily_tools.py # Weather/news API client
│   ├── embedding_tools.py
│   ├── hitl_tools.py   # Human approval workflows
│   └── __init__.py
├── models/             # Data schemas (SQLAlchemy + Pydantic)
│   ├── employee.py    # ⭐ Employee ORM (500-row dataset)
│   ├── pydantic_io.py # ⭐ Agent I/O schemas
│   └── __init__.py
├── config/            # Tuning parameters
│   ├── constants.py   # ⭐ Canonical cities, departments, thresholds
│   ├── llm_config.py  # Claude/GPT-4o config
│   └── __init__.py
├── db/                # Database
│   ├── engine.py      # SQLAlchemy sync/async setup
│   ├── seed.py        # Deterministic 500-row seeding (Faker seed=42)
│   └── __init__.py
├── chroma/            # Vector store
│   ├── client.py      # Chroma singleton + collection management
│   └── __init__.py
├── app/               # Streamlit UI (entry point)
│   ├── main.py        # ⭐ Streamlit app entry point
│   ├── integration.py # ⭐ Anthropic SDK integration, run_eira_agent()
│   ├── wire_tools.py  # Tool registration for agents
│   ├── components.py  # UI components
│   └── __init__.py
├── tests/             # pytest suite
├── scripts/
│   └── validate_env.py # Environment validation
├── pyproject.toml     # Package config (hatchling backend)
├── .env.example       # Environment template
└── README.md
```

**Key Files** (⭐ = most critical for understanding architecture):
- `app/integration.py`: async `run_eira_agent()` orchestrates the Anthropic SDK multi-agent flow
- `tools/sql_tools.py`: SQL query safety + ORM wrapper
- `tools/chroma_tools.py`: Vector retrieval (TOP_K_RETRIEVAL=4) with metadata filtering
- `models/pydantic_io.py`: Defines contract between agents (IntentClassification, EIRAResponse)
- `config/constants.py`: Canonical cities (enforced across SQL + Chroma), tuning thresholds

## Common Development Tasks

### Setup
```bash
# Copy environment template
cp .env.example .env

# Install dependencies (recommended with uv)
uv sync
# OR: python -m venv .venv && pip install -e .

# Validate environment
python scripts/validate_env.py
```

### Initialize Data
```bash
# Create SQLite employee DB + seed 500 rows
python -m db.seed

# Initialize Chroma vector store
python -c "from chroma.client import init_chroma; init_chroma()"
```

### Run Application
```bash
# Launch Streamlit UI (port 8501)
streamlit run app/main.py
```

### Testing
```bash
pytest                                      # All tests
pytest -m integration                       # Integration tests only (requires real APIs)
pytest --cov=agents --cov=tools --cov-report=html  # Coverage report
pytest tests/test_sql_tools.py -v          # Single test file
```

## Configuration & Constraints

### Environment Variables (.env)
```bash
ANTHROPIC_API_KEY=sk-ant-...           # Required
OPENAI_API_KEY=sk-...                  # Required (SDK dependency)
TAVILY_API_KEY=tvly-...                # Required for weather/news
DATABASE_URL=sqlite:///./data/employees.db
SESSION_DATABASE_URL=sqlite+aiosqlite:///./data/agent_sessions.db
CHROMA_HOST=embedded                   # or hostname for HTTP
DEBUG_AGENTS=false
LOG_LEVEL=INFO
```

### Canonical Cities Contract
Enforced across both SQL queries and Chroma metadata (location_normalized):
```
Austin TX, Seattle WA, New York NY, Chicago IL, Denver CO,
Boston MA, Atlanta GA, Miami FL, London UK, Toronto CA
```
**KIRA resolution threshold**: 0.80 (location ambiguity resolution confidence)

### Tuning Thresholds (config/constants.py)
- `SENTINEL_CONFIDENCE_THRESHOLD`: 0.75 (groundedness checking)
- `AXIOM_OVERWRITE_THRESHOLD`: 0.80 (filter overwriting)
- `WEATHER_FRESHNESS_HOURS`: 6 (data staleness detection)
- `TOP_K_RETRIEVAL`: 4 (Chroma vector results per query)

### Data Models
- **Employee Table**: employee_id (PK), name, age (22–65 validated), department, office_location (canonical city indexed)
- **Chroma Collections**:
  - `weather_embeddings`: {location_normalized, fetched_at, conditions, temp_c}
  - `news_embeddings`: {topic, source, fetched_at, region}

## Key Technologies

| Technology | Role | Min Version |
|-----------|------|------------|
| **Anthropic SDK** | Claude API (primary LLM) | 0.25.0+ |
| **OpenAI SDK** | GPT-4o fallback + embeddings | 1.30.0+ |
| **OpenAI Agents SDK** | Multi-agent orchestration | 0.0.19+ |
| **SQLAlchemy** | ORM for employee queries | 2.0.0+ |
| **ChromaDB** | Vector store | 0.5.0+ |
| **sentence-transformers** | Local embeddings (all-MiniLM-L6-v2, 384 dims) | 3.0.0+ |
| **Tavily Python** | Weather/news API client | 0.3.0+ |
| **Streamlit** | Web UI | 1.35.0+ |
| **Pydantic** | Schema validation | 2.7.0+ |

## Guardrails System — Security & Defense-in-Depth

All data flow through the system passes through **guardrails/** security layers:

**5-Layer Defense:**
1. **Input Validation** → Unicode normalization, sanitization, whitelist checking
2. **AXIOM Layer** (SQL Safety) → SQL injection prevention, parameterized queries, dangerous keyword detection
3. **Schema Enforcement** → Canonical cities contract, department validation, embedding dims, metadata contracts
4. **Execution** → Database/Vector operations with validated inputs
5. **SENTINEL Layer** (Output Validation) → Grounding checks, freshness validation, citation verification

**Covered Attack Vectors:**
- ✅ SQL injection (union, comments, stacked queries, blind injection, hex encoding)
- ✅ XSS & HTML injection
- ✅ Command injection
- ✅ Schema violations (non-canonical cities, invalid departments)
- ✅ Hallucinations (ungrounded claims)
- ✅ Stale data (freshness checks)
- ✅ Embedding model swaps (dimension validation)

**Quick Integration:**
```python
from guardrails import (
    validate_sql_query,
    sanitize_input_string,
    validate_response_grounding,
)

# Validate before execution
result = validate_sql_query(user_query)
if result.is_blocked:
    return {"error": "Query blocked"}

# Sanitize user input
clean_input, warnings = sanitize_input_string(user_input)

# Validate response for hallucinations
grounding_report = validate_response_grounding(response, sources, min_confidence=0.75)
if not grounding_report.passes:
    trigger_hitl_approval(grounding_report.ungrounded_claims)
```

See **guardrails/GUARDRAILS.md** for comprehensive documentation, module reference, and testing guide.

---

## VERIFIER Agent — Quality Assurance Gate

The **VERIFIER** agent is the final quality gate before responses reach users. It validates that responses adequately address the original question through 5 metrics:

**Validation Metrics (weighted):**
- **Semantic Relevance** (30%) — Does answer match question intent?
- **Completeness** (25%) — Are all question aspects covered?
- **Citation Coverage** (25%) — Is response adequately sourced?
- **Coherence** (15%) — Is answer logically structured?
- **Confidence Consistency** (5%) — Does confidence align with quality?

**Decision Logic:**
- ✅ **Accept** — Passes all checks (overall ≥ 0.75, no critical issues)
- 🔄 **Re-iterate** — Issues found; provide feedback to EIRA for re-query
- ❓ **Clarify** — Ask user for clarification

**Quick Integration:**
```python
from agents.verifier import verifier

passes, response, report = await verifier.verify_response(
    original_question=user_query,
    response=eira_response,
    intent_classification=intent,
    attempt=1,
)

if passes:
    return response  # User gets response
else:
    # Trigger re-iteration with feedback
    return await re_query_with_feedback(report)
```

See **VERIFIER_GUIDE.md** for comprehensive documentation, validation metrics, and integration patterns.

---

## Important Patterns & Conventions

### Zero-Hallucination Policy
- **SENTINEL** validates all generated responses for groundedness before delivery
- All claims must be backed by source citations (chunk_id or sql:employee_id:*)
- Low confidence (<0.75) or stale data triggers human-in-the-loop approve workflows
- All responses include source citations and confidence scores

### Canonical City Contract
- Any user mention of a location must resolve to one of 10 canonical cities
- KIRA handles fuzzy matching (e.g., "NYC" → "New York NY")
- SQL queries filter on `office_location` IN (canonical cities)
- Chroma metadata includes `location_normalized` for consistency

### SQL Safety
- All employee queries go through `tools/sql_tools.py` (ORM wrapper, no raw SQL)
- AXIOM pre-validates queries for injection and filter bypass
- Employee table is read-only in production

### Structured I/O
- All agent communication defined in `pydantic_io.py` schemas
- IntentClassification, EIRAResponse, EmployeeQueryResult, ChunkSource, LocationResolution, ValidationResult
- Enables type-safe agent chaining and output validation

### Human-in-the-Loop Gates
- Ambiguous location resolution (<0.80 confidence)
- Low groundedness scores (<0.75)
- Stale data (weather >6 hours, news >24 hours)
- Trigger approval workflow via `tools/hitl_tools.py`

## Development Status & Roadmap

Per README:
- **Phase 0**: ✅ COMPLETE (Foundation, dependencies, environment setup)
- **Phases 1–7**: ⏳ PENDING (Agent implementations, production hardening)

**Note**: Agent definitions in `agents/` are currently placeholder stubs. The actual orchestration happens in `app/integration.py` via the Anthropic SDK with tool-calling capabilities. As agents mature, their implementations will move into the `agents/` directory following the same structural pattern.

## Quick Reference: Entry Points

| Entry Point | Purpose | Execute |
|-----------|---------|---------|
| **Streamlit App** | Web UI for user queries | `streamlit run app/main.py` |
| **Agent Orchestrator** | Core EIRA logic | `app/integration.py::run_eira_agent()` |
| **Database Init** | Employee DB setup | `python -m db.seed` |
| **Vector Store Init** | Chroma initialization | `python -c "from chroma.client import init_chroma; init_chroma()"` |
| **Environment Check** | Validate .env and API keys | `python scripts/validate_env.py` |
