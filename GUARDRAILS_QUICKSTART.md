# Guardrails Quick Start

Add security to your EIRA system in 5 minutes.

---

## Installation

Guardrails are already implemented in `guardrails/` module. No external dependencies needed — uses only stdlib + existing project dependencies.

```python
from guardrails import (
    validate_sql_query,
    sanitize_input_string,
    validate_response_grounding,
    enforce_canonical_cities,
)
```

---

## 5 Quick Integration Points

### 1. Protect SQL Queries (tools/sql_tools.py)

**Before:**
```python
async def execute_employee_query(name: str | None = None, ...) -> dict:
    with get_db_session() as session:
        query = session.query(Employee)
        if name:
            query = query.filter(Employee.name.ilike(f"%{name}%"))
        rows = query.all()
        return {"employees": rows}
```

**After:**
```python
from guardrails import validate_filter_value

async def execute_employee_query(name: str | None = None, ...) -> dict:
    # NEW: Validate filter value
    if name:
        is_valid, error = validate_filter_value("name", name)
        if not is_valid:
            return {"employees": [], "error": error}
    
    with get_db_session() as session:
        query = session.query(Employee)
        if name:
            query = query.filter(Employee.name.ilike(f"%{name}%"))
        rows = query.all()
        return {"employees": rows}
```

---

### 2. Sanitize User Input (app/integration.py)

**Before:**
```python
async def run_eira_agent(user_query: str) -> EIRAResponse:
    # Process directly
    intent = await classify_intent(user_query)
    ...
```

**After:**
```python
from guardrails import sanitize_input_string

async def run_eira_agent(user_query: str) -> EIRAResponse:
    # NEW: Sanitize input first
    clean_query, warnings = sanitize_input_string(user_query, max_length=500)
    if warnings:
        logger.warning(f"Input warnings: {warnings}")
    
    intent = await classify_intent(clean_query)
    ...
```

---

### 3. Validate Responses (app/integration.py)

**Before:**
```python
async def run_eira_agent(user_query: str) -> EIRAResponse:
    # ... coordinate agents ...
    return eira_response  # Return without validation
```

**After:**
```python
from guardrails import validate_response_grounding

async def run_eira_agent(user_query: str) -> EIRAResponse:
    # ... coordinate agents ...
    
    # NEW: Validate response grounding (SENTINEL)
    grounding_report = validate_response_grounding(
        response=eira_response,
        sources=retrieved_sources,
        min_confidence=0.75
    )
    
    if not grounding_report.passes:
        logger.warning(f"Ungrounded claims: {grounding_report.ungrounded_claims}")
        # Trigger human approval
        await trigger_hitl_approval(
            trigger_reason="ungrounded_claims",
            ungrounded_claims=grounding_report.ungrounded_claims
        )
    
    return eira_response
```

---

### 4. Validate Locations (tools/chroma_tools.py or app/integration.py)

**Before:**
```python
# KIRA location resolution
canonical_location = map_user_location(user_input)
results = chroma_client.query(collection_name="weather", where={
    "location_normalized": canonical_location
})
```

**After:**
```python
from guardrails import validate_location_against_canonical

# KIRA location resolution
is_valid, canonical_location, confidence = validate_location_against_canonical(
    user_input,
    fuzzy_match=True
)

if not is_valid or confidence < 0.80:
    # Trigger HITL or ask user to clarify
    return {"error": "Location ambiguous, please clarify"}

results = chroma_client.query(collection_name="weather", where={
    "location_normalized": canonical_location
})
```

---

### 5. Log Security Events (anywhere)

**Add audit logging:**

```python
from guardrails.audit_logger import sql_safety_audit, input_validation_audit, EventType, Severity

# After validating a query
sql_safety_audit.log_query_validation(
    is_valid=result.is_valid,
    is_blocked=result.is_blocked,
    query_hash=hash(user_query),
    issues=result.issues
)

# Log input sanitization
input_validation_audit.log_input_sanitization(
    original_length=len(user_input),
    sanitized_length=len(clean_input),
    warnings=warnings
)

# Log injection attempt (critical)
sql_safety_audit.log_injection_attempt(
    pattern_detected="UNION",
    input_sample=user_query[:100],
    context="employee_query"
)
```

---

## Common Usage Patterns

### Pattern 1: Block SQL Injection
```python
from guardrails import validate_sql_query

result = validate_sql_query(user_query)
if result.is_blocked:
    print(f"Query blocked: {result.issues}")
    return {"error": "Invalid query"}
```

### Pattern 2: Sanitize & Validate
```python
from guardrails import sanitize_input_string, validate_location_against_canonical

# Clean input
clean, warnings = sanitize_input_string(raw_input)

# Validate against whitelist
is_valid, canonical, conf = validate_location_against_canonical(clean, fuzzy_match=True)

if not is_valid:
    return {"error": "Invalid location"}
```

### Pattern 3: Enforce Schema Contract
```python
from guardrails import (
    enforce_canonical_cities,
    enforce_department_contract,
    enforce_age_range,
)

# At pre-execution validation (AXIOM)
is_valid, error = enforce_canonical_cities(location, context="employee_insert")
is_valid, error = enforce_department_contract(dept, context="employee_insert")
is_valid, error = enforce_age_range(age, context="employee_insert")
```

### Pattern 4: Zero-Hallucination (SENTINEL)
```python
from guardrails import validate_response_grounding, check_data_freshness

# Check response grounding
report = validate_response_grounding(response, sources, min_confidence=0.75)
if not report.passes:
    print(f"Ungrounded: {report.ungrounded_claims}")
    # Require human approval

# Check data freshness
is_fresh, reason, hours_old = check_data_freshness(
    fetched_at=chunk.fetched_at,
    data_type="weather",
    max_age_hours=6
)
if not is_fresh:
    print(f"Stale data: {reason}")
```

### Pattern 5: Chroma Filter Validation
```python
from guardrails import validate_chroma_filter

user_filter = {"location_normalized": "Austin, TX"}

is_valid, errors = validate_chroma_filter(user_filter)
if not is_valid:
    print(f"Invalid filter: {errors}")
    return {"error": "Invalid filter"}

# Now safe to use
results = chroma_client.query(where=user_filter)
```

---

## One-Liner Safety Checks

**Block dangerous queries:**
```python
result = validate_sql_query(q)
if result.is_blocked: return {"error": "blocked"}
```

**Sanitize user input:**
```python
clean, _ = sanitize_input_string(user_input, max_length=500)
```

**Validate location:**
```python
is_valid, canonical, _ = validate_location_against_canonical(loc, fuzzy_match=True)
```

**Check response grounding:**
```python
report = validate_response_grounding(resp, sources, 0.75)
if not report.passes: trigger_hitl()
```

**Log security event:**
```python
sql_safety_audit.log_query_validation(result.is_valid, result.is_blocked, hash(q), result.issues)
```

---

## Testing Your Guardrails

```python
import pytest
from guardrails import validate_sql_query, sanitize_input_string

def test_sql_injection_blocked():
    """Verify UNION injection is blocked"""
    result = validate_sql_query("SELECT * FROM employees UNION SELECT password FROM users")
    assert result.is_blocked
    assert any("UNION" in issue for issue in result.issues)

def test_xss_sanitized():
    """Verify XSS tags are removed"""
    clean, warnings = sanitize_input_string("John<script>alert()</script>")
    assert "<script>" not in clean
    assert any("HTML" in w for w in warnings)

def test_canonical_city_exact():
    """Verify exact city matching"""
    is_valid, canonical, conf = validate_location_against_canonical("Austin, TX")
    assert is_valid
    assert canonical == "Austin, TX"
    assert conf == 1.0

def test_canonical_city_fuzzy():
    """Verify fuzzy city matching"""
    is_valid, canonical, conf = validate_location_against_canonical("NYC", fuzzy_match=True)
    assert is_valid
    assert canonical == "New York, NY"
    assert conf >= 0.75
```

---

## Full Example: Secure Employee Query

```python
from guardrails import (
    sanitize_input_string,
    validate_location_against_canonical,
    validate_department,
    validate_age_range,
    sql_safety_audit,
)

async def secure_employee_query(
    name: str | None = None,
    department: str | None = None,
    location: str | None = None,
    age_min: int | None = None,
    age_max: int | None = None,
) -> dict:
    """Execute employee query with full guardrail protection"""
    
    # 1. Sanitize name input
    if name:
        clean_name, warns = sanitize_input_string(name)
        if warns:
            logger.warning(f"Name sanitization: {warns}")
        name = clean_name
    
    # 2. Validate location
    if location:
        is_valid, canonical, conf = validate_location_against_canonical(
            location,
            fuzzy_match=True
        )
        if not is_valid or conf < 0.80:
            return {
                "error": "Location ambiguous",
                "message": f"Could not resolve location: {location}"
            }
        location = canonical
    
    # 3. Validate department
    if department:
        is_valid, error = validate_department(department)
        if not is_valid:
            return {"error": error}
    
    # 4. Validate age range
    if age_min is not None or age_max is not None:
        is_valid, errors = validate_age_range(age_min, age_max)
        if not is_valid:
            return {"errors": errors}
    
    # 5. Execute query
    try:
        with get_db_session() as session:
            query = session.query(Employee)
            if name:
                query = query.filter(Employee.name.ilike(f"%{name}%"))
            if department:
                query = query.filter(Employee.department == department)
            if location:
                query = query.filter(Employee.office_location == location)
            if age_min is not None:
                query = query.filter(Employee.age >= age_min)
            if age_max is not None:
                query = query.filter(Employee.age <= age_max)
            
            rows = query.all()
            
            # 6. Log data access
            sql_safety_audit.log_data_access(
                access_type="select",
                resource="employees",
                row_count=len(rows),
                filters_applied={
                    "name": bool(name),
                    "department": bool(department),
                    "location": bool(location),
                    "age_range": bool(age_min or age_max),
                }
            )
            
            return {
                "employees": [r.to_dict() for r in rows],
                "row_count": len(rows),
                "filters_applied": {
                    "name": name or None,
                    "department": department or None,
                    "location": location or None,
                    "age_min": age_min,
                    "age_max": age_max,
                }
            }
    
    except Exception as e:
        sql_safety_audit.log_error(
            error_message=str(e),
            error_type=type(e).__name__,
            context="employee_query"
        )
        return {"error": "Query failed", "details": str(e)}
```

---

## Next Steps

1. ✅ Read `guardrails/GUARDRAILS.md` for comprehensive docs
2. ✅ Add guardrail imports to `tools/sql_tools.py`
3. ✅ Add guardrail imports to `app/integration.py`
4. ✅ Add audit logging throughout
5. ✅ Write test suite in `tests/guardrails/`
6. ✅ Run periodic consistency checks

---

## Questions?

Refer to:
- **guardrails/GUARDRAILS.md** — Module reference & design decisions
- **GUARDRAILS_IMPLEMENTATION.md** — Implementation details & covered threats
- **CLAUDE.md** — System architecture & integration notes
