"""Portfolio editing routes for the API."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, status

from capstone_project_team_5.api.schemas.portfolio import (
    PortfolioEditRequest,
    PortfolioItemResponse,
)
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import PortfolioItem, Project, User
from capstone_project_team_5.services.portfolio import save_portfolio_item

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def _extract_markdown(content: str) -> str:
    """Extract markdown text from stored portfolio content."""
    try:
        decoded = json.loads(content)
    except Exception:
        decoded = content

    if isinstance(decoded, dict):
        markdown = decoded.get("markdown")
        if isinstance(markdown, str) and markdown.strip():
            return markdown
        return ""

    if isinstance(decoded, str) and decoded.strip():
        return decoded

    return ""


@router.post(
    "/items",
    response_model=PortfolioItemResponse,
    summary="Create or update a portfolio item",
    description=(
        "Create or update a portfolio item for a project and optional analysis. "
        "Content is stored as markdown and associated with the given username."
    ),
)
def upsert_portfolio_item(request: PortfolioEditRequest) -> PortfolioItemResponse:
    """Create or update a portfolio item for the given user and project."""
    with get_session() as session:
        project = session.query(Project).filter(Project.id == request.project_id).first()
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found.",
            )

        user = session.query(User).filter(User.username == request.username).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

    encoded_content = json.dumps({"markdown": request.markdown})
    saved = save_portfolio_item(
        username=request.username,
        project_id=request.project_id,
        title=request.title or project.name,
        content=encoded_content,
        is_user_edited=True,
        is_showcase=request.is_showcase,
        source_analysis_id=request.source_analysis_id,
    )
    if not saved:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save portfolio item.",
        )

    with get_session() as session:
        user = session.query(User).filter(User.username == request.username).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        item = (
            session.query(PortfolioItem)
            .filter(
                PortfolioItem.user_id == user.id,
                PortfolioItem.project_id == request.project_id,
            )
            .order_by(PortfolioItem.updated_at.desc())
            .first()
        )

        if item is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Portfolio item not found after save.",
            )

        markdown = _extract_markdown(item.content)

        return PortfolioItemResponse(
            id=item.id,
            project_id=item.project_id,
            title=item.title,
            markdown=markdown,
            is_user_edited=bool(item.is_user_edited),
            is_showcase=bool(item.is_showcase),
            source_analysis_id=getattr(item, "source_analysis_id", None),
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
