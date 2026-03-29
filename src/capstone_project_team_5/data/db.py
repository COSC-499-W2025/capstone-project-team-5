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

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL, Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""


_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def get_database_url() -> str:
    """Return the database URL, allowing overrides via environment variable.

    Checks DATABASE_URL (Railway auto-injects for PostgreSQL plugin),
    then DB_URL, then falls back to a local SQLite file.
    """
    env_url = os.getenv("DATABASE_URL") or os.getenv("DB_URL")
    if env_url:
        # Railway injects postgres:// but SQLAlchemy 2.x requires postgresql://
        if env_url.startswith("postgres://"):
            env_url = env_url.replace("postgres://", "postgresql://", 1)
        return env_url

    project_root = Path(__file__).resolve().parents[3]
    db_path = project_root / "database.db"
    return URL.create("sqlite", database=str(db_path)).render_as_string(hide_password=False)


def _get_engine() -> Engine:
    global _engine
    if _engine is None:
        database_url = get_database_url()
        kwargs: dict = {"echo": False, "future": True}
        if not database_url.startswith("sqlite"):
            kwargs.update(pool_size=5, max_overflow=10)
        _engine = create_engine(database_url, **kwargs)
        # Lazy initialization: create tables on first engine access
        _ensure_tables_created()
    return _engine


def _ensure_tables_created() -> None:
    """Ensure all ORM tables are created (called automatically on first engine access)."""
    # Import ORM models so their metadata is registered on Base before create_all.
    from capstone_project_team_5.data.models import (  # noqa: F401
        artifact_source,
        code_analysis,
        consent_record,
        portfolio,
        portfolio_item,
        project,
        resume,
        upload_record,
        user,
        user_code_analysis,
        user_skill,
    )

    Base.metadata.create_all(bind=_engine)
    _run_migrations()


def _run_migrations() -> None:
    """Apply incremental schema changes to existing databases.

    Since the project uses create_all() (no Alembic), new columns on existing
    tables require explicit ALTER TABLE statements. Each migration is
    idempotent — failures (column already exists) are silently ignored.
    """
    inspector = inspect(_engine)

    # --- users table ---
    user_cols = [c["name"] for c in inspector.get_columns("users")]
    user_migrations = [
        (
            "tutorial_completed",
            "ALTER TABLE users ADD COLUMN tutorial_completed BOOLEAN NOT NULL DEFAULT 0",
        ),
        (
            "setup_completed",
            "ALTER TABLE users ADD COLUMN setup_completed BOOLEAN NOT NULL DEFAULT 0",
        ),
        ("setup_step", "ALTER TABLE users ADD COLUMN setup_step INTEGER NOT NULL DEFAULT 0"),
    ]
    for col, stmt in user_migrations:
        if col not in user_cols:
            with _engine.begin() as conn:
                conn.execute(text(stmt))

    # --- upload_records table ---
    upload_cols = [c["name"] for c in inspector.get_columns("upload_records")]
    if "user_id" not in upload_cols:
        with _engine.begin() as conn:
            conn.execute(text("ALTER TABLE upload_records ADD COLUMN user_id INTEGER"))

    # --- portfolios / portfolio_items tables ---
    portfolio_migrations = [
        "ALTER TABLE portfolios ADD COLUMN share_token TEXT UNIQUE",
        "ALTER TABLE portfolios ADD COLUMN template TEXT NOT NULL DEFAULT 'grid'",
        "ALTER TABLE portfolios ADD COLUMN color_theme TEXT NOT NULL DEFAULT 'dark'",
        "ALTER TABLE portfolios ADD COLUMN description TEXT",
        "ALTER TABLE portfolio_items ADD COLUMN is_text_block INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE portfolio_items ADD COLUMN display_order INTEGER NOT NULL DEFAULT 0",
    ]
    with _engine.connect() as conn:
        for stmt in portfolio_migrations:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                pass  # Column already exists


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
