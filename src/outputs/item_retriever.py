"""
Generic item retriever for simple read-only access to DB-backed items.

This class is parameterized by a table name and exposes a small API:
 - get(item_id) -> dict | None
 - list_all(limit=None) -> list[dict]

Thin wrappers (portfolio_retriever, resume_retriever) can instantiate this
class to avoid duplicating connection and deserialization logic.
"""

from __future__ import annotations

import json
import os
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

# Environment variable used to locate the DB URL (SQLAlchemy connection string)
DB_ENV_VAR = "DATABASE_URL"


def _get_engine() -> Engine:
    """Return a SQLAlchemy Engine using the URL found in the environment.

    Raises:
        RuntimeError: if the environment variable is not set.
    """
    url = os.environ.get(DB_ENV_VAR)
    if not url:
        raise RuntimeError(f"Environment variable {DB_ENV_VAR} is not set")
    return create_engine(url)


def _get_conn() -> Connection:
    """Open and return a SQLAlchemy Connection. Caller must close it."""
    engine = _get_engine()
    return engine.connect()


class ItemRetriever:
    """Read-only retriever for a simple DB table containing JSON 'content'.

    Args:
        table_name: DB table to query (e.g. "PortfolioItem").
        id_col: Primary key column name (defaults to "id").
        created_col: Timestamp column used for ordering (defaults to "created_at").
    """

    def __init__(
        self,
        table_name: str,
        id_col: str = "id",
        created_col: str = "created_at",
        kind: str | None = None,
    ):
        self.table_name = table_name
        self.id_col = id_col
        self.created_col = created_col
        # Optional kind value used to scope queries (e.g. 'portfolio' or 'resume')
        self.kind = kind

    def get(self, item_id: int) -> dict[str, Any] | None:
        """Retrieve a single row by primary key and deserialize the `content` JSON."""
        conn = _get_conn()
        try:
            if self.kind is not None:
                sql = text(
                    f"SELECT * FROM {self.table_name} WHERE {self.id_col} = :id AND kind = :kind"
                )
                res = conn.execute(sql, {"id": item_id, "kind": self.kind})
            else:
                sql = text(f"SELECT * FROM {self.table_name} WHERE {self.id_col} = :id")
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

    def list_all(self, limit: int | None = None) -> list[dict[str, Any]]:
        """List rows ordered by created timestamp (descending)."""
        conn = _get_conn()
        try:
            if self.kind is not None:
                base_sql = f"SELECT * FROM {self.table_name} WHERE kind = :kind ORDER BY {self.created_col} DESC"
                if limit is not None:
                    sql = text(base_sql + " LIMIT :limit")
                    res = conn.execute(sql, {"kind": self.kind, "limit": limit})
                else:
                    res = conn.execute(text(base_sql), {"kind": self.kind})
            else:
                base_sql = f"SELECT * FROM {self.table_name} ORDER BY {self.created_col} DESC"
                if limit is not None:
                    sql = text(base_sql + " LIMIT :limit")
                    res = conn.execute(sql, {"limit": limit})
                else:
                    res = conn.execute(text(base_sql))

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
        finally:
            conn.close()
