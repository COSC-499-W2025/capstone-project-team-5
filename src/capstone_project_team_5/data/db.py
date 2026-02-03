"""Database configuration and session management.

This module provides SQLAlchemy 2.x ORM infrastructure including:
- Engine creation with SQLite backend
- Session factory with proper transaction handling
- Database initialization and table creation
- Context manager for safe session usage

The database URL can be overridden via the DB_URL environment variable.
Defaults to sqlite:///<project_root>/database.db for local persistence.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import URL, Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""


_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def get_database_url() -> str:
    """Return the database URL, allowing overrides via environment variable."""
    env_url = os.getenv("DB_URL")
    if env_url:
        return env_url

    project_root = Path(__file__).resolve().parents[3]
    db_path = project_root / "database.db"
    return URL.create("sqlite", database=str(db_path)).render_as_string(hide_password=False)


def _get_engine() -> Engine:
    global _engine
    if _engine is None:
        database_url = get_database_url()
        _engine = create_engine(database_url, echo=False, future=True)
        # Lazy initialization: create tables on first engine access
        _ensure_tables_created()
    return _engine


def _ensure_tables_created() -> None:
    """Ensure all ORM tables are created (called automatically on first engine access)."""
    # Import ORM models so their metadata is registered on Base before create_all.
    from capstone_project_team_5.data.models import (  # noqa: F401
        code_analysis,
        consent_record,
        portfolio,
        portfolio_item,
        project,
        resume,
        upload_record,
        user,
        user_code_analysis,
    )

    Base.metadata.create_all(bind=_engine)


def _get_session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=_get_engine(),
            autoflush=False,
            expire_on_commit=False,
        )
    return _SessionLocal


def init_db() -> None:
    """Create all tables defined on the Base metadata.

    Note: Tables are created automatically on first database access,
    so this function is optional. It exists for explicit initialization
    if needed (e.g., in tests or setup scripts).
    """
    # Trigger lazy initialization by accessing the engine
    _get_engine()


@contextmanager
def get_session() -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""
    session = _get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
