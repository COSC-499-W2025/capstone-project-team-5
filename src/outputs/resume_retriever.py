"""
Read-only retrieval helpers for previously generated resume items.

This module mirrors `portfolio_retriever.py` but targets the `ResumeItem`
table. It provides two convenience functions:
 - get(item_id) -> dict | None
 - list_all(limit=None) -> list[dict]

These functions deliberately do not provide write access.
"""

from .item_retriever import ItemRetriever

_retriever = ItemRetriever("GeneratedItem", kind="resume")


def get(item_id: int) -> dict | None:
    """Return a resume item by id (delegates to ItemRetriever)."""
    return _retriever.get(item_id)


def list_all(limit: int | None = None) -> list[dict]:
    """List resume items (delegates to ItemRetriever)."""
    return _retriever.list_all(limit)
