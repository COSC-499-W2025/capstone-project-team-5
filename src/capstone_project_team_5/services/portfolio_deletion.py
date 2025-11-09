"""Service module for deleting portfolio items (generated insights/reports).

This module provides functions to delete previously generated portfolio items
(résumé entries, project summaries) without affecting the underlying project
data or artifacts that may be shared across multiple reports.
"""

from __future__ import annotations

from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models.portfolio_item import PortfolioItem


def delete_portfolio_item(item_id: int) -> bool:
    """Delete a specific portfolio item by ID.

    This removes only the generated portfolio entry, not the underlying
    project or artifact data that may be used by other portfolio items.

    Args:
        item_id: Primary key of the portfolio item to delete.

    Returns:
        bool: True if the item was deleted, False if it didn't exist.
    """
    with get_session() as session:
        item = session.query(PortfolioItem).filter(PortfolioItem.id == item_id).first()
        if item is None:
            return False

        session.delete(item)
        return True


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
    with get_session() as session:
        items = session.query(PortfolioItem).filter(PortfolioItem.project_id == project_id).all()
        count = len(items)

        for item in items:
            session.delete(item)

        return count


def clear_all_portfolio_items() -> int:
    """Delete all portfolio items from the database.

    This removes all generated portfolio entries but preserves all project
    and artifact data. Projects, artifacts, and other database records remain
    intact and can be used to generate new portfolio items in the future.

    Returns:
        int: The number of portfolio items deleted.
    """
    with get_session() as session:
        items = session.query(PortfolioItem).all()
        count = len(items)

        for item in items:
            session.delete(item)

        return count
