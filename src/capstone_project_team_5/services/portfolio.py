from datetime import UTC, datetime

from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import PortfolioItem, User


def save_portfolio_item(
    username: str,
    project_id: int,
    title: str,
    content: str,
    is_user_edited: bool = False,
    source_analysis_id: int | None = None,
) -> bool:
    """Save or update a portfolio item for a user's project.

    Args:
        username: Username of the user saving the portfolio item
        project_id: ID of the project this portfolio item is for
        title: Title of the portfolio item
        content: Markdown content of the portfolio item
        is_user_edited: Whether this content has been edited by the user
        source_analysis_id: Optional ID of the source CodeAnalysis

    Returns:
        True if saved successfully, False otherwise
    """

    try:
        with get_session() as session:
            user = session.query(User).filter(User.username == username).first()

            if not user:
                return False

            existing = (
                session.query(PortfolioItem)
                .filter(PortfolioItem.project_id == project_id, PortfolioItem.user_id == user.id)
                .first()
            )

            if existing:
                existing.title = title
                existing.content = content
                existing.is_user_edited = is_user_edited
                existing.source_analysis_id = source_analysis_id
                existing.updated_at = datetime.now(UTC)
            else:
                new_item = PortfolioItem(
                    project_id=project_id,
                    user_id=user.id,
                    title=title,
                    content=content,
                    is_user_edited=is_user_edited,
                    source_analysis_id=source_analysis_id,
                )
                session.add(new_item)

            session.commit()
            return True
    except Exception:
        return False


def get_portfolio_item(username: str, project_id: int) -> dict | None:
    """Get a user's portfolio item for a project.

    Args:
        username: Username of the user
        project_id: ID of the project

    Returns:
        Dictionary with portfolio item data, or None if not found
    """

    try:
        with get_session() as session:
            user = session.query(User).filter(User.username == username).first()

            if not user:
                return None

            item = (
                session.query(PortfolioItem)
                .filter(PortfolioItem.project_id == project_id, PortfolioItem.user_id == user.id)
                .first()
            )

            if item:
                return {
                    "id": item.id,
                    "title": item.title,
                    "content": item.content,
                    "is_user_edited": item.is_user_edited,
                    "source_analysis_id": item.source_analysis_id,
                    "created_at": item.created_at,
                    "updated_at": item.updated_at,
                }
            return None

    except Exception:
        return None
