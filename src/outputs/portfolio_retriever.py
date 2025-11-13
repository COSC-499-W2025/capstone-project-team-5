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
from typing import Any

from sqlalchemy import text

# Reuse application's DB infrastructure
from capstone_project_team_5.data.db import get_session


def _get_connection():
    """Return the module-level session context manager.

    This mirrors the helper pattern used in `ProjectSummary` and provides a
    single place to change session wiring for this module.
    """
    return get_session()


def get(item_id: int) -> dict[str, Any] | None:
    """Retrieve a portfolio item by its primary key from PortfolioItem table.

    Returns a dict with keys: id, project_id, title, content (deserialized),
    created_at, or None if the item does not exist.
    """
    with _get_connection() as session:
        sql = text("SELECT * FROM PortfolioItem WHERE id = :id")
        res = session.execute(sql, {"id": item_id})
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


def list_all(limit: int | None = None) -> list[dict[str, Any]]:
    """List stored portfolio items ordered by created_at DESC.

    If `limit` is provided only that many items are returned.
    """
    with _get_connection() as session:
        base_sql = "SELECT * FROM PortfolioItem ORDER BY created_at DESC"
        if limit is not None:
            sql = text(base_sql + " LIMIT :limit")
            res = session.execute(sql, {"limit": limit})
        else:
            res = session.execute(text(base_sql))

        items: list[dict[str, Any]] = []
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
