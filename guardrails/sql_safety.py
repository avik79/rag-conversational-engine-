"""
SQL Safety Guardrails — AXIOM Layer

Prevents SQL injection, unauthorized queries, and database abuse through:
  - Pattern-based detection of malicious SQL
  - Parameterized query enforcement
  - Column/value whitelisting
  - Query intent validation
  - Audit trail generation

ALL SQL queries executed via tools/sql_tools.py MUST pass through this module.
"""

import re
from typing import Any, Optional
from enum import Enum
from config.constants import CANONICAL_CITIES, DEPARTMENTS
from models.pydantic_io import ValidationResult
import logging

logger = logging.getLogger(__name__)


class QueryType(str, Enum):
    """Allowed query types"""
    SELECT_EMPLOYEES = "select_employees"
    AGGREGATE = "aggregate"
    METADATA = "metadata"
    DENIED = "denied"


# ────────────────────────────────────────────────────────────────────────
# SQL Injection Patterns
# ────────────────────────────────────────────────────────────────────────

# Dangerous SQL keywords that should NEVER appear in user-influenced queries
DANGEROUS_KEYWORDS = {
    "DROP",
    "DELETE",
    "TRUNCATE",
    "ALTER",
    "CREATE",
    "REPLACE",
    "INSERT",
    "UPDATE",
    "EXEC",
    "EXECUTE",
    "SCRIPT",
}

# SQL comment patterns (potential injection vectors)
COMMENT_PATTERNS = [
    r"--\s",      # SQL line comment
    r"/\*",       # SQL block comment start
    r"\*/",       # SQL block comment end
    r"#",         # MySQL comment
]

# Union-based injection attempts
UNION_PATTERN = re.compile(r"\bUNION\b", re.IGNORECASE)

# Stacked queries (multiple statements)
STACKED_QUERY_PATTERN = re.compile(r";\s*\w+", re.IGNORECASE)

# Time-based blind injection attempts
SLEEP_PATTERN = re.compile(r"\b(SLEEP|BENCHMARK|WAITFOR)\s*\(", re.IGNORECASE)

# Boolean-based blind injection
BOOLEAN_INJECTION = re.compile(r"(OR|AND)\s*(1\s*=\s*1|0\s*=\s*0|TRUE|FALSE)", re.IGNORECASE)

# Stored procedure invocation
SPROC_PATTERN = re.compile(r"\b(xp_|sp_|sys\.|msdb\.)", re.IGNORECASE)

# Hex encoding evasion
HEX_PATTERN = re.compile(r"0x[0-9a-fA-F]+")

# Allowed column names for SELECT queries
ALLOWED_COLUMNS = {
    "employee_id",
    "name",
    "age",
    "department",
    "office_location",
}

# Allowed operators for WHERE clauses
ALLOWED_OPERATORS = {
    "=",
    "!=",
    "<",
    ">",
    "<=",
    ">=",
    "LIKE",
    "ILIKE",
    "IN",
    "NOT IN",
    "BETWEEN",
    "IS NULL",
    "IS NOT NULL",
}


def validate_sql_query(
    sql_string: str,
    expected_type: QueryType = QueryType.SELECT_EMPLOYEES,
) -> ValidationResult:
    """
    Comprehensive SQL injection & safety validation.

    Args:
        sql_string: SQL query string to validate
        expected_type: Expected query type (select_employees, aggregate, metadata)

    Returns:
        ValidationResult with is_valid, is_blocked, issues list, and safe_to_execute flags
    """
    issues = []
    is_blocked = False

    if not sql_string or not isinstance(sql_string, str):
        return ValidationResult(
            is_valid=False,
            is_blocked=True,
            issues=["Query must be a non-empty string"],
            safe_to_execute=False,
            query_type="sql",
        )

    sql_upper = sql_string.upper()

    # ────────────────────────────────────────────────────────────────────
    # 1. Dangerous Keywords Check
    # ────────────────────────────────────────────────────────────────────
    for keyword in DANGEROUS_KEYWORDS:
        if re.search(rf"\b{keyword}\b", sql_upper):
            issues.append(f"Dangerous operation detected: {keyword}")
            is_blocked = True

    # ────────────────────────────────────────────────────────────────────
    # 2. Comment Injection Check
    # ────────────────────────────────────────────────────────────────────
    for pattern in COMMENT_PATTERNS:
        if re.search(pattern, sql_string):
            issues.append(f"SQL comment detected (injection vector): {pattern}")
            is_blocked = True

    # ────────────────────────────────────────────────────────────────────
    # 3. Union-Based Injection Check
    # ────────────────────────────────────────────────────────────────────
    if UNION_PATTERN.search(sql_string):
        issues.append("UNION keyword detected (union-based injection attempt)")
        is_blocked = True

    # ────────────────────────────────────────────────────────────────────
    # 4. Stacked Queries Check
    # ────────────────────────────────────────────────────────────────────
    if STACKED_QUERY_PATTERN.search(sql_string):
        issues.append("Multiple statements detected (stacked query injection)")
        is_blocked = True

    # ────────────────────────────────────────────────────────────────────
    # 5. Time-Based Blind Injection Check
    # ────────────────────────────────────────────────────────────────────
    if SLEEP_PATTERN.search(sql_string):
        issues.append("Time-based injection pattern detected (SLEEP/BENCHMARK)")
        is_blocked = True

    # ────────────────────────────────────────────────────────────────────
    # 6. Boolean-Based Injection Check
    # ────────────────────────────────────────────────────────────────────
    if BOOLEAN_INJECTION.search(sql_string):
        issues.append("Boolean-based injection pattern detected")
        is_blocked = True

    # ────────────────────────────────────────────────────────────────────
    # 7. Stored Procedure Invocation Check
    # ────────────────────────────────────────────────────────────────────
    if SPROC_PATTERN.search(sql_string):
        issues.append("Stored procedure/system call detected")
        is_blocked = True

    # ────────────────────────────────────────────────────────────────────
    # 8. Hex Encoding Evasion Check
    # ────────────────────────────────────────────────────────────────────
    if HEX_PATTERN.search(sql_string):
        issues.append("Hex-encoded values detected (potential obfuscation)")
        is_blocked = True

    # ────────────────────────────────────────────────────────────────────
    # 9. SELECT * Check
    # ────────────────────────────────────────────────────────────────────
    if "SELECT *" in sql_upper:
        issues.append("SELECT * not allowed; specify columns explicitly")

    # ────────────────────────────────────────────────────────────────────
    # 10. Query Length Sanity Check
    # ────────────────────────────────────────────────────────────────────
    if len(sql_string) > 5000:
        issues.append("Query exceeds maximum length (5000 chars)")
        is_blocked = True

    logger.info(
        "SQL validation",
        extra={
            "query_hash": hash(sql_string),
            "is_blocked": is_blocked,
            "issue_count": len(issues),
            "query_length": len(sql_string),
        }
    )

    return ValidationResult(
        is_valid=len(issues) == 0,
        is_blocked=is_blocked,
        issues=issues,
        safe_to_execute=not is_blocked and len(issues) == 0,
        query_type="sql",
    )


def sanitize_column_name(column_name: str) -> Optional[str]:
    """
    Whitelist-based column name sanitization.

    Returns None if column is not in allowed set.
    """
    clean_name = column_name.strip().lower()

    if clean_name not in ALLOWED_COLUMNS:
        logger.warning(f"Unauthorized column access attempt: {column_name}")
        return None

    return clean_name


def validate_filter_value(
    column_name: str,
    value: Any,
    operator: str = "=",
) -> tuple[bool, Optional[str]]:
    """
    Validate filter values against column constraints.

    Args:
        column_name: Column to filter on
        value: Value to filter by
        operator: SQL operator (=, <, >, LIKE, etc.)

    Returns:
        (is_valid, error_message)
    """
    if operator.upper() not in ALLOWED_OPERATORS:
        return False, f"Operator not allowed: {operator}"

    column_lower = column_name.lower()

    # ────────────────────────────────────────────────────────────────────
    # Column-Specific Validation
    # ────────────────────────────────────────────────────────────────────

    if column_lower == "office_location":
        # Must be a canonical city
        if isinstance(value, str) and value not in CANONICAL_CITIES:
            return False, f"office_location must be one of: {', '.join(CANONICAL_CITIES)}"

    elif column_lower == "department":
        # Must be a valid department
        if isinstance(value, str) and value not in DEPARTMENTS:
            return False, f"department must be one of: {', '.join(DEPARTMENTS)}"

    elif column_lower == "age":
        # Must be integer in valid range
        try:
            age = int(value) if not isinstance(value, int) else value
            if not (22 <= age <= 65):
                return False, "age must be between 22 and 65"
        except (ValueError, TypeError):
            return False, "age must be an integer"

    elif column_lower == "name":
        # Check for SQL injection patterns in name filter
        if isinstance(value, str):
            if len(value) > 120:
                return False, "name filter exceeds maximum length"
            if any(char in value for char in [";", "'", '"', "--", "/*"]):
                return False, "name filter contains invalid characters"

    elif column_lower == "employee_id":
        # Must be positive integer
        try:
            emp_id = int(value) if not isinstance(value, int) else value
            if emp_id <= 0:
                return False, "employee_id must be positive"
        except (ValueError, TypeError):
            return False, "employee_id must be an integer"

    return True, None


def get_safe_query_string(
    query_obj: Any,
    include_values: bool = False,
) -> str:
    """
    Extract safe query string from SQLAlchemy query object.

    Args:
        query_obj: SQLAlchemy query object
        include_values: If True, compile with literal_binds (shows param values)

    Returns:
        SQL query string safe for logging/audit
    """
    try:
        compile_kwargs = {}
        if include_values:
            compile_kwargs["literal_binds"] = True

        query_str = str(query_obj.statement.compile(**compile_kwargs))

        # Truncate if exceptionally long
        if len(query_str) > 1000:
            query_str = query_str[:1000] + "..."

        return query_str
    except Exception as e:
        logger.error(f"Failed to extract query string: {e}")
        return "[redacted]"
