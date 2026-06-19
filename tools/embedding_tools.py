"""Embedding tools for IRIS and KIRA agents"""
from typing import Any
from sentence_transformers import SentenceTransformer
from config.constants import EMBEDDING_MODEL, EMBEDDING_DIMS

_model_cache = None

def _get_model():
    """Lazy load and cache the embedding model"""
    global _model_cache
    if _model_cache is None:
        _model_cache = SentenceTransformer(EMBEDDING_MODEL)
    return _model_cache


def generate_embeddings(texts: list[str]) -> dict[str, Any]:
    """Generate embeddings using sentence-transformers (local, no API key needed)"""
    try:
        model = _get_model()
        embeddings = model.encode(texts, convert_to_numpy=False)

        embeddings_list = []
        for embedding in embeddings:
            emb_list = embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)
            if len(emb_list) != EMBEDDING_DIMS:
                return {
                    "success": False,
                    "error": f"Embedding dimension mismatch: got {len(emb_list)}, expected {EMBEDDING_DIMS}",
                    "embeddings": [],
                }
            embeddings_list.append(emb_list)

        return {
            "success": True,
            "embeddings": embeddings_list,
            "model": EMBEDDING_MODEL,
            "dimension": EMBEDDING_DIMS,
            "count": len(embeddings_list),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "embeddings": [],
        }


async def semantic_location_match(location_text: str, candidates: list[str]) -> dict[str, Any]:
    """Find nearest canonical city via semantic similarity"""
    try:
        # Generate embedding for input location
        input_result = generate_embeddings([location_text])
        if not input_result["success"]:
            return {
                "match": None,
                "confidence": 0.0,
                "error": input_result["error"],
            }

        input_embedding = input_result["embeddings"][0]

        # Generate embeddings for candidates
        candidates_result = generate_embeddings(candidates)
        if not candidates_result["success"]:
            return {
                "match": None,
                "confidence": 0.0,
                "error": candidates_result["error"],
            }

        # Compute cosine similarity
        import numpy as np
        input_vec = np.array(input_embedding)
        best_match = None
        best_score = -1.0

        for i, candidate in enumerate(candidates):
            candidate_vec = np.array(candidates_result["embeddings"][i])
            # Cosine similarity
            similarity = np.dot(input_vec, candidate_vec) / (
                np.linalg.norm(input_vec) * np.linalg.norm(candidate_vec)
            )
            if similarity > best_score:
                best_score = similarity
                best_match = candidate

        # Normalize to [0, 1] from cosine [-1, 1]
        confidence = (best_score + 1.0) / 2.0

        return {
            "match": best_match,
            "confidence": confidence,
            "error": None,
        }
    except Exception as e:
        return {
            "match": None,
            "confidence": 0.0,
            "error": str(e),
        }
