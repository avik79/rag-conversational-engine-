"""
ChromaDB Client Singleton

Single point of initialization and access for all Chroma operations.
Collections created with:
  - Explicit cosine distance (hnsw:space = cosine)
  - OpenAI text-embedding-3-small via OpenAIEmbeddingFunction
  - Metadata schema enforced by IRIS at write; AXIOM at query

Reference: handoff.md §2.6
"""

import os
import chromadb
from chromadb.utils import embedding_functions
from chromadb import Collection
from config.constants import (
    WEATHER_COLLECTION,
    NEWS_COLLECTION,
    EMBEDDING_MODEL,
    CHROMA_DISTANCE,
)
from loguru import logger

_chroma_client: chromadb.Client | None = None
_weather_collection: Collection | None = None
_news_collection: Collection | None = None


def _get_embedding_function():
    """
    OpenAI embedding function using text-embedding-3-small (1536 dims).

    CRITICAL: This same function is used at ingestion (IRIS) AND query time (NOVA).
    They MUST use the same model. Never change one without the other.
    """
    return embedding_functions.OpenAIEmbeddingFunction(
        api_key=os.environ["OPENAI_API_KEY"],
        model_name=EMBEDDING_MODEL,
    )


def init_chroma():
    """
    Called once at startup (from app/main.py or cli).

    Initializes the Chroma client and creates/gets both collections:
      - weather_embeddings: weather snapshots per city
      - news_embeddings: news items per topic
    """
    global _chroma_client, _weather_collection, _news_collection

    chroma_host = os.environ.get("CHROMA_HOST", "embedded")
    persist_dir = os.environ.get("CHROMA_PERSIST_DIR", "./data/chroma")

    if chroma_host == "embedded":
        # Development: in-process Chroma with local persistence
        _chroma_client = chromadb.PersistentClient(path=persist_dir)
        logger.info(f"Chroma: embedded PersistentClient at {persist_dir}")
    else:
        # Production: Chroma HTTP server
        _chroma_client = chromadb.HttpClient(
            host=chroma_host,
            port=int(os.environ.get("CHROMA_PORT", 8000)),
        )
        logger.info(
            f"Chroma: HttpClient at {chroma_host}:{os.environ.get('CHROMA_PORT', 8000)}"
        )

    emb_fn = _get_embedding_function()

    # ── Weather Collection ───────────────────────────────────────────
    _weather_collection = _chroma_client.get_or_create_collection(
        name=WEATHER_COLLECTION,
        embedding_function=emb_fn,
        metadata={
            "hnsw:space": CHROMA_DISTANCE,
            "schema_keys": "location_normalized,fetched_at,conditions,temp_c",
            "description": "Weather snapshots per canonical city from Tavily API",
        },
    )
    logger.info(
        f"Chroma collection '{WEATHER_COLLECTION}': {_weather_collection.count()} documents"
    )

    # ── News Collection ─────────────────────────────────────────────
    _news_collection = _chroma_client.get_or_create_collection(
        name=NEWS_COLLECTION,
        embedding_function=emb_fn,
        metadata={
            "hnsw:space": CHROMA_DISTANCE,
            "schema_keys": "topic,source,fetched_at,region",
            "description": "News items from Tavily API",
        },
    )
    logger.info(
        f"Chroma collection '{NEWS_COLLECTION}': {_news_collection.count()} documents"
    )


def get_weather_collection() -> Collection:
    """Get weather_embeddings collection (lazy load)."""
    if _weather_collection is None:
        raise RuntimeError("init_chroma() must be called before get_weather_collection()")
    return _weather_collection


def get_news_collection() -> Collection:
    """Get news_embeddings collection (lazy load)."""
    if _news_collection is None:
        raise RuntimeError("init_chroma() must be called before get_news_collection()")
    return _news_collection


def get_chroma_client() -> chromadb.Client:
    """Get the Chroma client singleton (lazy load)."""
    if _chroma_client is None:
        raise RuntimeError("init_chroma() must be called before get_chroma_client()")
    return _chroma_client
