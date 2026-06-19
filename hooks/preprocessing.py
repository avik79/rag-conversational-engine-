"""PreToolUse hooks for pre-execution validation and logging"""
import logging
from typing import Any
from datetime import datetime

logger = logging.getLogger(__name__)


async def log_tool_call(
    tool_name: str,
    tool_args: dict,
    agent_name: str | None = None,
) -> dict[str, Any]:
    """Log tool invocation with args"""
    timestamp = datetime.utcnow().isoformat()
    logger.info(
        f"[{timestamp}] PRE_TOOL_USE: agent={agent_name}, "
        f"tool={tool_name}, args_keys={list(tool_args.keys())}"
    )
    return {
        "logged": True,
        "timestamp": timestamp,
    }


async def check_pii_leakage(
    tool_name: str,
    tool_args: dict,
) -> dict[str, Any]:
    """Detect potential PII leakage in tool arguments"""
    sensitive_patterns = [
        ("ssn", r"^\d{3}-\d{2}-\d{4}$"),
        ("credit_card", r"^\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}$"),
        ("email", r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"),
        ("phone", r"^\d{3}[-.\s]?\d{3}[-.\s]?\d{4}$"),
    ]

    warnings = []
    for key, value in tool_args.items():
        if isinstance(value, str):
            for pii_type, pattern in sensitive_patterns:
                import re
                if re.match(pattern, value):
                    warnings.append(f"Detected {pii_type} in '{key}'")

    if warnings:
        logger.warning(f"PII_LEAKAGE_DETECTED: {warnings}")
        return {
            "has_pii": True,
            "warnings": warnings,
            "blocked": True,
        }

    return {
        "has_pii": False,
        "warnings": [],
        "blocked": False,
    }


async def validate_tool_input(tool_name: str, tool_args: dict) -> dict[str, Any]:
    """Validate tool input schema"""
    required_fields = {
        "execute_employee_query": {"at_least_one": ["name", "department", "office_location", "age_min", "age_max"]},
        "search_weather_embeddings": ["query_text"],
        "search_news_embeddings": ["query_text"],
        "validate_chroma_query": ["collection_name", "filters"],
        "upsert_to_chroma": ["chunks", "collection_name"],
        "validate_location_contract": ["chunks"],
        "generate_embeddings": ["texts"],
        "fetch_tavily_weather": ["locations"],
        "fetch_tavily_news": ["topics"],
        "hitl_gate": ["trigger_reason"],
    }

    if tool_name not in required_fields:
        return {
            "valid": True,
            "field_check": "skipped (tool not in validation list)",
        }

    required = required_fields[tool_name]
    if isinstance(required, dict) and "at_least_one" in required:
        # For employee_query, at least one filter must be provided
        filters = required["at_least_one"]
        if not any(f in tool_args for f in filters):
            logger.error(f"INVALID_INPUT: {tool_name} requires at least one of {filters}")
            return {
                "valid": False,
                "reason": f"Must provide at least one of {filters}",
            }
    else:
        # Standard required fields check
        missing = [f for f in required if f not in tool_args]
        if missing:
            logger.error(f"INVALID_INPUT: {tool_name} missing fields {missing}")
            return {
                "valid": False,
                "reason": f"Missing required fields: {missing}",
            }

    return {
        "valid": True,
        "field_check": "passed",
    }
