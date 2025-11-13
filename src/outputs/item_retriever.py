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
from typing import Any

from sqlalchemy import MetaData, Table, select

from capstone_project_team_5.data.db import get_session

# Simple cache for reflected Table objects keyed by (engine id, table name).
_TABLE_CACHE: dict[tuple[int, str], Table] = {}


def _get_table(name: str, bind) -> Table:
    key = (id(bind), name)
    if key in _TABLE_CACHE:
        return _TABLE_CACHE[key]
    md = MetaData()
    tbl = Table(name, md, autoload_with=bind)
    _TABLE_CACHE[key] = tbl
    return tbl


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
        with get_session() as session:
            engine = session.get_bind()
            table = _get_table(self.table_name, engine)
            if self.kind is not None:
                stmt = select(table).where(
                    table.c[self.id_col] == item_id, table.c.kind == self.kind
                )
            else:
                stmt = select(table).where(table.c[self.id_col] == item_id)

            res = session.execute(stmt)
            row = res.mappings().fetchone()
            if row is None:
                return None
            # Safely deserialize JSON content; if it's already a dict or
            # invalid JSON, fall back to the raw value stored in the DB.
            try:
                content = json.loads(row["content"])
            except (TypeError, json.JSONDecodeError):
                content = row["content"]

            return {
                "id": row["id"],
                "project_id": row["project_id"],
                "title": row["title"],
                "content": content,
                "created_at": row["created_at"],
            }

    def list_all(self, limit: int | None = None) -> list[dict[str, Any]]:
        """List rows ordered by created timestamp (descending)."""
        with get_session() as session:
            engine = session.get_bind()
            table = _get_table(self.table_name, engine)
            stmt = select(table)
            if self.kind is not None:
                stmt = stmt.where(table.c.kind == self.kind)
            stmt = stmt.order_by(table.c[self.created_col].desc())
            if limit is not None:
                stmt = stmt.limit(limit)

            res = session.execute(stmt)
            items: list[dict[str, Any]] = []
            for row in res.mappings().all():
                # Attempt to deserialize JSON content; on failure return raw value
                raw_content = row["content"]
                try:
                    content = json.loads(raw_content)
                except (TypeError, json.JSONDecodeError):
                    content = raw_content

                items.append(
                    {
                        "id": row["id"],
                        "project_id": row["project_id"],
                        "title": row["title"],
                        "content": content,
                        "created_at": row["created_at"],
                    }
                )
            return items
