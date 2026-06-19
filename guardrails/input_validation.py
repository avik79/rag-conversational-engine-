"""
Input Validation Guardrails

Sanitizes and validates all user inputs before processing:
  - String sanitization (XSS, Unicode normalization)
  - Location validation against canonical cities
  - Department whitelist validation
  - Age range enforcement
  - Chroma filter validation
  - Request size limits
"""

import re
import unicodedata
from typing import Any, Optional
from config.constants import CANONICAL_CITIES, DEPARTMENTS
import logging

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────
# Constants
# ────────────────────────────────────────────────────────────────────────

MAX_STRING_LENGTH = 500
MAX_QUERY_LENGTH = 2000
MAX_BATCH_SIZE = 100
MIN_AGE = 22
MAX_AGE = 65

# Characters allowed in free-text queries (name searches, etc.)
# Whitelist approach: only allow alphanumeric, spaces, common punctuation
SAFE_TEXT_PATTERN = re.compile(r"^[a-zA-Z0-9\s\-'.,]*$")

# SQL filter context—stricter than general text
SAFE_FILTER_PATTERN = re.compile(r"^[a-zA-Z0-9\s\-]*$")


def sanitize_input_string(
    value: str,
    max_length: int = MAX_STRING_LENGTH,
    allow_special_chars: bool = False,
) -> tuple[str, list[str]]:
    """
    Sanitize user input string.

    Args:
        value: Input string to sanitize
        max_length: Maximum allowed length
        allow_special_chars: If True, allow more characters (for general text)

    Returns:
        (sanitized_string, list_of_warnings)
    """
    warnings = []

    if not isinstance(value, str):
        return "", ["Input must be a string"]

    # ────────────────────────────────────────────────────────────────────
    # 1. Normalize Unicode
    # ────────────────────────────────────────────────────────────────────
    # Prevents homograph attacks and ensures consistent comparison
    normalized = unicodedata.normalize("NFKC", value)

    # ────────────────────────────────────────────────────────────────────
    # 2. Strip Whitespace
    # ────────────────────────────────────────────────────────────────────
    normalized = normalized.strip()

    # ────────────────────────────────────────────────────────────────────
    # 3. Check Length
    # ────────────────────────────────────────────────────────────────────
    if len(normalized) > max_length:
        warnings.append(f"Input truncated from {len(normalized)} to {max_length} chars")
        normalized = normalized[:max_length]

    # ────────────────────────────────────────────────────────────────────
    # 4. Check for Dangerous Patterns
    # ────────────────────────────────────────────────────────────────────

    # HTML/Script tags
    if re.search(r"<[^>]+>", normalized):
        warnings.append("HTML/XML tags detected and removed")
        normalized = re.sub(r"<[^>]+>", "", normalized)

    # SQL keywords in suspicious context
    suspicious_sql = re.search(
        r"\b(UNION|SELECT|DROP|INSERT|DELETE|UPDATE|EXEC|SCRIPT)\b",
        normalized,
        re.IGNORECASE
    )
    if suspicious_sql:
        warnings.append(f"Suspicious SQL keyword detected: {suspicious_sql.group()}")

    # Control characters (except newline/tab in general text)
    control_chars = [c for c in normalized if ord(c) < 32 and c not in '\n\t']
    if control_chars:
        warnings.append(f"Control characters removed: {len(control_chars)} chars")
        normalized = "".join(c for c in normalized if ord(c) >= 32 or c in '\n\t')

    # ────────────────────────────────────────────────────────────────────
    # 5. Character Whitelist (Optional)
    # ────────────────────────────────────────────────────────────────────
    if not allow_special_chars:
        if not SAFE_TEXT_PATTERN.match(normalized):
            warnings.append("Special characters detected (filtered)")
            # Keep only safe characters
            normalized = re.sub(r"[^a-zA-Z0-9\s\-'.,]", "", normalized)

    logger.debug(
        "Input sanitized",
        extra={
            "original_len": len(value),
            "sanitized_len": len(normalized),
            "warnings": len(warnings),
        }
    )

    return normalized, warnings


def validate_location_against_canonical(
    location: str,
    fuzzy_match: bool = False,
) -> tuple[bool, Optional[str], float]:
    """
    Validate location against canonical cities.

    Args:
        location: Location string to validate
        fuzzy_match: If True, allow similar matches (e.g., "NYC" → "New York, NY")

    Returns:
        (is_valid, canonical_location, confidence_score)
    """
    location_clean = location.strip()

    # ────────────────────────────────────────────────────────────────────
    # 1. Exact Match
    # ────────────────────────────────────────────────────────────────────
    if location_clean in CANONICAL_CITIES:
        return True, location_clean, 1.0

    # ────────────────────────────────────────────────────────────────────
    # 2. Case-Insensitive Match
    # ────────────────────────────────────────────────────────────────────
    location_lower = location_clean.lower()
    for canonical in CANONICAL_CITIES:
        if canonical.lower() == location_lower:
            return True, canonical, 1.0

    # ────────────────────────────────────────────────────────────────────
    # 3. Abbreviation Resolution (Optional Fuzzy)
    # ────────────────────────────────────────────────────────────────────
    if fuzzy_match:
        abbrev_map = {
            "nyc": "New York, NY",
            "ny": "New York, NY",
            "la": "Chicago, IL",  # Note: not LA, we don't have it
            "sf": "Seattle, WA",  # Note: not SF
            "dc": "Boston, MA",
            "boston": "Boston, MA",
            "denver": "Denver, CO",
            "seattle": "Seattle, WA",
            "austin": "Austin, TX",
            "miami": "Miami, FL",
            "atlanta": "Atlanta, GA",
            "chicago": "Chicago, IL",
            "london": "London, UK",
            "toronto": "Toronto, CA",
        }

        normalized = location_clean.replace(",", "").lower().strip()

        matching_canonical = None
        for abbrev, canonical in abbrev_map.items():
            if normalized.startswith(abbrev):
                confidence = min(1.0, len(abbrev) / len(normalized))
                if confidence >= 0.75:
                    matching_canonical = canonical
                    return True, canonical, confidence

    logger.warning(f"Location validation failed: {location}")
    return False, None, 0.0


def validate_department(department: str) -> tuple[bool, Optional[str]]:
    """
    Validate department against allowed list.

    Returns:
        (is_valid, error_message)
    """
    department_clean = department.strip()

    if department_clean in DEPARTMENTS:
        return True, None

    # Case-insensitive match
    for dept in DEPARTMENTS:
        if dept.lower() == department_clean.lower():
            return True, None

    valid_depts = ", ".join(DEPARTMENTS)
    error = f"Invalid department. Must be one of: {valid_depts}"
    logger.warning(f"Department validation failed: {department}")

    return False, error


def validate_age_range(
    age_min: Optional[int] = None,
    age_max: Optional[int] = None,
) -> tuple[bool, list[str]]:
    """
    Validate age range parameters.

    Returns:
        (is_valid, list_of_errors)
    """
    errors = []

    if age_min is not None:
        try:
            age_min_int = int(age_min)
            if age_min_int < MIN_AGE:
                errors.append(f"age_min must be >= {MIN_AGE}")
            if age_min_int > MAX_AGE:
                errors.append(f"age_min must be <= {MAX_AGE}")
        except (ValueError, TypeError):
            errors.append("age_min must be an integer")

    if age_max is not None:
        try:
            age_max_int = int(age_max)
            if age_max_int < MIN_AGE:
                errors.append(f"age_max must be >= {MIN_AGE}")
            if age_max_int > MAX_AGE:
                errors.append(f"age_max must be <= {MAX_AGE}")
        except (ValueError, TypeError):
            errors.append("age_max must be an integer")

    if age_min is not None and age_max is not None:
        try:
            if int(age_min) > int(age_max):
                errors.append("age_min must be <= age_max")
        except (ValueError, TypeError):
            pass  # Already caught above

    return len(errors) == 0, errors


def validate_chroma_filter(
    filter_dict: dict[str, Any],
) -> tuple[bool, list[str]]:
    """
    Validate Chroma vector store filter dictionary.

    Chroma filters must conform to expected metadata fields and operators.

    Args:
        filter_dict: Filter dictionary to validate

    Returns:
        (is_valid, list_of_errors)
    """
    errors = []

    if not isinstance(filter_dict, dict):
        return False, ["Filter must be a dictionary"]

    # ────────────────────────────────────────────────────────────────────
    # 1. Check for Nested Injection Attempts
    # ────────────────────────────────────────────────────────────────────
    allowed_operators = {"$eq", "$ne", "$gt", "$gte", "$lt", "$lte", "$in", "$nin"}
    for key, value in filter_dict.items():
        if isinstance(value, dict):
            for op in value.keys():
                if op not in allowed_operators:
                    errors.append(f"Operator not allowed: {op}")

    # ────────────────────────────────────────────────────────────────────
    # 2. Validate Expected Metadata Fields
    # ────────────────────────────────────────────────────────────────────
    allowed_fields = {
        "location_normalized",  # Weather only
        "fetched_at",
        "topic",
        "source",
        "region",
    }

    for key in filter_dict.keys():
        if key not in allowed_fields:
            errors.append(f"Field not allowed in filter: {key}")

    # ────────────────────────────────────────────────────────────────────
    # 3. Validate field values
    # ────────────────────────────────────────────────────────────────────
    if "location_normalized" in filter_dict:
        loc_filter = filter_dict["location_normalized"]
        if isinstance(loc_filter, dict):
            if "$eq" in loc_filter:
                loc_value = loc_filter["$eq"]
                if loc_value not in CANONICAL_CITIES:
                    errors.append(f"location_normalized must be a canonical city")
        elif isinstance(loc_filter, str):
            if loc_filter not in CANONICAL_CITIES:
                errors.append(f"location_normalized must be a canonical city")

    logger.debug(
        "Chroma filter validated",
        extra={"is_valid": len(errors) == 0, "error_count": len(errors)}
    )

    return len(errors) == 0, errors


def validate_batch_size(batch_items: list[Any], max_size: int = MAX_BATCH_SIZE) -> tuple[bool, Optional[str]]:
    """
    Validate batch request size.

    Returns:
        (is_valid, error_message)
    """
    if not isinstance(batch_items, list):
        return False, "Batch must be a list"

    if len(batch_items) > max_size:
        return False, f"Batch size exceeds maximum ({max_size})"

    if len(batch_items) == 0:
        return False, "Batch cannot be empty"

    return True, None
