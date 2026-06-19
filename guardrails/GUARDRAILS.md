# Guardrails Module Documentation

## Overview

The **guardrails** module implements a defense-in-depth security architecture to prevent SQL injection, data validation failures, hallucinations, and schema violations in the EIRA system.

All data flow through the system must pass through appropriate guardrail layers:

```
User Input
    ↓
[Input Validation] ← sanitize, normalize, whitelist
    ↓
[AXIOM Layer] ← SQL query validation & safety
    ↓
Database/Vector Store Execution
    ↓
[SENTINEL Layer] ← Output validation & grounding
    ↓
User Response
```

---

## Module Structure

### 1. **sql_safety.py** — AXIOM Layer

Comprehensive SQL injection and query safety validation.

**Covered Attack Vectors:**

- ✅ Dangerous SQL keywords (DROP, DELETE, INSERT, etc.)
- ✅ SQL comments (`--`, `/* */`, `#`)
- ✅ UNION-based injection
- ✅ Stacked queries (`;` statement chaining)
- ✅ Time-based blind injection (SLEEP, BENCHMARK)
- ✅ Boolean-based blind injection (`OR 1=1`)
- ✅ Stored procedure invocation (`xp_`, `sp_`)
- ✅ Hex encoding evasion (`0x...`)

**Key Functions:**

```python
validate_sql_query(sql_string, expected_type)
    → ValidationResult(is_valid, is_blocked, issues, safe_to_execute)

sanitize_column_name(column_name)
    → Optional[str]  # Returns None if not in whitelist

validate_filter_value(column_name, value, operator)
    → (is_valid, error_message)

get_safe_query_string(query_obj, include_values)
    → str  # Safe for audit logging
```

**Whitelist-Based Validation:**

- **Allowed Columns**: `employee_id`, `name`, `age`, `department`, `office_location`
- **Allowed Operators**: `=`, `!=`, `<`, `>`, `<=`, `>=`, `LIKE`, `ILIKE`, `IN`, `NOT IN`, `BETWEEN`, `IS NULL`, `IS NOT NULL`
- **Max Query Length**: 5000 characters

**Usage:**

```python
from guardrails import validate_sql_query

result = validate_sql_query("SELECT * FROM employees WHERE age > 30")
assert result.is_blocked  # SELECT * not allowed
assert not result.safe_to_execute
print(result.issues)  # ["SELECT * not allowed; specify columns explicitly"]
```

---

### 2. **input_validation.py** — Request Sanitization

Validates and sanitizes all user-provided input before processing.

**Covered Threats:**

- ✅ XSS attacks (HTML/XML/script tag injection)
- ✅ Unicode homograph attacks (normalized with NFKC)
- ✅ Control character injection
- ✅ SQL keyword injection in name/filter fields
- ✅ Location validation against canonical cities
- ✅ Department enumeration validation
- ✅ Age range validation (22–65)
- ✅ Batch request size limits

**Key Functions:**

```python
sanitize_input_string(value, max_length, allow_special_chars)
    → (sanitized_string, list[warnings])

validate_location_against_canonical(location, fuzzy_match)
    → (is_valid, canonical_location, confidence_score)

validate_department(department)
    → (is_valid, error_message)

validate_age_range(age_min, age_max)
    → (is_valid, list[errors])

validate_chroma_filter(filter_dict)
    → (is_valid, list[errors])

validate_batch_size(batch_items, max_size)
    → (is_valid, error_message)
```

**Unicode Normalization:**

All strings are normalized using NFKC to prevent:
- Homograph attacks (visually similar characters)
- Encoding evasion attempts
- Bypassing character restrictions

**Usage:**

```python
from guardrails import sanitize_input_string, validate_location_against_canonical

# Sanitize user input
clean_name, warnings = sanitize_input_string("John<script>alert()</script> Doe")
print(clean_name)  # "JohnDoe" (tags removed)

# Validate location (with fuzzy matching)
is_valid, canonical, confidence = validate_location_against_canonical("NYC", fuzzy_match=True)
assert is_valid
assert canonical == "New York, NY"
assert confidence > 0.75
```

---

### 3. **output_validation.py** — SENTINEL Layer

Validates system-generated responses to enforce the **zero-hallucination policy**: all claims must be grounded in retrieved data.

**Validation Checks:**

- ✅ All response claims are backed by sources
- ✅ Citations are properly formatted and referenced
- ✅ Confidence scores are valid (0.0–1.0)
- ✅ Data freshness (weather ≤6h, news ≤24h)
- ✅ Response format compliance
- ✅ No ungrounded claims

**Key Functions:**

```python
validate_response_grounding(response, sources, min_confidence)
    → GroundednessReport(confidence, ungrounded_claims, passes)

check_data_freshness(fetched_at, data_type, max_age_hours)
    → (is_fresh, reason_if_stale, hours_old)

validate_citations(citations, require_all_grounded)
    → (is_valid, list[errors])

validate_response_format(response)
    → (is_valid, list[errors])
```

**Zero-Hallucination Policy:**

Every claim in the final response must:
1. Have at least one source citation backing it
2. Reference a specific chunk_id or SQL record
3. Mark `grounded=True` on the citation
4. Meet the confidence threshold (≥ 0.75 by default)

**Usage:**

```python
from guardrails import validate_response_grounding, check_data_freshness

# Validate grounding
report = validate_response_grounding(
    response=eira_response,
    sources=retrieved_chunks,
    min_confidence=0.75
)

if not report.passes:
    print(f"Ungrounded claims: {report.ungrounded_claims}")
    # Trigger HITL: stale data, ambiguous match, low confidence

# Check data freshness
is_fresh, reason, hours_old = check_data_freshness(
    fetched_at=datetime.now(),
    data_type="weather",
    max_age_hours=6
)

if not is_fresh:
    print(f"Stale data: {reason}")
```

---

### 4. **schema_enforcement.py** — Contract Validation

Enforces the system data contracts to maintain consistency across SQL and Chroma domains.

**Canonical Cities Contract:**

The 10 canonical cities are the single source of truth:

```python
from config.constants import CANONICAL_CITIES

CANONICAL_CITIES = [
    "Austin, TX",
    "Seattle, WA",
    "New York, NY",
    "Chicago, IL",
    "Denver, CO",
    "Boston, MA",
    "Atlanta, GA",
    "Miami, FL",
    "London, UK",
    "Toronto, CA",
]
```

This list MUST be consistent across:
- Employee table (`office_location` column)
- Chroma weather metadata (`location_normalized` field)
- KIRA location resolution service

**Key Functions:**

```python
enforce_canonical_cities(location, context)
    → (is_valid, error_message)

enforce_department_contract(department, context)
    → (is_valid, error_message)

enforce_age_range(age, min_age=22, max_age=65, context)
    → (is_valid, error_message)

enforce_embedding_dims(embedding, expected_dims=384, context)
    → (is_valid, error_message)  # Detects model swaps

validate_metadata_contract(metadata, collection_type)
    → (is_valid, list[errors])

validate_data_consistency(sql_locations, chroma_locations)
    → (is_consistent, list[inconsistencies])
```

**Metadata Contract:**

**Weather Collection:**
```python
{
    "location_normalized": "Austin, TX",  # Must be canonical
    "fetched_at": "2026-06-19T10:30:00Z",
    "conditions": "Sunny, 28°C",
    "temp_c": 28.5,
}
```

**News Collection:**
```python
{
    "topic": "technology",  # Must be in NEWS_TOPICS
    "source": "Reuters",
    "fetched_at": "2026-06-19T10:30:00Z",
    "region": "North America",  # Optional
}
```

**Usage:**

```python
from guardrails import (
    enforce_canonical_cities,
    enforce_embedding_dims,
    validate_data_consistency,
)

# Validate location
is_valid, error = enforce_canonical_cities("Austin, TX", context="employee_insert")
assert is_valid

# Detect embedding model swap
is_valid, error = enforce_embedding_dims(embedding_vector, expected_dims=384)
if not is_valid:
    print(f"CRITICAL: {error}")  # Model swap detected!

# Check SQL ↔ Chroma consistency
sql_locs = {"Austin, TX", "New York, NY"}
chroma_locs = {"Austin, TX", "New York, NY", "Paris, FR"}  # Invalid!

is_consistent, issues = validate_data_consistency(sql_locs, chroma_locs)
print(issues)  # ["Non-canonical cities in Chroma: Paris, FR"]
```

---

### 5. **audit_logger.py** — Compliance Logging

Structured logging for security events, enabling audit trails and compliance reporting.

**Event Types:**

```python
class EventType(str, Enum):
    QUERY_VALIDATED = "query_validated"
    QUERY_BLOCKED = "query_blocked"
    INPUT_SANITIZED = "input_sanitized"
    INJECTION_ATTEMPT = "injection_attempt"
    VALIDATION_FAILED = "validation_failed"
    RESPONSE_GROUNDED = "response_grounded"
    RESPONSE_UNGROUNDED = "response_ungrounded"
    FRESHNESS_CHECK = "freshness_check"
    HITL_TRIGGERED = "hitl_triggered"
    DATA_ACCESS = "data_access"
    ERROR = "error"
```

**Use Module-Level Loggers:**

```python
from guardrails.audit_logger import (
    sql_safety_audit,
    input_validation_audit,
    output_validation_audit,
)

# Log SQL validation
sql_safety_audit.log_query_validation(
    is_valid=False,
    is_blocked=True,
    query_hash="abc123...",
    issues=["Dangerous keyword: DROP"]
)

# Log injection attempt
sql_safety_audit.log_injection_attempt(
    pattern_detected="UNION",
    input_sample="SELECT * FROM employees UNION SELECT ...",
    context="employee_query"
)

# Log response grounding
output_validation_audit.log_response_grounding(
    is_grounded=True,
    confidence=0.87,
    ungrounded_claims=[],
    citation_count=3
)
```

**Audit Log Output (JSON):**

```json
{
  "timestamp": "2026-06-19T10:30:45.123456",
  "event_type": "query_blocked",
  "severity": "warning",
  "module": "sql_safety",
  "query_hash": "abc123...",
  "is_blocked": true,
  "issues": ["Dangerous keyword: DROP"]
}
```

---

## Integration Guide

### Using Guardrails in tools/sql_tools.py

```python
from guardrails import (
    validate_sql_query,
    validate_filter_value,
    get_safe_query_string,
    sql_safety_audit,
)

async def execute_employee_query(
    name: str | None = None,
    department: str | None = None,
    office_location: str | None = None,
) -> dict:
    """Execute parameterized employee query with guardrails"""
    
    # Validate location
    if office_location:
        is_valid, error = validate_filter_value("office_location", office_location)
        if not is_valid:
            sql_safety_audit.log_validation_failure(
                validation_type="office_location",
                errors=[error],
                context="employee_query"
            )
            return {"employees": [], "error": error}
    
    # Validate department
    if department:
        is_valid, error = validate_filter_value("department", department)
        if not is_valid:
            sql_safety_audit.log_validation_failure(
                validation_type="department",
                errors=[error],
                context="employee_query"
            )
            return {"employees": [], "error": error}
    
    # Build query
    with get_db_session() as session:
        query = session.query(Employee)
        
        if name:
            query = query.filter(Employee.name.ilike(f"%{name}%"))
        if department:
            query = query.filter(Employee.department == department)
        if office_location:
            query = query.filter(Employee.office_location == office_location)
        
        rows = query.all()
        
        # Generate audit trail
        query_str = get_safe_query_string(query, include_values=True)
        sql_safety_audit.log_data_access(
            access_type="select",
            resource="employees",
            row_count=len(rows),
            filters_applied={"name": bool(name), "department": bool(department), "location": bool(office_location)}
        )
        
        return {"employees": rows, "query_sql": query_str}
```

### Using Guardrails in app/integration.py

```python
from guardrails import (
    sanitize_input_string,
    validate_response_grounding,
    check_data_freshness,
)

async def run_eira_agent(user_query: str) -> EIRAResponse:
    """EIRA orchestrator with guardrail enforcement"""
    
    # 1. Sanitize input
    clean_query, warnings = sanitize_input_string(user_query, max_length=500)
    if warnings:
        logger.warning(f"Input sanitization warnings: {warnings}")
    
    # 2. Orchestrate agents (VEGA, NOVA, KIRA, AXIOM)
    # ... agent coordination ...
    
    # 3. Validate response (SENTINEL layer)
    grounding_report = validate_response_grounding(
        response=eira_response,
        sources=retrieved_sources,
        min_confidence=0.75
    )
    
    if not grounding_report.passes:
        # Trigger human-in-the-loop approval
        await trigger_hitl_approval(
            trigger_reason="ungrounded_claims",
            ungrounded_claims=grounding_report.ungrounded_claims,
            draft_response=eira_response
        )
    
    # 4. Check data freshness
    for source in retrieved_sources:
        is_fresh, reason, hours_old = check_data_freshness(
            fetched_at=source.fetched_at,
            data_type="weather" if "weather" in source.collection else "news"
        )
        if not is_fresh:
            logger.warning(f"Stale data detected: {reason}")
    
    return eira_response
```

---

## Testing Guardrails

**Example test cases:**

```python
import pytest
from guardrails import validate_sql_query, sanitize_input_string

def test_sql_injection_union():
    """Test UNION injection detection"""
    result = validate_sql_query(
        "SELECT name FROM employees UNION SELECT password FROM users"
    )
    assert result.is_blocked
    assert "UNION" in " ".join(result.issues)

def test_sql_injection_comment():
    """Test SQL comment injection"""
    result = validate_sql_query("SELECT * FROM employees -- DROP TABLE")
    assert result.is_blocked
    assert any("comment" in issue.lower() for issue in result.issues)

def test_xss_sanitization():
    """Test XSS removal"""
    clean, warnings = sanitize_input_string(
        "Alice <script>alert('xss')</script> Bob"
    )
    assert "<script>" not in clean
    assert "HTML/XML tags" in " ".join(warnings)

def test_canonical_city_validation():
    """Test city validation"""
    is_valid, canonical, conf = validate_location_against_canonical(
        "NYC", fuzzy_match=True
    )
    assert is_valid
    assert canonical == "New York, NY"
```

---

## Best Practices

1. **Always sanitize user input** - Call `sanitize_input_string()` first
2. **Never skip SQL validation** - Always call `validate_sql_query()` before execution
3. **Validate all responses** - SENTINEL layer must validate groundedness
4. **Check data freshness** - Prevent stale information from being presented
5. **Log security events** - Enable audit trails for compliance
6. **Enforce contracts** - Use schema enforcement at boundaries
7. **Fail safely** - Block suspicious requests rather than allowing them
8. **Review audit logs** - Periodically review for attack patterns

---

## References

- **CLAUDE.md** - System architecture and high-level design
- **config/constants.py** - Canonical cities, departments, thresholds
- **models/pydantic_io.py** - Data validation schemas
- OWASP SQL Injection: https://owasp.org/www-community/attacks/SQL_Injection
- OWASP Input Validation: https://owasp.org/www-community/attacks/xss/
