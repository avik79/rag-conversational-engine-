"""
Schema Enforcement Guardrails

Ensures system contracts are maintained across data domains:
  - Canonical cities contract between SQL and Chroma
  - Department enumeration consistency
  - Embedding dimension validation
  - Metadata field consistency (weather vs. news)
  - Age range enforcement
"""

from typing import Optional, Any
from config.constants import (
    CANONICAL_CITIES,
    DEPARTMENTS,
    EMBEDDING_DIMS,
    NEWS_TOPICS,
)
import logging

logger = logging.getLogger(__name__)


def enforce_canonical_cities(
    location: str,
    context: str = "unknown",
) -> tuple[bool, Optional[str]]:
    """
    Enforce that location is a canonical city.

    Used at multiple enforcement points:
      - Employee.office_location (SQL)
      - weather_embeddings metadata.location_normalized (Chroma)
      - User location queries (KIRA)

    Args:
        location: Location string to validate
        context: Where this is being used (for logging)

    Returns:
        (is_valid, error_message)
    """
    location_clean = location.strip() if isinstance(location, str) else None

    if not location_clean:
        error = "Location cannot be empty"
        logger.warning(f"Canonical city enforcement failed in {context}: {error}")
        return False, error

    if location_clean not in CANONICAL_CITIES:
        valid_cities = ", ".join(CANONICAL_CITIES)
        error = f"'{location_clean}' is not a canonical city. Must be one of: {valid_cities}"
        logger.warning(f"Canonical city enforcement failed in {context}: {error}")
        return False, error

    return True, None


def enforce_department_contract(
    department: str,
    context: str = "unknown",
) -> tuple[bool, Optional[str]]:
    """
    Enforce that department is in allowed enumeration.

    Used at:
      - Employee seeding (db/seed.py)
      - Employee queries (VEGA)
      - User requests

    Args:
        department: Department string to validate
        context: Where this is being used (for logging)

    Returns:
        (is_valid, error_message)
    """
    dept_clean = department.strip() if isinstance(department, str) else None

    if not dept_clean:
        error = "Department cannot be empty"
        logger.warning(f"Department contract enforcement failed in {context}: {error}")
        return False, error

    if dept_clean not in DEPARTMENTS:
        valid_depts = ", ".join(DEPARTMENTS)
        error = f"'{dept_clean}' is not a valid department. Must be one of: {valid_depts}"
        logger.warning(f"Department contract enforcement failed in {context}: {error}")
        return False, error

    return True, None


def enforce_age_range(
    age: int,
    min_age: int = 22,
    max_age: int = 65,
    context: str = "unknown",
) -> tuple[bool, Optional[str]]:
    """
    Enforce age is within valid range.

    Used at:
      - Employee seeding (db/seed.py)
      - Employee queries (VEGA)

    Args:
        age: Age value to validate
        min_age: Minimum allowed age
        max_age: Maximum allowed age
        context: Where this is being used (for logging)

    Returns:
        (is_valid, error_message)
    """
    try:
        age_int = int(age)
    except (ValueError, TypeError):
        error = f"Age must be an integer, got: {type(age).__name__}"
        logger.warning(f"Age range enforcement failed in {context}: {error}")
        return False, error

    if not (min_age <= age_int <= max_age):
        error = f"Age {age_int} is outside valid range [{min_age}, {max_age}]"
        logger.warning(f"Age range enforcement failed in {context}: {error}")
        return False, error

    return True, None


def enforce_embedding_dims(
    embedding: list[float],
    expected_dims: int = EMBEDDING_DIMS,
    context: str = "unknown",
) -> tuple[bool, Optional[str]]:
    """
    Enforce embedding has correct dimensionality.

    CRITICAL: All embeddings MUST have same dimensions (384 for all-MiniLM-L6-v2).
    Mismatch indicates embedding model swap without reingestion.

    Args:
        embedding: Embedding vector to validate
        expected_dims: Expected dimensionality
        context: Where this is being used (for logging)

    Returns:
        (is_valid, error_message)
    """
    if not isinstance(embedding, (list, tuple)):
        error = f"Embedding must be list/tuple, got: {type(embedding).__name__}"
        logger.error(f"Embedding dims enforcement failed in {context}: {error}")
        return False, error

    actual_dims = len(embedding)

    if actual_dims != expected_dims:
        error = (
            f"Embedding dimensionality mismatch: expected {expected_dims}, "
            f"got {actual_dims}. Model swap detected? Context: {context}"
        )
        logger.error(f"Embedding dims enforcement failed in {context}: {error}")
        return False, error

    # ────────────────────────────────────────────────────────────────────
    # Validate embedding values (should be floats between -1 and 1)
    # ────────────────────────────────────────────────────────────────────
    for i, val in enumerate(embedding):
        try:
            float_val = float(val)
            if not (-2.0 <= float_val <= 2.0):
                error = f"Embedding value at index {i} is out of bounds: {float_val}"
                logger.warning(f"Embedding dims enforcement (bounds) in {context}: {error}")
                return False, error
        except (ValueError, TypeError):
            error = f"Embedding value at index {i} is not numeric: {val}"
            logger.error(f"Embedding dims enforcement failed in {context}: {error}")
            return False, error

    return True, None


def validate_metadata_contract(
    metadata: dict[str, Any],
    collection_type: str = "weather",
) -> tuple[bool, list[str]]:
    """
    Validate metadata conforms to collection schema.

    Weather metadata required fields:
      - location_normalized: must be canonical city
      - fetched_at: datetime
      - conditions: string (weather description)
      - temp_c: float (temperature Celsius)

    News metadata required fields:
      - topic: in NEWS_TOPICS
      - source: string (news source)
      - fetched_at: datetime
      - region: optional string

    Args:
        metadata: Metadata dict to validate
        collection_type: "weather" or "news"

    Returns:
        (is_valid, list_of_errors)
    """
    errors = []

    if not isinstance(metadata, dict):
        return False, ["Metadata must be a dictionary"]

    # ────────────────────────────────────────────────────────────────────
    # Common Required Fields
    # ────────────────────────────────────────────────────────────────────

    if "fetched_at" not in metadata:
        errors.append("fetched_at is required")
    elif not isinstance(metadata["fetched_at"], str):
        errors.append("fetched_at must be ISO timestamp string")

    # ────────────────────────────────────────────────────────────────────
    # Weather-Specific Validation
    # ────────────────────────────────────────────────────────────────────
    if collection_type == "weather":
        required_weather_fields = {
            "location_normalized": str,
            "conditions": str,
            "temp_c": (int, float),
        }

        for field, expected_type in required_weather_fields.items():
            if field not in metadata:
                errors.append(f"Weather metadata missing required field: {field}")
            elif not isinstance(metadata[field], expected_type):
                errors.append(
                    f"Field '{field}' must be {expected_type}, "
                    f"got {type(metadata[field]).__name__}"
                )

        # Validate location_normalized is canonical
        if "location_normalized" in metadata:
            location = metadata["location_normalized"]
            is_valid, error = enforce_canonical_cities(location, context="metadata")
            if not is_valid:
                errors.append(f"Weather metadata: {error}")

    # ────────────────────────────────────────────────────────────────────
    # News-Specific Validation
    # ────────────────────────────────────────────────────────────────────
    elif collection_type == "news":
        required_news_fields = {
            "topic": str,
            "source": str,
        }

        for field, expected_type in required_news_fields.items():
            if field not in metadata:
                errors.append(f"News metadata missing required field: {field}")
            elif not isinstance(metadata[field], expected_type):
                errors.append(
                    f"Field '{field}' must be {expected_type}, "
                    f"got {type(metadata[field]).__name__}"
                )

        # Validate topic is in allowed list
        if "topic" in metadata and isinstance(metadata["topic"], str):
            topic = metadata["topic"]
            if topic not in NEWS_TOPICS:
                valid_topics = ", ".join(NEWS_TOPICS)
                errors.append(f"Invalid news topic. Must be one of: {valid_topics}")

    else:
        errors.append(f"Unknown collection type: {collection_type}")

    logger.debug(
        "Metadata contract validated",
        extra={
            "collection_type": collection_type,
            "is_valid": len(errors) == 0,
            "error_count": len(errors),
        }
    )

    return len(errors) == 0, errors


def enforce_name_contract(
    name: str,
    min_length: int = 1,
    max_length: int = 120,
    context: str = "unknown",
) -> tuple[bool, Optional[str]]:
    """
    Enforce employee name constraints.

    Args:
        name: Name string to validate
        min_length: Minimum name length
        max_length: Maximum name length
        context: Where this is being used (for logging)

    Returns:
        (is_valid, error_message)
    """
    if not isinstance(name, str):
        error = f"Name must be string, got: {type(name).__name__}"
        logger.warning(f"Name contract enforcement failed in {context}: {error}")
        return False, error

    name_clean = name.strip()

    if len(name_clean) < min_length:
        error = f"Name too short (min: {min_length})"
        logger.warning(f"Name contract enforcement failed in {context}: {error}")
        return False, error

    if len(name_clean) > max_length:
        error = f"Name too long (max: {max_length})"
        logger.warning(f"Name contract enforcement failed in {context}: {error}")
        return False, error

    return True, None


def validate_data_consistency(
    sql_locations: set[str],
    chroma_locations: set[str],
) -> tuple[bool, list[str]]:
    """
    Validate SQL and Chroma data maintain canonical city consistency.

    Should be run periodically or after ingestion to catch desynchronization.

    Args:
        sql_locations: Set of unique office_location values in SQL
        chroma_locations: Set of unique location_normalized in Chroma weather

    Returns:
        (is_consistent, list_of_inconsistencies)
    """
    inconsistencies = []

    # ────────────────────────────────────────────────────────────────────
    # 1. Check SQL locations are canonical
    # ────────────────────────────────────────────────────────────────────
    canonical_set = set(CANONICAL_CITIES)

    non_canonical_sql = sql_locations - canonical_set
    if non_canonical_sql:
        inconsistencies.append(
            f"Non-canonical cities in SQL: {', '.join(non_canonical_sql)}"
        )

    # ────────────────────────────────────────────────────────────────────
    # 2. Check Chroma locations are canonical
    # ────────────────────────────────────────────────────────────────────
    non_canonical_chroma = chroma_locations - canonical_set
    if non_canonical_chroma:
        inconsistencies.append(
            f"Non-canonical cities in Chroma: {', '.join(non_canonical_chroma)}"
        )

    # ────────────────────────────────────────────────────────────────────
    # 3. Warn about missing data (optional)
    # ────────────────────────────────────────────────────────────────────
    missing_in_sql = canonical_set - sql_locations
    if missing_in_sql:
        inconsistencies.append(
            f"Cities in canonical list but missing from SQL: {', '.join(missing_in_sql)}"
        )

    missing_in_chroma = canonical_set - chroma_locations
    if missing_in_chroma:
        inconsistencies.append(
            f"Cities in canonical list but missing from Chroma: {', '.join(missing_in_chroma)}"
        )

    logger.info(
        "Data consistency check",
        extra={
            "is_consistent": len(inconsistencies) == 0,
            "inconsistency_count": len(inconsistencies),
        }
    )

    return len(inconsistencies) == 0, inconsistencies
