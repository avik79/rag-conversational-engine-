# Phase 3: Agent Definitions — COMPLETE ✅

**Date**: 2026-06-12  
**Status**: All 7 agent definitions implemented and verified

## Summary
Implemented all core agents with complete instruction logic, Pydantic I/O schemas, tool placeholders, and handoff declarations. Each agent has a clear role, constraints, and validation rules aligned to handoff.md §1.4.

## Files Delivered (7 agents)

### 1. **agents/axiom.py** (60 LOC)
**Role**: Pre-execution query validator  
**Key Features**:
- SQL injection pattern detection (UNION, DROP, INSERT, DELETE, etc.)
- Column existence validation via schema snapshot
- Semantic query correctness checks
- Chroma filter key existence validation
- Returns `ValidationResult` with `is_valid`, `is_blocked`, `safe_to_execute`, `issues[]`

### 2. **agents/sentinel.py** (65 LOC)
**Role**: Post-generation hallucination detector  
**Key Features**:
- Entity grounding against retrieved chunks
- Location consistency validation
- Numeric accuracy checks
- Freshness validation (warns if data >6hrs old)
- Scoring: starts 1.0, deducts per violation
  - Ungrounded entity: -0.25
  - Numeric mismatch: -0.15
  - Freshness failure: -0.20
  - Missing attribution: -0.10
- Returns `GroundednessReport` with `confidence`, `ungrounded_claims[]`, `passes`, `freshness_ok`, `citations[]`

### 3. **agents/vega.py** (55 LOC)
**Role**: SQL specialist for employee database  
**Key Features**:
- NL → SQLAlchemy ORM translation
- Pre-execution validation via AXIOM call
- Flags ambiguous name matches (sets `ambiguous_match=True`)
- Returns raw SQL string for audit
- Never guesses column values
- Returns `EmployeeQueryResult` with `employees[]`, `query_sql`, `row_count`, `confidence`, `ambiguous_match`

### 4. **agents/nova.py** (60 LOC)
**Role**: RAG specialist for weather/news  
**Key Features**:
- Validates Chroma filters before querying (calls AXIOM)
- Always includes `ChunkSource` citations (chunk_id, collection, fetched_at)
- Checks data freshness: if most recent chunk >6hrs old, sets `freshness_ok=False`
- Never synthesizes from missing chunks
- Returns `RAGResponse` with `synthesis`, `sources[]`, `freshness_ok`, `confidence`

### 5. **agents/kira.py** (50 LOC)
**Role**: Semantic location resolver  
**Key Features**:
- 4-step resolution pipeline:
  1. Exact string match → `confidence=1.0`, `match_method="exact"`
  2. Fuzzy matching (Levenshtein ≤2) → `confidence=0.9`, `match_method="fuzzy"`
  3. Semantic embedding + cosine similarity → `confidence=similarity_score`, `match_method="semantic"`
  4. Failure → `match_method="failed"`, `needs_clarification=True`, `confidence=0.0`
- Never returns `needs_clarification=False` if `confidence < 0.80`
- Returns `LocationResolution` with `raw_input`, `canonical_key`, `confidence`, `match_method`, `needs_clarification`

### 6. **agents/iris.py** (70 LOC)
**Role**: Ingestion specialist (Tavily → Chroma)  
**Key Features**:
- **ONLY agent with Chroma write access**
- All weather chunks MUST have `location_normalized` from `CANONICAL_CITIES`
- Validates location contract before batch upsert
- HITL gate if ingestion would overwrite >80% of collection
- Tracks: `chunks_ingested`, `chunks_rejected`, `rejection_reasons[]`, `location_contract_violations[]`, `ingestion_timestamp`
- Uses OpenAI text-embedding-3-small (must match NOVA's query-time model)
- Returns `IngestionReport`

### 7. **agents/eira.py** (140 LOC)
**Role**: Orchestrator entry point  
**Key Features**:
- Dynamic instructions include session context (`turn_count`, `user_name`)
- Intent classification: `sql_only | rag_only | cross_domain | meta | unclear`
- Routing logic for cross-domain queries:
  1. Call VEGA → get `office_location`
  2. Call KIRA → resolve to canonical city
  3. Call NOVA → retrieve weather context
- Pre-query validation: calls AXIOM before execution
- Post-synthesis validation: calls SENTINEL, triggers HITL if confidence <0.75
- Handoff declarations to VEGA, NOVA, IRIS with `input_filter=remove_all_tools`
- `HandoffMetadata` class for structured handoff routing (`reason`, `subquery`)
- Returns `EIRAResponse`

## Architectural Decisions

### Intent Classification Flow
```
User Query
    ↓
EIRA (classify intent)
    ├─ sql_only → VEGA.as_tool()
    ├─ rag_only → NOVA.as_tool()
    ├─ cross_domain → VEGA → KIRA → NOVA
    ├─ meta → internal reasoning
    └─ unclear → HITL gate
```

### Validation Pipeline
```
Query → AXIOM (pre-check) → execute → SENTINEL (post-check) → HITL? → synthesize
```

### HITL Triggers
- **AXIOM**: `is_blocked=True` → block immediately
- **VEGA**: `ambiguous_match=True` → HITL approval needed
- **KIRA**: `needs_clarification=True` → HITL approval needed
- **SENTINEL**: `confidence < 0.75` → HITL approval needed
- **IRIS**: >80% collection overwrite → HITL approval needed

## Verification

✅ All 7 agent files created  
✅ All agents have proper I/O Pydantic types  
✅ All agents have role-specific instructions  
✅ All agents have tool placeholders (ready for Phase 4 wiring)  
✅ All agents have appropriate `tool_use_behavior` settings  
✅ EIRA has full handoff declarations  
✅ SENTINAL scoring formula verified  
✅ KIRA resolution pipeline complete  
✅ IRIS location contract enforced  

## Next Phase
**Phase 4 - Tool Implementations & Agent Wiring**:
- Create 12 function tools (SQL, Chroma, Tavily, embeddings, HITL)
- Wire agent-as-tool references in EIRA
- Implement hooks (PreToolUse, PostToolUse)

**Ready to proceed to Phase 4? Answer: YES/NO**
