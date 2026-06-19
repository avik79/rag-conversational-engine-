"""
NOVA — Neural Observation & Vector Analysis Agent

Role: RAG specialist. NL → Chroma query → grounded synthesis with citations.
Can be used as tool (retrieve context) or full handoff (conversational RAG).

Reference: handoff.md §1.4, AGENT 3
"""

from agents import Agent, RunContextWrapper
from models.pydantic_io import RAGResponse
from config.llm_config import get_claude_model, SHARED_MODEL_SETTINGS


async def nova_instructions(ctx: RunContextWrapper, agent: "Agent") -> str:
    """Dynamic instructions for NOVA RAG agent"""
    return """
You are NOVA (Neural Observation & Vector Analysis Agent).
Your ONLY job: retrieve relevant context from the Chroma vector database and
produce grounded, cited natural language synthesis.

Two collections available:
  1. weather_embeddings — weather snapshots per city. Metadata: location_normalized,
     fetched_at (ISO timestamp), conditions, temp_c.
  2. news_embeddings — news items. Metadata: topic, source, fetched_at, region.

Rules:
  1. Before calling search_weather_embeddings or search_news_embeddings, call
     validate_chroma_query to verify filter keys exist in the collection schema.
  2. ALWAYS include chunk sources (chunk_id, collection, fetched_at) in output.
  3. If fetched_at of the most recent weather chunk is > 6 hours ago, set
     freshness_ok=False in RAGResponse. Do NOT suppress this.
  4. NEVER synthesize claims not present in the retrieved chunks.
  5. If no relevant chunks are found, say so. Do NOT hallucinate context.
""".strip()


NOVA = Agent(
    name="NOVA",
    handoff_description=(
        "RAG specialist. Queries Chroma vector DB for weather and news context. "
        "Returns grounded synthesis with chunk citations and freshness status."
    ),
    instructions=nova_instructions,
    model=get_claude_model(),
    model_settings=SHARED_MODEL_SETTINGS,
    output_type=RAGResponse,
    tools=[
        # Tools will be wired in Phase 4:
        # - validate_chroma_query (calls AXIOM; checks filter key existence)
        # - search_weather_embeddings (vector search on weather_embeddings)
        # - search_news_embeddings (vector search on news_embeddings)
    ],
    tool_use_behavior="run_llm_again",
)
