"""
IRIS — Ingestion & Real-time Intelligence Sync Agent

Role: Tavily API → chunk → embed → upsert to Chroma. Offline / on-demand.
The ONLY agent with Chroma write access.

Reference: handoff.md §1.4, AGENT 4
"""

from agents import Agent, RunContextWrapper
from models.pydantic_io import IngestionReport
from config.llm_config import get_claude_model, SHARED_MODEL_SETTINGS
from config.constants import CANONICAL_CITIES


async def iris_instructions(ctx: RunContextWrapper, agent: "Agent") -> str:
    """Dynamic instructions for IRIS ingestion agent"""
    cities = ", ".join(CANONICAL_CITIES)
    return f"""
You are IRIS (Ingestion & Real-time Intelligence Sync Agent).
Your job: fetch weather and news from Tavily, chunk the content, generate
embeddings, and upsert to Chroma. You are the ONLY agent that writes to Chroma.

Canonical city list (the ONLY valid values for location_normalized):
  {cities}

Rules:
  1. Every weather chunk MUST have metadata.location_normalized set to a value
     from the canonical city list above. If Tavily returns a non-canonical
     location string, normalize it or reject the chunk. NEVER ingest with a
     missing or non-canonical location_normalized.
  2. Before upserting, call validate_location_contract for every chunk batch.
     If any chunk fails, reject the entire batch (do not partial-ingest).
  3. If this ingestion would overwrite >80% of an existing collection, call
     hitl_gate with trigger_reason="reingestion_overwrite". Do not proceed
     until approved.
  4. Log every ingestion: chunks_ingested, chunks_rejected, rejection_reasons,
     location_contract_violations, ingestion_timestamp in IngestionReport.
  5. Embed using OpenAI text-embedding-3-small for consistency with NOVA's
     query-time embedding model. They MUST match.
""".strip()


IRIS = Agent(
    name="IRIS",
    handoff_description=(
        "Ingestion specialist. Fetches weather/news from Tavily, chunks, embeds, "
        "and upserts to Chroma. The only agent with Chroma write access."
    ),
    instructions=iris_instructions,
    model=get_claude_model(),
    model_settings=SHARED_MODEL_SETTINGS,
    output_type=IngestionReport,
    tools=[
        # Tools will be wired in Phase 4:
        # - fetch_tavily_weather(locations: list[str]) -> list[RawWeatherItem]
        # - fetch_tavily_news(topics: list[str]) -> list[RawNewsItem]
        # - validate_location_contract(chunks: list[EmbeddingChunk])
        # - upsert_to_chroma(chunks: list[EmbeddingChunk])
        # - generate_embeddings(texts: list[str])
        # - hitl_gate (needs_approval=True for >80% overwrite)
    ],
    tool_use_behavior="run_llm_again",
)
