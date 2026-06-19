#!/usr/bin/env python3
"""
Initialize All Databases

Sets up both SQLite (employees) and Chroma (vector store) from scratch.

Usage:
    python scripts/init_databases.py [--no-seed]

Flags:
    --no-seed: Create databases without seeding employees
"""

import sys
import os
from pathlib import Path

# Fix encoding on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from dotenv import load_dotenv


def main():
    # Load environment
    load_dotenv()

    # Create data directory
    os.makedirs("data", exist_ok=True)
    logger.info("Data directory ready: ./data/")

    # Initialize employee database
    logger.info("\n=== Initializing Employee Database ===")
    try:
        from db.engine import init_db
        init_db()
        logger.info("[OK] Employee database schema created")
    except Exception as e:
        logger.error(f"[FAIL] Could not initialize employee DB: {e}")
        return 1

    # Seed employees (unless --no-seed)
    if "--no-seed" not in sys.argv:
        logger.info("\n=== Seeding 500 Employees ===")
        try:
            from db.seed import run_seed
            run_seed(clear_existing=True)
            logger.info("[OK] 500 employees seeded")
        except Exception as e:
            logger.error(f"[FAIL] Could not seed employees: {e}")
            return 1
    else:
        logger.info("[SKIP] --no-seed flag set, skipping employee seed")

    # Initialize Chroma
    logger.info("\n=== Initializing Chroma Vector Store ===")
    try:
        from chroma.client import init_chroma
        init_chroma()
        logger.info("[OK] Chroma collections initialized")
    except Exception as e:
        logger.error(f"[FAIL] Could not initialize Chroma: {e}")
        return 1

    logger.info("\n" + "=" * 70)
    logger.info("DATABASE INITIALIZATION COMPLETE")
    logger.info("=" * 70)
    logger.info("Status:")
    logger.info("  [OK] Employee DB: ./data/employees.db")
    if "--no-seed" not in sys.argv:
        logger.info("  [OK] 500 employees seeded")
    logger.info("  [OK] Chroma: weather_embeddings + news_embeddings (empty, ready for IRIS)")
    logger.info("  [OK] Session DB: ./data/agent_sessions.db (for agent RunState)")
    logger.info("\nNext steps:")
    logger.info("  1. Run Phase 3: Agent definitions")
    logger.info("  2. Run Phase 4: Tool implementations")
    logger.info("  3. Run Phase 5: Streamlit UI")

    return 0


if __name__ == "__main__":
    sys.exit(main())
