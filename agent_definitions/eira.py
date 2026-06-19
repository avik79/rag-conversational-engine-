"""
EIRA — Executive Intelligence Routing Agent

Role: Orchestrator. Single entry point. Owns conversation. Routes to specialists.
The heart of the system — classifies intent, routes to specialists, validates responses.

Reference: handoff.md §1.4, AGENT 1
"""

from agents import Agent, RunContextWrapper, handoff
from agents.extensions.handoff_filters import remove_all_tools
from pydantic import BaseModel
from models.pydantic_io import EIRAResponse, HITLContext
from config.llm_config import get_claude_model, SHARED_MODEL_SETTINGS


async def eira_instructions(ctx: RunContextWrapper, agent: "Agent") -> str:
    """Dynamic instructions for EIRA orchestrator"""
    session_turn = ctx.context.get("turn_count", 0)
    user_name = ctx.context.get("user_name", "User")
    return f"""
You are EIRA (Executive Intelligence Routing Agent), the orchestrator of a
conversational intelligence system that queries two data domains:

  1. EMPLOYEE DATABASE — SQL (via VEGA): employee name, ID, age, department,
     office location (canonical city). 500 employees.
  2. REAL-TIME KNOWLEDGE — Vector RAG (via NOVA): weather snapshots and news
     fetched from Tavily API, stored as embeddings in Chroma.

Your job:
  a) Classify the user's intent (sql_only | rag_only | cross_domain | meta | unclear).
  b) Route to the correct specialist agent(s).
  c) For cross-domain queries (employee + weather), first call VEGA (tool mode)
     to get the office_location, then call KIRA to resolve that location to a
     Chroma key, then call NOVA (tool mode) to retrieve weather context.
  d) Before ANY query executes, call AXIOM to validate it.
  e) After synthesis, call SENTINEL to validate groundedness.
  f) If SENTINEL confidence < 0.75, or KIRA returns needs_clarification=True,
     or VEGA returns ambiguous_match=True, call hitl_gate immediately.
  g) NEVER fabricate employee data, weather data, or locations. If evidence is
     absent, say so. Cite your sources in every response.

Session context:
  - Turn: {session_turn}
  - User: {user_name}
""".strip()


class HandoffMetadata(BaseModel):
    """Metadata passed during handoffs"""
    reason: str
    subquery: str


def log_handoff_to_vega(ctx: RunContextWrapper, data: HandoffMetadata):
    """Log handoff to VEGA"""
    ctx.context["last_handoff"] = {"to": "VEGA", "reason": data.reason}


def log_handoff_to_nova(ctx: RunContextWrapper, data: HandoffMetadata):
    """Log handoff to NOVA"""
    ctx.context["last_handoff"] = {"to": "NOVA", "reason": data.reason}


def log_handoff_to_iris(ctx: RunContextWrapper, data: HandoffMetadata):
    """Log handoff to IRIS"""
    ctx.context["last_handoff"] = {"to": "IRIS", "reason": data.reason}


EIRA = Agent(
    name="EIRA",
    handoff_description=(
        "Executive Intelligence Routing Agent — the system entry point. "
        "Handles all user queries and routes to SQL, RAG, or ingestion specialists."
    ),
    instructions=eira_instructions,
    model=get_claude_model(),
    model_settings=SHARED_MODEL_SETTINGS,
    output_type=EIRAResponse,
    tools=[],  # Wired via wire_eira_tools()
    handoffs=[],  # Wired via wire_eira_tools()
    input_guardrails=[],  # Will be wired in Phase 5+
    output_guardrails=[],  # Will be wired in Phase 5+
    tool_use_behavior="run_llm_again",
)
