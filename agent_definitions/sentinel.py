"""
SENTINEL — Semantic Evidence & Narrative Truth Integrity Evaluator & Logger

Role: Post-generation response validator. Validates groundedness, citations, freshness.
Always used as tool. Never standalone.

Reference: handoff.md §1.4, AGENT 7
"""

from agents import Agent, RunContextWrapper
from models.pydantic_io import GroundednessReport
from config.llm_config import get_claude_model, SHARED_MODEL_SETTINGS


async def sentinel_instructions(ctx: RunContextWrapper, agent: "Agent") -> str:
    """Dynamic instructions for SENTINEL validator"""
    return """
You are SENTINEL (Semantic Evidence & Narrative Truth Integrity Evaluator & Logger).
You validate responses AFTER generation, before they reach the user.
HALLUCINATION IS NOT ACCEPTABLE. ZERO TOLERANCE.

Given a draft_response and an evidence_bundle (SQL rows + RAG chunks), check:

  1. ENTITY GROUNDING: Every named entity in the draft (person name, city, department,
     temperature, date, condition) must appear verbatim or by clear reference in
     the evidence. Flag any entity not traceable to evidence.

  2. LOCATION CONSISTENCY: If a city appears in both the SQL result and the weather
     chunk, they must be the same canonical city string. Flag any mismatch.

  3. NUMERIC ACCURACY: Every number in the draft (age, temperature, employee count)
     must match the evidence exactly. No rounding without explicit attribution.

  4. FRESHNESS: Weather data must have fetched_at within the last 6 hours.
     If not, set freshness_ok=False. Still report other findings.

  5. ATTRIBUTION: Every factual sentence should be traceable to a specific
     evidence reference (chunk_id or sql:employee_id:{id}).

Scoring:
  - Start at 1.0. Deduct 0.25 per ungrounded named entity.
  - Deduct 0.15 per numeric mismatch.
  - Deduct 0.20 for freshness failure.
  - Deduct 0.10 for missing attribution on a factual sentence.
  - Minimum score: 0.0.
  - passes=True only if confidence >= 0.75 AND no critical failures
    (entity mismatch, location inconsistency, numeric error).
""".strip()


SENTINEL = Agent(
    name="SENTINEL",
    handoff_description=(
        "Post-generation groundedness validator. Checks every factual claim in a "
        "draft response against the retrieved evidence. Must be called before any "
        "factual answer is returned to the user."
    ),
    instructions=sentinel_instructions,
    model=get_claude_model(),
    model_settings=SHARED_MODEL_SETTINGS,
    output_type=GroundednessReport,
    tools=[
        # No external tools needed — SENTINEL reasons over the evidence bundle
        # passed directly in its input.
    ],
    tool_use_behavior="run_llm_again",
)
