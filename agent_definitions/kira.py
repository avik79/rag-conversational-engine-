"""
KIRA — Knowledge & Intent Resolution Agent

Role: Semantic location resolver. Resolves office_location strings → Chroma metadata keys.
Default mode: as_tool on EIRA. Standalone agent only for complex alias resolution.

Reference: handoff.md §1.4, AGENT 5
"""

from agents import Agent, RunContextWrapper
from models.pydantic_io import LocationResolution
from config.llm_config import get_claude_model, SHARED_MODEL_SETTINGS


async def kira_instructions(ctx: RunContextWrapper, agent: "Agent") -> str:
    """Dynamic instructions for KIRA resolver"""
    return """
You are KIRA (Knowledge & Intent Resolution Agent).
Your ONLY job: take a raw location string from the employee database and resolve
it to the canonical city key used in Chroma weather_embeddings metadata.

This is the semantic bridge between two data domains. Accuracy is critical.

Resolution steps:
  1. First attempt exact string match against the canonical city list.
     If match → confidence=1.0, match_method="exact".
  2. If no exact match → attempt fuzzy string matching (Levenshtein distance).
     If distance ≤ 2 → confidence=0.9, match_method="fuzzy".
  3. If fuzzy fails → embed the input and call semantic_location_match to find
     the nearest canonical city vector.
     Return confidence from the cosine similarity score.
     match_method="semantic".
  4. If all methods fail → set match_method="failed", needs_clarification=True,
     confidence=0.0. Do NOT guess a city.

NEVER map a location to a city not in the canonical list.
NEVER return needs_clarification=False if confidence < 0.80.
""".strip()


KIRA = Agent(
    name="KIRA",
    handoff_description=(
        "Semantic location resolver. Maps raw employee office_location strings "
        "to canonical Chroma weather metadata keys. Critical for cross-domain queries."
    ),
    instructions=kira_instructions,
    model=get_claude_model(),
    model_settings=SHARED_MODEL_SETTINGS,
    output_type=LocationResolution,
    tools=[
        # Tools will be wired in Phase 4
    ],
    tool_use_behavior="stop_on_first_tool",
)
