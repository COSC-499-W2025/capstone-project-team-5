"""Service module for deleting portfolio items (generated insights/reports).

This module provides functions to delete previously generated portfolio items
(résumé entries, project summaries) without affecting the underlying project
data or artifacts that may be shared across multiple reports.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


def _get_db_path() -> Path:
    """Get the path to the artifact_miner database."""
    base_dir = Path(__file__).resolve().parents[3]
    return base_dir / "db" / "artifact_miner.db"


def _get_connection() -> sqlite3.Connection:
    """Open a connection to the artifact_miner database."""
    db_path = _get_db_path()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def delete_portfolio_item(item_id: int) -> bool:
    """Delete a specific portfolio item by ID.

    This removes only the generated portfolio entry, not the underlying
    project or artifact data that may be used by other portfolio items.

    Args:
        item_id: Primary key of the portfolio item to delete.

    Returns:
        bool: True if the item was deleted, False if it didn't exist.
    """
    conn = _get_connection()
    try:
        cur = conn.cursor()

        # Check if the item exists
        cur.execute("SELECT id FROM PortfolioItem WHERE id = ?", (item_id,))
        if cur.fetchone() is None:
            return False

        # Delete the portfolio item
        cur.execute("DELETE FROM PortfolioItem WHERE id = ?", (item_id,))
        conn.commit()
        return True
    finally:
        conn.close()


def delete_portfolio_items_by_project(project_id: int) -> int:
    """Delete all portfolio items for a specific project.

    This removes all generated portfolio entries associated with a project,
    but preserves the project data and artifacts themselves, which may be
    referenced by other portfolio items or reports.

    Args:
        project_id: ID of the project whose portfolio items should be deleted.

    Returns:
        int: The number of portfolio items deleted.
    """
    conn = _get_connection()
    try:
        cur = conn.cursor()

        # Count items before deletion
        cur.execute("SELECT COUNT(*) FROM PortfolioItem WHERE project_id = ?", (project_id,))
        count = cur.fetchone()[0]

        # Delete all portfolio items for this project
        if count > 0:
            cur.execute("DELETE FROM PortfolioItem WHERE project_id = ?", (project_id,))
            conn.commit()

        return count
    finally:
        conn.close()


def clear_all_portfolio_items() -> int:
    """Delete all portfolio items from the database.

    This removes all generated portfolio entries but preserves all project
    and artifact data. Projects, artifacts, and other database records remain
    intact and can be used to generate new portfolio items in the future.

    Returns:
        int: The number of portfolio items deleted.
    """
    conn = _get_connection()
    try:
        cur = conn.cursor()

        # Count items before deletion
        cur.execute("SELECT COUNT(*) FROM PortfolioItem")
        count = cur.fetchone()[0]

        # Delete all portfolio items
        if count > 0:
            cur.execute("DELETE FROM PortfolioItem")
            conn.commit()

        return count
    finally:
        conn.close()
