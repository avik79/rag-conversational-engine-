"""PostToolUse hooks for result validation and HITL tracking"""
import logging
from typing import Any
from datetime import datetime

logger = logging.getLogger(__name__)


async def log_tool_result(
    tool_name: str,
    result: Any,
    execution_time_ms: float | None = None,
) -> dict[str, Any]:
    """Log tool result with latency"""
    timestamp = datetime.utcnow().isoformat()
    result_summary = str(result)[:100]  # First 100 chars

    logger.info(
        f"[{timestamp}] POST_TOOL_USE: tool={tool_name}, "
        f"result_preview={result_summary}, latency_ms={execution_time_ms}"
    )
    return {
        "logged": True,
        "timestamp": timestamp,
    }


async def detect_hitl_triggers(
    tool_name: str,
    result: dict,
) -> dict[str, Any]:
    """Detect HITL gate triggers from tool results"""
    triggers = []

    # AXIOM validation failures
    if tool_name == "validate_query" and not result.get("safe_to_execute"):
        triggers.append({
            "gate": "AXIOM_BLOCKED",
            "reason": "Query validation failed",
            "issues": result.get("issues", []),
        })

    # VEGA ambiguous matches
    if tool_name == "query_employees" and result.get("ambiguous_match"):
        triggers.append({
            "gate": "VEGA_AMBIGUOUS",
            "reason": "Employee name query matched multiple rows",
            "rows": result.get("row_count"),
        })

    # KIRA needs clarification
    if tool_name == "resolve_location" and result.get("needs_clarification"):
        triggers.append({
            "gate": "KIRA_CLARIFICATION",
            "reason": "Location resolution unclear",
            "confidence": result.get("confidence"),
        })

    # SENTINEL low confidence
    if tool_name == "validate_response" and result.get("confidence", 1.0) < 0.75:
        triggers.append({
            "gate": "SENTINEL_LOW_CONFIDENCE",
            "reason": "Response groundedness below threshold",
            "confidence": result.get("confidence"),
            "ungrounded_claims": result.get("ungrounded_claims", []),
        })

    # IRIS overwrite gate
    if tool_name == "trigger_ingestion" and result.get("blocked"):
        triggers.append({
            "gate": "IRIS_OVERWRITE",
            "reason": "Ingestion would overwrite >80% of collection",
            "blocks": result.get("reason"),
        })

    # Chroma validation failures
    if tool_name in ["validate_chroma_query", "validate_location_contract"]:
        if not result.get("is_valid") or result.get("violations"):
            triggers.append({
                "gate": "CHROMA_VALIDATION",
                "reason": f"Chroma validation failed for {tool_name}",
                "issues": result.get("issues") or result.get("violations"),
            })

    if triggers:
        logger.warning(f"HITL_TRIGGERS_DETECTED: {len(triggers)} gate(s) activated")
        for trigger in triggers:
            logger.warning(f"  - {trigger['gate']}: {trigger['reason']}")

        return {
            "has_triggers": True,
            "trigger_count": len(triggers),
            "triggers": triggers,
        }

    return {
        "has_triggers": False,
        "trigger_count": 0,
        "triggers": [],
    }


async def measure_latency(
    start_time: float,
    end_time: float,
    tool_name: str,
) -> dict[str, Any]:
    """Measure and log tool execution latency"""
    latency_ms = (end_time - start_time) * 1000
    logger.info(f"LATENCY: {tool_name} took {latency_ms:.2f}ms")

    # Flag slow operations
    if latency_ms > 5000:  # >5 seconds
        logger.warning(f"SLOW_OPERATION: {tool_name} took {latency_ms:.2f}ms")

    return {
        "latency_ms": latency_ms,
        "slow": latency_ms > 5000,
    }


async def validate_tool_output(
    tool_name: str,
    result: dict,
) -> dict[str, Any]:
    """Validate tool output against expected schema"""
    # Define output schemas (minimal validation)
    expected_keys = {
        "execute_employee_query": ["employees", "query_sql", "row_count"],
        "search_weather_embeddings": ["sources", "count"],
        "search_news_embeddings": ["sources", "count"],
        "validate_chroma_query": ["is_valid", "issues"],
        "upsert_to_chroma": ["success", "ingested", "collection"],
        "validate_location_contract": ["is_valid", "violations"],
        "generate_embeddings": ["success", "embeddings"],
        "fetch_tavily_weather": ["success", "results"],
        "fetch_tavily_news": ["success", "results"],
        "validate_query": ["is_valid", "is_blocked", "safe_to_execute"],
        "resolve_location": ["canonical_key", "confidence", "needs_clarification"],
        "validate_response": ["confidence", "passes"],
        "trigger_ingestion": ["success", "ingested"],
    }

    if tool_name not in expected_keys:
        return {
            "valid": True,
            "check": "skipped (tool not in validation list)",
        }

    expected = expected_keys[tool_name]
    if not isinstance(result, dict):
        logger.error(f"OUTPUT_SCHEMA_ERROR: {tool_name} returned non-dict: {type(result)}")
        return {
            "valid": False,
            "reason": f"Expected dict, got {type(result)}",
        }

    missing = [k for k in expected if k not in result]
    if missing:
        logger.error(f"OUTPUT_SCHEMA_ERROR: {tool_name} missing keys {missing}")
        return {
            "valid": False,
            "reason": f"Missing expected keys: {missing}",
        }

    return {
        "valid": True,
        "check": "passed",
    }
