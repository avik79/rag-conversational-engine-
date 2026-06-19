"""Chroma tools for NOVA and IRIS agents"""
from typing import Any
from chroma.client import (
    get_chroma_client,
    get_weather_collection,
    get_news_collection,
)
from models.pydantic_io import EmbeddingChunk, ChunkSource
from config.constants import CANONICAL_CITIES


async def validate_chroma_query(collection_name: str, filters: dict) -> dict[str, Any]:
    """Validate filter keys exist in collection schema before query"""
    try:
        if collection_name == "weather_embeddings":
            collection = get_weather_collection()
            valid_keys = {"location_normalized", "fetched_at", "conditions", "temp_c"}
        elif collection_name == "news_embeddings":
            collection = get_news_collection()
            valid_keys = {"topic", "source", "fetched_at", "region"}
        else:
            return {
                "is_valid": False,
                "issues": [f"Unknown collection: {collection_name}"],
            }

        filter_keys = set(filters.keys()) if filters else set()
        invalid_keys = filter_keys - valid_keys

        if invalid_keys:
            return {
                "is_valid": False,
                "issues": [f"Invalid filter keys: {invalid_keys}"],
            }

        return {
            "is_valid": True,
            "issues": [],
        }
    except Exception as e:
        return {
            "is_valid": False,
            "issues": [str(e)],
        }


async def search_weather_embeddings(
    query_text: str,
    location_filter: str | None = None,
    n_results: int = 4,
) -> dict[str, Any]:
    """Vector search on weather_embeddings collection"""
    try:
        collection = get_weather_collection()

        where_filter = None
        if location_filter:
            where_filter = {"location_normalized": {"$eq": location_filter}}

        results = collection.query(
            query_texts=[query_text],
            where=where_filter,
            n_results=n_results,
        )

        sources = []
        if results["ids"] and len(results["ids"]) > 0:
            for i, chunk_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                sources.append(
                    ChunkSource(
                        chunk_id=chunk_id,
                        collection="weather_embeddings",
                        text=results["documents"][0][i],
                        metadata=metadata,
                        distance=results["distances"][0][i],
                    )
                )

        return {
            "sources": [s.model_dump() for s in sources],
            "count": len(sources),
        }
    except Exception as e:
        return {
            "sources": [],
            "count": 0,
            "error": str(e),
        }


async def search_news_embeddings(
    query_text: str,
    topic_filter: str | None = None,
    n_results: int = 4,
) -> dict[str, Any]:
    """Vector search on news_embeddings collection"""
    try:
        collection = get_news_collection()

        where_filter = None
        if topic_filter:
            where_filter = {"topic": {"$eq": topic_filter}}

        results = collection.query(
            query_texts=[query_text],
            where=where_filter,
            n_results=n_results,
        )

        sources = []
        if results["ids"] and len(results["ids"]) > 0:
            for i, chunk_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                sources.append(
                    ChunkSource(
                        chunk_id=chunk_id,
                        collection="news_embeddings",
                        text=results["documents"][0][i],
                        metadata=metadata,
                        distance=results["distances"][0][i],
                    )
                )

        return {
            "sources": [s.model_dump() for s in sources],
            "count": len(sources),
        }
    except Exception as e:
        return {
            "sources": [],
            "count": 0,
            "error": str(e),
        }


async def validate_location_contract(chunks: list[dict]) -> dict[str, Any]:
    """Validate all chunks have location_normalized from CANONICAL_CITIES"""
    violations = []

    for i, chunk in enumerate(chunks):
        metadata = chunk.get("metadata", {})
        location = metadata.get("location_normalized")

        if not location:
            violations.append(
                f"Chunk {i}: missing location_normalized"
            )
        elif location not in CANONICAL_CITIES:
            violations.append(
                f"Chunk {i}: non-canonical location '{location}'"
            )

    if violations:
        return {
            "is_valid": False,
            "violations": violations,
            "violation_count": len(violations),
        }

    return {
        "is_valid": True,
        "violations": [],
        "violation_count": 0,
    }


async def upsert_to_chroma(
    chunks: list[dict],
    collection_name: str,
) -> dict[str, Any]:
    """Batch upsert chunks to Chroma collection"""
    try:
        if collection_name == "weather_embeddings":
            collection = get_weather_collection()
        elif collection_name == "news_embeddings":
            collection = get_news_collection()
        else:
            return {
                "success": False,
                "error": f"Unknown collection: {collection_name}",
                "ingested": 0,
            }

        ids = []
        documents = []
        metadatas = []

        for chunk in chunks:
            ids.append(chunk.get("id"))
            documents.append(chunk.get("text"))
            metadatas.append(chunk.get("metadata", {}))

        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

        return {
            "success": True,
            "ingested": len(ids),
            "collection": collection_name,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "ingested": 0,
        }
