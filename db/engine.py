"""
Database Engine Factory

Provides sync and async SQLAlchemy engines for:
  1. Employee DB (sync) — used by VEGA for ORM queries
  2. Session DB (async) — used by OpenAI Agents SDK for RunState persistence

Reference: handoff.md §2.2
"""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from loguru import logger

# ── Employee DB (sync — used by VEGA for ORM queries) ────────────────
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./data/employees.db")


def get_sync_engine():
    """
    Sync SQLAlchemy engine for employee ORM queries (VEGA).

    For SQLite: StaticPool used to avoid multi-thread issues.
    For PostgreSQL in production: remove connect_args and StaticPool.
    """
    if DATABASE_URL.startswith("sqlite"):
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )
    else:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)

    return engine


# ── Session DB (async — used by SQLAlchemySession for agent memory) ──
SESSION_DATABASE_URL = os.environ.get(
    "SESSION_DATABASE_URL",
    "sqlite+aiosqlite:///./data/agent_sessions.db"
)


def get_async_session_engine() -> AsyncEngine:
    """
    Async engine for OpenAI Agents SDK SQLAlchemySession.

    Uses aiosqlite driver for SQLite; swap to asyncpg for PostgreSQL.
    """
    if SESSION_DATABASE_URL.startswith("sqlite"):
        engine = create_async_engine(
            SESSION_DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        engine = create_async_engine(SESSION_DATABASE_URL, pool_pre_ping=True)

    return engine


# ── Singleton Session Factories ──────────────────────────────────────
_sync_engine = None
_sync_session_factory = None
_async_session_engine = None


def init_db():
    """
    Called once at startup (from app/main.py).

    Creates all tables in the employee database and initializes
    the sync session factory for VEGA tool calls.
    """
    global _sync_engine, _sync_session_factory

    from models.employee import Base

    _sync_engine = get_sync_engine()
    Base.metadata.create_all(_sync_engine)
    _sync_session_factory = sessionmaker(bind=_sync_engine, autoflush=False)

    logger.info(f"Employee DB initialized: {DATABASE_URL}")


def get_db_session() -> Session:
    """Context-managed sync session for VEGA tool calls."""
    if _sync_session_factory is None:
        raise RuntimeError("init_db() must be called before get_db_session()")
    return _sync_session_factory()


def get_session_engine() -> AsyncEngine:
    """Returns the singleton async engine for agent session storage."""
    global _async_session_engine
    if _async_session_engine is None:
        _async_session_engine = get_async_session_engine()
    return _async_session_engine
