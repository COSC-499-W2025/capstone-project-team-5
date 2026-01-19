"""
Module for creating and updating portfolio showcase items.
"""

from __future__ import annotations

from typing import Any

from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import User
from capstone_project_team_5.data.models.portfolio_item import PortfolioItem


def create_portfolio_item(
    *,
    username: str,
    project_id: int | None,
    title: str,
    content: dict[str, Any] | list[dict[str, Any]] | list[str],
) -> PortfolioItem:
    """Create and persist a new portfolio item for a user.

    Args:
        username: Username of the owner of this portfolio item.
        project_id: ID of the project this portfolio item is associated with
            (or ``None`` for a standalone item).
        title: Project or showcase name.
        content: Serializable structure describing the showcase details.
            Typical shapes include::

                {"bullets": [...], "summary": "...", "links": [...]}

            The value is JSON-encoded before being stored.

    Returns:
        The newly created :class:`PortfolioItem` instance with an assigned ID.

    Raises:
        ValueError: If the user with the given username does not exist.
    """
    import json

    encoded_content = json.dumps(content)

    with get_session() as session:
        user = session.query(User).filter(User.username == username).first()
        if user is None:
            msg = f"User '{username}' not found when creating portfolio item."
            raise ValueError(msg)

        item = PortfolioItem(
            project_id=project_id,
            user_id=user.id,
            title=title,
            content=encoded_content,
        )
        session.add(item)
        session.flush()
        session.refresh(item)
        return item


def get_latest_portfolio_item_for_project(project_id: int) -> PortfolioItem | None:
    """Return the most recently created portfolio item for a project.

    Args:
        project_id: ID of the project whose portfolio item should be fetched.

    Returns:
        The latest :class:`PortfolioItem` instance for the project, or ``None``
        if no items exist.
    """
    with get_session() as session:
        return (
            session.query(PortfolioItem)
            .filter(PortfolioItem.project_id == project_id)
            .order_by(PortfolioItem.created_at.desc())
            .first()
        )


def update_portfolio_item(
    *,
    item_id: int,
    title: str | None = None,
    content: dict[str, Any] | list[dict[str, Any]] | list[str] | None = None,
) -> PortfolioItem | None:
    """Update an existing portfolio item's title and/or content."""
    import json

    with get_session() as session:
        item = session.query(PortfolioItem).filter(PortfolioItem.id == item_id).first()
        if item is None:
            return None

        if title is not None:
            item.title = title

        if content is not None:
            item.content = json.dumps(content)

        session.flush()
        session.refresh(item)
        return item


__all__ = [
    "create_portfolio_item",
    "get_latest_portfolio_item_for_project",
    "update_portfolio_item",
]
