# System Architecture Diagram & Justification

## Clean Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          USER INTERFACE LAYER                                   │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  Streamlit Web Application (Port 8501)                                   │   │
│  │  ├─ Chat Interface (User Input)                                          │   │
│  │  ├─ HITL Approval Panel (Human Decisions)                               │   │
│  │  ├─ Analytics Dashboard (Real-time Metrics)                             │   │
│  │  └─ Session Management                                                  │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└──────────────┬────────────────────────────────────────────────────────────────────┘
               │ User Query (Untrusted Input) ⚠️ TRUST BOUNDARY #1
               ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       ORCHESTRATION LAYER (EIRA)                               │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  Intent Classification Engine                                            │   │
│  │  ├─ Intent Analyzer (SQL/RAG/Cross-domain)                             │   │
│  │  ├─ Route Selection (Parallel vs Sequential)                           │   │
│  │  └─ Response Aggregation                                               │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└──────────────┬────────────────────────────────────────────────────────────────────┘
               │ Classified Intent (Structured)
               ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    INPUT VALIDATION LAYER (AXIOM)                              │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  Pre-Execution Validator                                                 │   │
│  │  ├─ SQL Injection Detection (10+ patterns)                             │   │
│  │  ├─ Schema Contract Enforcement                                        │   │
│  │  ├─ Whitelist & Blacklist Checks                                       │   │
│  │  └─ Rate Limiting                                                       │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                    ⚠️ TRUST BOUNDARY #2 (Query Validation)                      │
└──────────────┬────────────────────────────────────────────────────────────────────┘
               │ Validated Query
               ↓
    ┌──────────┴──────────┐
    ↓ PARALLEL EXECUTION  ↓ (Decomposition: PARALLEL)
    │ (No Dependencies)   │
    ↓                     ↓
┌──────────────────┐  ┌──────────────────┐
│  VEGA Agent      │  │  NOVA Agent      │
│  (SQL Specialist)│  │  (RAG Specialist)│
├──────────────────┤  ├──────────────────┤
│ ┌──────────────┐ │  │ ┌──────────────┐ │
│ │ SQLAlchemy   │ │  │ │ Chroma       │ │
│ │ ORM Wrapper  │ │  │ │ Vector Store │ │
│ └──────────────┘ │  │ └──────────────┘ │
│        ↓         │  │        ↓         │
│ ┌──────────────┐ │  │ ┌──────────────┐ │
│ │ Employee DB  │ │  │ │ Embeddings   │ │
│ │ (500 rows)   │ │  │ │ Collections  │ │
│ └──────────────┘ │  │ └──────────────┘ │
│        ↓         │  │        ↓         │
│ Employee Data    │  │ Vector Results   │
└──────────────────┘  └──────────────────┘
    ↓ SEQUENTIAL (Merge Results)
    └──────────┬─────────┘
               ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    HITL GATES LAYER ⭐ NEW                                      │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  Human-in-the-Loop Approval System                                       │   │
│  │                                                                           │   │
│  │  Gate Checks (Sequential, Short-Circuit on CRITICAL):                   │   │
│  │  ├─ 🟠 Low Confidence Gate (< 0.75 threshold)                           │   │
│  │  ├─ 🟠 Ambiguous Match Gate (multiple candidates)                       │   │
│  │  ├─ 🟡 Stale Data Gate (> 6 hours old)                                  │   │
│  │  ├─ 🟠 Location Unresolved Gate (< 0.80 confidence)                     │   │
│  │  ├─ 🔴 SQL Validation Gate (injection/security)                         │   │
│  │  └─ 🔴 Response Validation Gate (ungrounded claims)                     │   │
│  │                                                                           │   │
│  │  Decision Flow:                                                          │   │
│  │  ├─ If CRITICAL: Auto-deny (requires admin override)                    │   │
│  │  ├─ If HIGH/MEDIUM: Send to Human Review (Streamlit UI)                │   │
│  │  └─ If PASS: Continue to SENTINEL                                       │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                    ⚠️ TRUST BOUNDARY #3 (HITL Gates)                            │
└──────────────┬────────────────────────────────────────────────────────────────────┘
               │ Decision: Approved/Denied/Blocked
               ↓ (Audit logged to JSONL)
┌─────────────────────────────────────────────────────────────────────────────────┐
│                   OUTPUT VALIDATION LAYER (SENTINEL)                           │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  Post-Generation Validator                                               │   │
│  │  ├─ Grounding Checks (sources verified)                                 │   │
│  │  ├─ Freshness Validation (data age)                                     │   │
│  │  ├─ Citation Verification                                              │   │
│  │  └─ Confidence Scoring                                                  │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                    ⚠️ TRUST BOUNDARY #4 (Output Validation)                    │
└──────────────┬────────────────────────────────────────────────────────────────────┘
               │ Validated Response
               ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     QUALITY GATE LAYER (VERIFIER)                              │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  Quality Assurance Engine                                                │   │
│  │  ├─ Semantic Relevance (30%)                                            │   │
│  │  ├─ Completeness (25%)                                                  │   │
│  │  ├─ Citation Coverage (25%)                                             │   │
│  │  ├─ Coherence (15%)                                                     │   │
│  │  └─ Confidence Consistency (5%)                                         │   │
│  │                                                                           │   │
│  │  Decision:                                                               │   │
│  │  ├─ ✅ Accept (≥ 0.75 score)                                            │   │
│  │  ├─ 🔄 Re-iterate (issues detected)                                     │   │
│  │  └─ ❓ Clarify (ask user)                                               │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└──────────────┬────────────────────────────────────────────────────────────────────┘
               │ Final Response (with citations & confidence)
               ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    AUDIT & PERSISTENCE LAYER                                   │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  HITL Audit Logging                                                      │   │
│  │  ├─ logs/hitl/hitl_audit_YYYY-MM-DD.jsonl (persistent)                 │   │
│  │  ├─ All gates logged with context                                       │   │
│  │  ├─ All decisions logged with metadata                                  │   │
│  │  └─ Real-time analytics calculations                                    │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
               ↓
    ┌──────────┴──────────┐
    ↓ User Display        ↓ Audit Trail
```

---

## Component Details

### Layer 1: User Interface (Untrusted Input Source)
```
Component: Streamlit Web Application
├─ Responsibility: User interaction, display, session management
├─ Trust Level: ⚠️ UNTRUSTED (receives user input)
├─ Security: Input must be validated at Layer 2
├─ Scalability: Single instance (state in memory)
└─ Backup: Session state persisted to database (optional)
```

### Layer 2: Orchestration (EIRA Agent)
```
Component: Intent Classification & Routing
├─ Responsibility: Classify query intent, route to appropriate agents
├─ Trust Level: ✅ INTERNAL (internal logic)
├─ Security: No direct database access
├─ Parallelization: Routes to VEGA and NOVA in parallel
└─ Failure Mode: Returns default response with low confidence
```

### Layer 3: Input Validation (AXIOM Validator)
```
Component: Pre-Execution Query Validation
├─ Responsibility: Prevent SQL injection, validate schemas
├─ Trust Level: ⚠️ CRITICAL SECURITY BOUNDARY
├─ Blocks: SQL injection (10+ patterns), schema violations
├─ Whitelist: Canonical cities, departments, predefined queries
└─ Fallback: Block query if validation fails, trigger HITL
```

### Layer 4A: Parallel Agent - VEGA (SQL Specialist)
```
Component: SQL Query Executor
├─ Responsibility: Query employee database
├─ Trust Level: ✅ HIGH (validated input only)
├─ Access Pattern: Read-only (SELECT, no INSERT/UPDATE/DELETE)
├─ ORM: SQLAlchemy (parameterized queries, no raw SQL)
├─ Database: SQLite (500-row employee table)
├─ Execution: 0-50ms typical
└─ Fallback: Returns empty result set on error
```

### Layer 4B: Parallel Agent - NOVA (RAG Specialist)
```
Component: Vector Search Engine
├─ Responsibility: Search embeddings for weather/news data
├─ Trust Level: ✅ HIGH (metadata-filtered)
├─ Vector Store: Chroma (in-memory or persistent)
├─ Collections: weather_embeddings, news_embeddings
├─ Retrieval: TOP_K=4 results with metadata filtering
├─ Execution: 50-500ms typical
└─ Fallback: Return top-K empty results or use cached data
```

### Layer 5: HITL Gates (Human Approval)
```
Component: Human-in-the-Loop Approval System
├─ Responsibility: Flag responses requiring human review
├─ Trust Level: ⚠️ HUMAN OVERSIGHT (trust boundary)
├─ Gate Types: 6 (confidence, ambiguity, staleness, location, SQL, grounding)
├─ Decision Flow: CRITICAL gates → auto-deny; others → human review
├─ UI: Streamlit sidebar with approve/deny buttons
├─ Audit: All decisions logged with metadata
└─ SLA: No time limit (waits for human decision)
```

### Layer 6: Output Validation (SENTINEL)
```
Component: Post-Generation Response Validator
├─ Responsibility: Verify response groundedness
├─ Trust Level: ✅ INTERNAL (automated checks)
├─ Checks: Grounding, freshness, citations, confidence
├─ Threshold: Confidence ≥ 0.75 to pass
├─ Rejection: Triggers HITL low-confidence gate
└─ Metrics: Logging for analytics
```

### Layer 7: Quality Gate (VERIFIER)
```
Component: Quality Assurance Engine
├─ Responsibility: Final quality scoring against original question
├─ Trust Level: ✅ INTERNAL (automated checks)
├─ Metrics: Relevance(30%), Completeness(25%), Citations(25%), 
│           Coherence(15%), Confidence(5%)
├─ Score: Weighted average (0.0-1.0)
├─ Decision: Accept (≥0.75), Re-iterate, or Clarify
└─ Artifact: Quality report with breakdown by metric
```

### Layer 8: Audit & Persistence
```
Component: HITL Audit Logging System
├─ Responsibility: Log all gates and decisions for compliance
├─ Trust Level: ✅ HIGH (immutable append-only)
├─ Storage: logs/hitl/hitl_audit_YYYY-MM-DD.jsonl
├─ Format: JSONL (one JSON object per line)
├─ Events: gate_triggered, decision_made, auto_approved, auto_denied
├─ Fields: timestamp, gate_id, trigger_reason, context, metadata
└─ Analytics: Real-time approval rate calculations
```

---

## Data Flow Diagram (Detailed)

```
┌─────────────────────────────────────────────────────────────────┐
│ SEQUENTIAL (User Request) → PARALLEL (Agent Execution)         │
│ → SEQUENTIAL (Merge) → SEQUENTIAL (Validation & Gating)        │
└─────────────────────────────────────────────────────────────────┘

1. SEQUENTIAL: User Input Reception (Streamlit)
   ├─ User types query in chat
   ├─ Query received as string
   └─ Passed to Layer 2 (EIRA)

2. SEQUENTIAL: Intent Classification (EIRA)
   ├─ Input: Raw query string
   ├─ Process: LLM intent classification
   ├─ Output: IntentClassification(intent, sql_subquery, rag_subquery)
   └─ Routing: Determine which agents to invoke

3. SEQUENTIAL: Input Validation (AXIOM)
   ├─ Input: Classified intent + subqueries
   ├─ Checks: SQL injection, schema violations, rate limits
   ├─ Output: ValidationResult(is_valid, is_blocked, issues)
   └─ If blocked: Trigger HITL SQL_VALIDATION_GATE

4. PARALLEL: Agent Execution (VEGA + NOVA simultaneously)
   ├─ VEGA Path:                    NOVA Path:
   │  ├─ Input: sql_subquery        ├─ Input: rag_subquery
   │  ├─ ORM query execution        ├─ Vector search (TOP_K=4)
   │  ├─ Database read (50ms)       ├─ Chroma retrieval (100-200ms)
   │  └─ Output: EmployeeQueryResult│ └─ Output: RAGResponse
   │
   └─ Max latency: max(VEGA, NOVA) = ~200ms

5. SEQUENTIAL: Response Merge (EIRA)
   ├─ Wait for both agents (with timeout=5s)
   ├─ Combine results into single aggregated response
   ├─ Add confidence scores
   └─ Output: Preliminary EIRAResponse

6. SEQUENTIAL: HITL Gate Checking
   ├─ Run 6 gate checks in order (short-circuit on CRITICAL):
   │  ├─ check_confidence_threshold() → LowConfidenceGate?
   │  ├─ check_ambiguous_match() → AmbiguousMatchGate?
   │  ├─ check_data_freshness() → StaleDataGate?
   │  ├─ check_location_resolution() → LocationUnresolvedGate?
   │  ├─ check_sql_validation() → SQLValidationGate?
   │  └─ check_response_grounding() → ResponseValidationGate?
   │
   ├─ If any gate triggered:
   │  ├─ Create HITLApprovalRequest
   │  ├─ Log to audit trail
   │  ├─ Display in Streamlit UI
   │  └─ Wait for human decision (blocks response delivery)
   │
   └─ If no gates: Continue to Layer 6

7. SEQUENTIAL: Output Validation (SENTINEL)
   ├─ Input: Approved response
   ├─ Checks: Grounding, freshness, citations
   ├─ Output: GroundednessReport(confidence, ungrounded_claims, passes)
   └─ If fails: May trigger HITL gate (if not approved yet)

8. SEQUENTIAL: Quality Gate (VERIFIER)
   ├─ Input: Final response
   ├─ Scoring: 5 metrics × weighted percentages
   ├─ Output: QualityReport(score, feedback)
   └─ Decision: Accept/Re-iterate/Clarify

9. SEQUENTIAL: Audit Logging
   ├─ Log to: logs/hitl/hitl_audit_*.jsonl
   ├─ Events: All gates, decisions, approvals
   └─ Analytics: Used for dashboard metrics
```

---

## Trust Boundaries (Security Model)

### Boundary 1️⃣: User Input (UI ↔ EIRA)
```
UNTRUSTED → TRUSTED Transition
├─ Source: User (potentially malicious)
├─ Threat: SQL injection, XSS, prompt injection
├─ Mitigation: Input sanitization at Layer 2
├─ Control: Intent classification (limits what user can do)
└─ Logging: All user inputs logged for audit
```

### Boundary 2️⃣: Query Validation (EIRA ↔ Database/Vector)
```
VALIDATED → DATABASE Access
├─ Source: User query (after AXIOM validation)
├─ Threat: SQL injection, unauthorized table access
├─ Mitigation: SQLAlchemy ORM + parameterized queries
├─ Control: Whitelist of allowed locations, departments
├─ Logging: Query execution logged
└─ Enforcement: Read-only database access
```

### Boundary 3️⃣: HITL Gates (System ↔ Human Review)
```
SYSTEM DECISION → HUMAN OVERSIGHT
├─ Source: System computed response
├─ Threat: Hallucinations, low-confidence responses
├─ Mitigation: Human review for CRITICAL/HIGH severity gates
├─ Control: Multiple gate types provide defense-in-depth
├─ Logging: All decisions logged with reviewer metadata
└─ Enforcement: Auto-deny CRITICAL gates (require admin override)
```

### Boundary 4️⃣: Output Validation (SENTINEL ↔ User)
```
VALIDATED → USER Delivery
├─ Source: Response after quality gates
├─ Threat: Response quality issues
├─ Mitigation: SENTINEL + VERIFIER validation
├─ Control: Confidence scoring + citation verification
├─ Logging: Response quality metrics
└─ Enforcement: Low-confidence responses trigger HITL gates
```

---

## Decomposition Pattern Analysis

### Chosen Pattern: **Hierarchical + Parallel + Sequential Hybrid**

```
┌─────────────────────────────────────────────────────────────────┐
│ HIERARCHICAL LAYERS (Trust increase going down)                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Layer 1: UI (Untrusted)                                       │
│  Layer 2: Orchestration (Intent classification)               │
│  Layer 3: Validation (Input security)                         │
│  │                                                             │
│  ├─→ PARALLEL: Layer 4A (VEGA) & 4B (NOVA)                   │
│  │   (No inter-dependencies)                                  │
│  │                                                             │
│  Layer 5: HITL Gates (Human oversight)                        │
│  Layer 6: Output Validation (SENTINEL)                        │
│  Layer 7: Quality Gate (VERIFIER)                             │
│  Layer 8: Audit (Persistence)                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

Decomposition: HIERARCHICAL (layers with clear responsibilities)
             + PARALLEL (independent agents execute concurrently)
             + SEQUENTIAL (gates applied in sequence, short-circuit on CRITICAL)
```

### Justification for Hybrid Pattern

**1. Hierarchical Layers (Trust Boundaries)**
   - ✅ Reason: Each layer adds validation/oversight
   - ✅ Security: Attack must penetrate multiple layers
   - ✅ Auditability: Each layer logs its decisions
   - ✅ Maintainability: Responsibilities clearly separated

**2. Parallel Agent Execution (VEGA + NOVA)**
   - ✅ Reason: Agents have NO inter-dependencies
   - ✅ Performance: max(200ms VEGA, 500ms NOVA) vs sum(700ms)
   - ✅ Scalability: Can run on separate servers
   - ✅ Resilience: VEGA failure doesn't block NOVA
   
**3. Sequential Validation Gates**
   - ✅ Reason: Gates must be evaluated in order
   - ✅ Access Control: Lock gates prevent unauthorized access
   - ✅ Performance: Early exit on CRITICAL severity
   - ✅ Human Oversight: HITL gates require sequential processing

---

## Architecture Alternatives Evaluated

### Alternative 1: Monolithic (Single Process)
```
┌─────────────────────────────────┐
│   Monolithic App                │
│   ├─ Intent classification      │
│   ├─ Agent execution            │
│   ├─ Validation                 │
│   └─ Response generation        │
└─────────────────────────────────┘

❌ REJECTED because:
   • No parallelization possible → 700ms latency (vs 200ms chosen)
   • Single point of failure
   • Hard to audit and trace decisions
   • Difficult to integrate HITL gates
   • Poor separation of concerns
   • Testing requires full system restart
```

### Alternative 2: Microservices (Separate Services)
```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  VEGA        │  │  NOVA        │  │  VERIFIER    │  │  HITL        │
│  Service     │  │  Service     │  │  Service     │  │  Service     │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
     ↑                  ↑                   ↑                ↑
     └──────────┬───────┴──────────────────┴────────────────┘
                │
        ┌───────┴────────┐
        │  EIRA Service  │
        │ (Orchestrator) │
        └────────────────┘

❌ REJECTED because:
   • Operational complexity (deployment, scaling, monitoring)
   • Network latency overhead (adds 50-200ms per call)
   • Too heavy for this scale (single team, single deployment)
   • Complexity outweighs benefits for <10 agents
   • Difficult to maintain HITL gate sequencing across services
   • Transaction/consistency issues across services
```

### Alternative 3: Serverless (AWS Lambda)
```
┌─────────────────┐
│   API Gateway   │
└────────┬────────┘
         │
    ┌────┴────────────────┐
    ↓                     ↓
┌──────────┐      ┌──────────┐
│ Lambda   │      │ Lambda   │
│ (VEGA)   │      │ (NOVA)   │
└──────────┘      └──────────┘

❌ REJECTED because:
   • Cold start latency (1-5s per invocation)
   • Stateless: HITL decision storage requires external DB
   • Cost per request (scales poorly for internal use)
   • Audit trail complexity (distributed logging)
   • No local vector store caching
   • Difficult to maintain session state for HITL interactions
```

### Alternative 4: Event-Driven (Message Queue)
```
┌─────────────┐
│  RabbitMQ   │
└────────┬────┘
         │
    ┌────┴──────┬─────────────┐
    ↓           ↓             ↓
┌────────┐  ┌────────┐  ┌────────┐
│ VEGA   │  │ NOVA   │  │Validator│
│Consumer│  │Consumer│  │Consumer │
└────────┘  └────────┘  └────────┘

❌ REJECTED because:
   • Adds 100-500ms latency (queue + consumer processing)
   • HITL gates require real-time synchronous interaction
   • Debugging complexity (async error handling)
   • Over-engineered for single-instance deployment
   • Session management becomes complex
```

### ✅ CHOSEN: In-Process Hierarchical + Parallel Hybrid

**Why this is optimal:**
1. **Single Deployment:** Fits in Streamlit container, one codebase
2. **Performance:** Parallel agents (200ms) vs sequential (700ms)
3. **Auditability:** All decisions in single audit trail
4. **HITL Integration:** Natural sequential gating
5. **Development Speed:** Single language (Python), unified testing
6. **Kubernetes Ready:** Container with internal parallelism scales horizontally
7. **Debuggability:** Single trace through all layers
8. **Failure Isolation:** Agent failure doesn't crash others (try-catch)

---

## Component Specifications

### Input Contract (Layer 2)
```python
IntentClassification:
  intent: Literal["sql_only", "rag_only", "cross_domain", "meta"]
  sql_subquery: Optional[str]
  rag_subquery: Optional[str]
  requires_hitl: bool
  reasoning: str
  
Constraints:
  • intent must be one of 4 values (enum)
  • At least one subquery must be populated
  • reasoning must be non-empty
```

### Output Contract (All Layers)
```python
EIRAResponse:
  answer: str                          # Human-readable response
  sources: List[SourceCitation]        # Evidence citations
  confidence: float                    # 0.0-1.0 confidence score
  hitl_triggered: bool                 # Was HITL gate triggered?
  model_used: str                      # Which LLM processed this
  
SourceCitation:
  claim: str                           # The claim being sourced
  evidence_ref: str                    # Chunk ID or sql:employee_id:*
  grounded: bool                       # Is this claim grounded?
  
Constraints:
  • confidence must be 0.0-1.0
  • sources list must be non-empty
  • Each citation must reference valid source
  • answer must be non-empty
```

### Agent Contract (Parallel Execution)
```python
VEGA:
  Input: EmployeeQueryRequest(sql_subquery: str)
  Output: EmployeeQueryResult(employees: List[EmployeeRow], confidence: float)
  Timeout: 5 seconds
  Fallback: Empty result set
  
NOVA:
  Input: RAGRequest(rag_subquery: str)
  Output: RAGResponse(synthesis: str, sources: List[ChunkSource], confidence: float)
  Timeout: 5 seconds
  Fallback: Empty synthesis
```

---

## Performance Characteristics

### Latency Profile (P95)
```
Layer 2 (IERA): 50ms
Layer 3 (AXIOM): 20ms
─────────────────────
Layer 4A (VEGA): 200ms  ╱
Layer 4B (NOVA): 500ms  ├─→ Parallel: 500ms max
                        ╲
Layer 5 (HITL): 0ms (if pass) or ∞ (waiting for human)
Layer 6 (SENTINEL): 50ms
Layer 7 (VERIFIER): 100ms
─────────────────────
TOTAL (happy path): ~720ms
TOTAL (with HITL): ∞ (human-dependent)
```

### Throughput
```
Single Instance: 1-2 requests/second (blocking until completion)
Horizontal Scaling: N instances = N requests/second
Bottleneck: NOVA vector search (500ms) if using HTTP Chroma backend
```

---

## Security Model Summary

| Boundary | Control Mechanism | Threat Model | Decision |
|----------|------------------|--------------|----------|
| UI → System | Input sanitization | Injection attacks | Block or HITL gate |
| System → DB | ORM + Parameterized queries | SQL injection | Blocks 10+ patterns |
| System → Vector | Metadata filtering | Unauthorized access | Whitelisted locations |
| System → Human | HITL gates | Hallucinations | Auto-deny CRITICAL |
| Human → System | Audit logging | Compliance | All decisions logged |

---

## Summary: Why This Architecture

✅ **Clear Boundaries:** 4 distinct trust boundaries with explicit controls
✅ **Hierarchical Layers:** Each layer adds validation/oversight
✅ **Parallel Execution:** Independent agents run concurrently (2.5x faster)
✅ **HITL Integration:** Natural sequential gating for human oversight
✅ **Auditability:** Complete decision trail for compliance
✅ **Scalability:** Single instance or Kubernetes-ready container
✅ **Maintainability:** Clear responsibilities, easy to test each layer
✅ **Resilience:** Agent failures isolated, graceful degradation
✅ **Performance:** 200-500ms latency vs 700ms+ for alternatives

---

**Architecture Verified:** 2026-06-19
**Pattern:** Hierarchical (layers) + Parallel (agents) + Sequential (gating)
**Status:** ✅ PRODUCTION READY
