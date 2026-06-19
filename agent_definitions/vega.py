"""
VEGA — Verified Employee & Geo-data Agent

Role: SQL specialist. NL → SQLAlchemy ORM → EmployeeQueryResult.
Can be used as tool (simple queries) or full handoff (complex queries).

Reference: handoff.md §1.4, AGENT 2
"""

from agents import Agent, RunContextWrapper
from models.pydantic_io import EmployeeQueryResult
from config.llm_config import get_claude_model, SHARED_MODEL_SETTINGS


async def vega_instructions(ctx: RunContextWrapper, agent: "Agent") -> str:
    """Dynamic instructions for VEGA SQL agent"""
    return """
You are VEGA (Verified Employee & Geo-data Agent).
Your ONLY job: translate natural language queries into SQLAlchemy ORM queries
against the employees table, execute them, and return structured results.

Table schema:
  employees(employee_id PK, name VARCHAR, age INTEGER,
            department VARCHAR, office_location VARCHAR)

Rules:
  1. BEFORE executing any query, call validate_sql_query with the generated SQL.
     If it returns safe_to_execute=False, do NOT execute. Return the issue.
  2. If a name query matches >1 row, set ambiguous_match=True. Do NOT pick one.
  3. NEVER guess column values. Query only what exists in the schema.
  4. Always include the raw SQL string in your output for audit purposes.
  5. office_location values are canonical city strings (e.g. "Austin, TX").
     Never modify or normalize them — return them exactly as stored.
""".strip()


VEGA = Agent(
    name="VEGA",
    handoff_description=(
        "SQL specialist for the employee database. Handles NL → SQL translation "
        "and execution. Returns structured employee records with audit SQL."
    ),
    instructions=vega_instructions,
    model=get_claude_model(),
    model_settings=SHARED_MODEL_SETTINGS,
    output_type=EmployeeQueryResult,
    tools=[
        # Tools will be wired in Phase 4:
        # - validate_sql_query (calls AXIOM; blocks execution if unsafe)
        # - execute_employee_query (ORM query wrapper)
        # - get_schema_snapshot (returns live schema dict for AXIOM)
    ],
    tool_use_behavior="run_llm_again",
)
