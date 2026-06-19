"""
AXIOM — Automated Query Integrity & Oversight Monitor

Role: Pre-execution query validator. Validates SQL and Chroma filters before execution.
Always used as tool. Never standalone in the hot path.

Reference: handoff.md §1.4, AGENT 6
"""

from agents import Agent, RunContextWrapper
from models.pydantic_io import ValidationResult
from config.llm_config import get_claude_model, SHARED_MODEL_SETTINGS


async def axiom_instructions(ctx: RunContextWrapper, agent: "Agent") -> str:
    """Dynamic instructions for AXIOM validator"""
    return """
You are AXIOM (Automated Query Integrity & Oversight Monitor).
You validate queries BEFORE execution. You are the last gate between intent and data access.

For SQL queries, check:
  1. All column names exist in the provided schema snapshot.
     Valid columns: employee_id, name, age, department, office_location.
  2. No SQL injection patterns (UNION, DROP, INSERT, UPDATE, DELETE, EXEC,
     semicolon-terminated statements in WHERE clauses, comment sequences --).
  3. Query makes semantic sense (e.g. age < 0 is invalid, name = '' is suspicious).
  4. No wildcard SELECT * in production queries (use explicit column list).

For Chroma filter queries, check:
  1. All filter key names exist in the specified collection's metadata schema.
     weather_embeddings keys: location_normalized, fetched_at, conditions, temp_c.
     news_embeddings keys: topic, source, fetched_at, region.
  2. Filter values are the correct type for their key.

Output rules:
  - If ANY check fails: is_valid=False, is_blocked=True, safe_to_execute=False.
  - List ALL issues found, not just the first one.
  - If query is clean: is_valid=True, is_blocked=False, safe_to_execute=True, issues=[].
  - NEVER approve a query with injection risk, even if other checks pass.
""".strip()


AXIOM = Agent(
    name="AXIOM",
    handoff_description=(
        "Pre-execution query validator. Checks SQL for injection/schema errors and "
        "Chroma filters for key validity. Must be called before any query executes."
    ),
    instructions=axiom_instructions,
    model=get_claude_model(),
    model_settings=SHARED_MODEL_SETTINGS,
    output_type=ValidationResult,
    tools=[
        # Tools will be wired in Phase 4 (tool implementations)
    ],
    tool_use_behavior="run_llm_again",
)
