"""
Read-only retrieval helpers for previously generated portfolio items.

This module assumes a `PortfolioItem` table exists with the schema created by
the storage component. It provides two convenience functions:
 - get(item_id) -> Optional[dict]
 - list_all(limit=None) -> List[dict]

These functions deliberately do not provide write access.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, Connection

# Database URL environment variable (keeps module backend-agnostic)
DB_ENV_VAR = "DATABASE_URL"


def _get_engine() -> Engine:
    """Create and return a SQLAlchemy Engine using DATABASE_URL.

    Raises:
        RuntimeError: if DATABASE_URL is not set in the environment.
    """
    url = os.environ.get(DB_ENV_VAR)
    if not url:
        raise RuntimeError(f"Environment variable {DB_ENV_VAR} is not set")
    return create_engine(url)


def _get_conn() -> Connection:
    """Return a SQLAlchemy Connection. Caller must close it."""
    engine = _get_engine()
    return engine.connect()


def get(item_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve a portfolio item by id.

    Args:
        item_id: Primary key of the portfolio item.

    Returns:
        Optional[Dict[str, Any]]: Deserialized item (or None if not found).
    """
    conn: Connection = _get_conn()
    try:
        sql = text("SELECT * FROM PortfolioItem WHERE id = :id")
        res = conn.execute(sql, {"id": item_id})
        row = res.mappings().fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "project_id": row["project_id"],
            "title": row["title"],
            "content": json.loads(row["content"]),
            "created_at": row["created_at"],
        }
    finally:
        conn.close()


def list_all(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    List stored portfolio items in reverse chronological order.

    Args:
        limit: Optional maximum number of items to return.
    """
    conn: Connection = _get_conn()
    try:
        base_sql = "SELECT * FROM PortfolioItem ORDER BY created_at DESC"
        if limit is not None:
            sql = text(base_sql + " LIMIT :limit")
            res = conn.execute(sql, {"limit": limit})
        else:
            res = conn.execute(text(base_sql))

        items: List[Dict[str, Any]] = []
        for row in res.mappings().all():
            items.append(
                {
                    "id": row["id"],
                    "project_id": row["project_id"],
                    "title": row["title"],
                    "content": json.loads(row["content"]),
                    "created_at": row["created_at"],
                }
            )
        return items
    finally:
        conn.close()
