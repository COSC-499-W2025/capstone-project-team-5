"""Read-only retrieval helpers for previously generated portfolio items.

This module assumes a `PortfolioItem` table exists with the schema created by
the storage component. It provides two convenience functions:
 - get(item_id) -> Optional[dict]
 - list_all(limit=None) -> List[dict]

These functions deliberately do not provide write access.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "db" / "artifact_miner.db"


def _get_conn() -> sqlite3.Connection:
    """Open a SQLite connection configured for row access.

    Raises:
        FileNotFoundError: If the DB file does not exist at `DB_PATH`.
    """
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get(item_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a portfolio item by id.

    Args:
        item_id: Primary key of the portfolio item.

    Returns:
        Optional[Dict[str, Any]]: Deserialized item (or None if not found).
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM PortfolioItem WHERE id = ?", (item_id,))
        row = cur.fetchone()
        if not row:
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


def list_all(limit: int | None = None) -> List[Dict[str, Any]]:
    """List stored portfolio items in reverse chronological order.

    Args:
        limit: Optional maximum number of items to return.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        query = "SELECT * FROM PortfolioItem ORDER BY created_at DESC"
        if limit:
            query += " LIMIT ?"
            cur.execute(query, (limit,))
        else:
            cur.execute(query)
        rows = cur.fetchall()
        items: List[Dict[str, Any]] = []
        for row in rows:
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
