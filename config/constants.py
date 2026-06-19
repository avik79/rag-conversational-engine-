"""
Constants — The Canonical City Contract

Single source of truth for location strings, departments, thresholds, and collection names.
Binds SQL office_location column to Chroma location_normalized metadata field.

Reference: handoff.md §2.1
"""

from typing import Final

# ── Canonical City List ──────────────────────────────────────────────
# These exact strings MUST appear in:
#   - employees.office_location   (SQL column)
#   - weather_embeddings metadata.location_normalized  (Chroma)
# IRIS validates every ingested weather chunk against this list.
# KIRA resolves any employee location string to one of these.
# NEVER add a city here without also ensuring Tavily coverage for it.

CANONICAL_CITIES: Final[list[str]] = [
    "Austin, TX",
    "Seattle, WA",
    "New York, NY",
    "Chicago, IL",
    "Denver, CO",
    "Boston, MA",
    "Atlanta, GA",
    "Miami, FL",
    "London, UK",
    "Toronto, CA",
]

# City → Tavily query string mapping
# Used by IRIS when building fetch_tavily_weather() calls.
CITY_WEATHER_QUERIES: Final[dict[str, str]] = {
    "Austin, TX": "current weather Austin Texas today",
    "Seattle, WA": "current weather Seattle Washington today",
    "New York, NY": "current weather New York City today",
    "Chicago, IL": "current weather Chicago Illinois today",
    "Denver, CO": "current weather Denver Colorado today",
    "Boston, MA": "current weather Boston Massachusetts today",
    "Atlanta, GA": "current weather Atlanta Georgia today",
    "Miami, FL": "current weather Miami Florida today",
    "London, UK": "current weather London United Kingdom today",
    "Toronto, CA": "current weather Toronto Canada today",
}

# ── Department List ──────────────────────────────────────────────────
DEPARTMENTS: Final[list[str]] = [
    "Engineering",
    "Sales",
    "Human Resources",
    "Finance",
    "Operations",
    "Product",
    "Marketing",
    "Legal",
]

# ── Chroma Collection Names ──────────────────────────────────────────
WEATHER_COLLECTION: Final[str] = "weather_embeddings"
NEWS_COLLECTION: Final[str] = "news_embeddings"

# ── Embedding Model ──────────────────────────────────────────────────
# CRITICAL: This model MUST be the same at ingestion (IRIS) and query time (NOVA)
# Using sentence-transformers for local embeddings (no API key needed)
EMBEDDING_MODEL: Final[str] = "all-MiniLM-L6-v2"
EMBEDDING_DIMS: Final[int] = 384  # all-MiniLM-L6-v2 output dimensions
CHROMA_DISTANCE: Final[str] = "cosine"  # hnsw:space metric

# ── Tuning Thresholds ────────────────────────────────────────────────
TOP_K_RETRIEVAL: Final[int] = 4  # n_results for Chroma queries
WEATHER_FRESHNESS_HOURS: Final[int] = 6  # NOVA freshness check window
SENTINEL_CONFIDENCE_THRESHOLD: Final[float] = 0.75  # Groundedness threshold
KIRA_CONFIDENCE_THRESHOLD: Final[float] = 0.80  # Location resolution threshold
IRIS_OVERWRITE_THRESHOLD: Final[float] = 0.80  # Collection overwrite % threshold

# ── Chunking Parameters ──────────────────────────────────────────────
CHUNK_SIZE_TOKENS: Final[int] = 400  # target tokens per chunk
CHUNK_OVERLAP_TOKENS: Final[int] = 60  # ~15% overlap

# ── News Topics ──────────────────────────────────────────────────────
NEWS_TOPICS: Final[list[str]] = [
    "technology",
    "business",
    "finance",
    "weather",
    "world news",
]

# ── Convenient Lookups ──────────────────────────────────────────────
CITY_SET: Final[set[str]] = set(CANONICAL_CITIES)
DEPT_SET: Final[set[str]] = set(DEPARTMENTS)
TOPIC_SET: Final[set[str]] = set(NEWS_TOPICS)
