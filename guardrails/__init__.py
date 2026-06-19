"""
Guardrails Module — Security & Safety Validation

This module provides defense-in-depth guardrails for the EIRA system:

  1. SQL Safety (sql_safety.py)
     - SQL injection pattern detection
     - Parameterized query enforcement
     - Column/value whitelisting
     - Query intent validation

  2. Input Validation (input_validation.py)
     - String sanitization (XSS, Unicode normalization)
     - Location validation against canonical cities
     - Department whitelist validation
     - Age range enforcement
     - Chroma filter validation

  3. Output Validation (output_validation.py) — SENTINEL Layer
     - Response grounding validation (zero-hallucination policy)
     - Data freshness checks
     - Citation accuracy and completeness
     - Response format compliance

  4. Schema Enforcement (schema_enforcement.py)
     - Canonical cities contract (SQL ↔ Chroma)
     - Department enumeration consistency
     - Embedding dimension validation
     - Metadata field consistency
     - Age range enforcement

  5. Audit Logging (audit_logger.py)
     - Structured logging for compliance
     - Security event tracking
     - Data access patterns
     - HITL decision logging

Reference: CLAUDE.md § Zero-Hallucination Policy
"""

# ────────────────────────────────────────────────────────────────────────
# SQL Safety Exports
# ────────────────────────────────────────────────────────────────────────
from guardrails.sql_safety import (
    validate_sql_query,
    sanitize_column_name,
    validate_filter_value,
    get_safe_query_string,
    QueryType,
)

# ────────────────────────────────────────────────────────────────────────
# Input Validation Exports
# ────────────────────────────────────────────────────────────────────────
from guardrails.input_validation import (
    sanitize_input_string,
    validate_location_against_canonical,
    validate_department,
    validate_age_range,
    validate_chroma_filter,
    validate_batch_size,
)

# ────────────────────────────────────────────────────────────────────────
# Output Validation Exports (SENTINEL)
# ────────────────────────────────────────────────────────────────────────
from guardrails.output_validation import (
    validate_response_grounding,
    check_data_freshness,
    validate_citations,
    validate_response_format,
)

# ────────────────────────────────────────────────────────────────────────
# Schema Enforcement Exports
# ────────────────────────────────────────────────────────────────────────
from guardrails.schema_enforcement import (
    enforce_canonical_cities,
    enforce_department_contract,
    enforce_age_range,
    enforce_embedding_dims,
    validate_metadata_contract,
    enforce_name_contract,
    validate_data_consistency,
)

# ────────────────────────────────────────────────────────────────────────
# Audit Logging Exports
# ────────────────────────────────────────────────────────────────────────
from guardrails.audit_logger import (
    AuditLogger,
    EventType,
    Severity,
    sql_safety_audit,
    input_validation_audit,
    output_validation_audit,
    schema_enforcement_audit,
)

__all__ = [
    # SQL Safety
    "validate_sql_query",
    "sanitize_column_name",
    "validate_filter_value",
    "get_safe_query_string",
    "QueryType",
    # Input Validation
    "sanitize_input_string",
    "validate_location_against_canonical",
    "validate_department",
    "validate_age_range",
    "validate_chroma_filter",
    "validate_batch_size",
    # Output Validation (SENTINEL)
    "validate_response_grounding",
    "check_data_freshness",
    "validate_citations",
    "validate_response_format",
    # Schema Enforcement
    "enforce_canonical_cities",
    "enforce_department_contract",
    "enforce_age_range",
    "enforce_embedding_dims",
    "validate_metadata_contract",
    "enforce_name_contract",
    "validate_data_consistency",
    # Auditing
    "AuditLogger",
    "EventType",
    "Severity",
    "sql_safety_audit",
    "input_validation_audit",
    "output_validation_audit",
    "schema_enforcement_audit",
]
