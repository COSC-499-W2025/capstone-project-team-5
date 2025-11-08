"""Portfolio retriever convenience wrapper.

This module provides a tiny, stable public surface for retrieving previously
generated portfolio entries. It intentionally delegates to the shared
`ItemRetriever` implementation to avoid duplicating connection and
deserialization logic while keeping a discoverable module name for callers.

API
- get(item_id: int) -> dict | None
    Retrieve a single portfolio item by primary key. Returns a dictionary with
    keys: ``id``, ``project_id``, ``title``, ``content`` (deserialized JSON),
    and ``created_at``, or ``None`` if not found.

- list_all(limit: int | None = None) -> list[dict]
    Return a list of portfolio items ordered by ``created_at`` descending. If
    ``limit`` is provided, only that many items are returned.

Notes
- This wrapper preserves the historical import path
    ``outputs.portfolio_retriever`` so existing callers do not need to change.
- For shared retrieval logic see :mod:`outputs.item_retriever`.
"""

from .item_retriever import ItemRetriever


_retriever = ItemRetriever("GeneratedItem", kind="portfolio")


def get(item_id: int) -> dict | None:
    """Return a portfolio item by id (delegates to ItemRetriever)."""
    return _retriever.get(item_id)


def list_all(limit: int | None = None) -> list[dict]:
    """List portfolio items (delegates to ItemRetriever)."""
    return _retriever.list_all(limit)
