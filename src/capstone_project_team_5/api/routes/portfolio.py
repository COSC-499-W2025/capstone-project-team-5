"""Portfolio editing routes for the API."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Response, status

from capstone_project_team_5.api.schemas.portfolio import (
    PortfolioAddItemRequest,
    PortfolioCreateRequest,
    PortfolioEditRequest,
    PortfolioItemResponse,
    PortfolioResponse,
)
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import Portfolio, PortfolioItem, Project, User

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
    "",
    response_model=PortfolioResponse,
    summary="Create a portfolio",
    description=(
        "Create a named portfolio for a user. A portfolio is a logical grouping of "
        "portfolio items for a user."
    ),
)
def create_portfolio(request: PortfolioCreateRequest) -> PortfolioResponse:
    """Create a new portfolio for the given user."""
    with get_session() as session:
        user = session.query(User).filter(User.username == request.username).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        portfolio = Portfolio(
            user_id=user.id,
            name=request.name,
        )
        session.add(portfolio)
        session.flush()
        session.refresh(portfolio)

        return PortfolioResponse(
            id=portfolio.id,
            name=portfolio.name,
            created_at=portfolio.created_at,
            updated_at=portfolio.updated_at,
        )


@router.get(
    "/user/{username}",
    response_model=list[PortfolioResponse],
    summary="List portfolios for a user",
    description="Return all portfolios belonging to the given username.",
)
def list_portfolios(username: str) -> list[PortfolioResponse]:
    """List all portfolios for a given user."""
    with get_session() as session:
        user = session.query(User).filter(User.username == username).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        portfolios = session.query(Portfolio).filter(Portfolio.user_id == user.id).all()

        return [
            PortfolioResponse(
                id=p.id,
                name=p.name,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in portfolios
        ]


@router.post(
    "/{portfolio_id}/items",
    response_model=PortfolioItemResponse,
    summary="Add project to portfolio",
    description=(
        "Ensure a portfolio item exists for the given user/project and attach it to the "
        "specified portfolio. If no item exists yet, one is created with default content."
    ),
)
def add_project_to_portfolio(
    portfolio_id: int,
    request: PortfolioAddItemRequest,
) -> PortfolioItemResponse:
    """Create or reuse a portfolio item for a project in a specific portfolio."""
    with get_session() as session:
        user = session.query(User).filter(User.username == request.username).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        portfolio = session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if portfolio is None or portfolio.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found for user.",
            )

        project = session.query(Project).filter(Project.id == request.project_id).first()
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found.",
            )

        # Try to find an existing item for this user/project/analysis/portfolio.
        query = (
            session.query(PortfolioItem)
            .filter(
                PortfolioItem.user_id == user.id,
                PortfolioItem.project_id == request.project_id,
                PortfolioItem.source_analysis_id == request.source_analysis_id,
                PortfolioItem.portfolio_id == portfolio_id,
            )
            .order_by(PortfolioItem.updated_at.desc())
        )
        item = query.first()

        if item is None:
            # Create a default item with minimal content.
            default_markdown = f"# {project.name}\n\n`{project.rel_path}`"
            encoded_content = json.dumps({"markdown": default_markdown})

            item = PortfolioItem(
                project_id=request.project_id,
                portfolio_id=portfolio_id,
                user_id=user.id,
                title=project.name,
                content=encoded_content,
                is_user_edited=False,
                source_analysis_id=request.source_analysis_id,
            )
            session.add(item)
            session.flush()
            session.refresh(item)

        markdown = _extract_markdown(item.content)

        return PortfolioItemResponse(
            id=item.id,
            project_id=item.project_id,
            title=item.title,
            markdown=markdown,
            is_user_edited=bool(item.is_user_edited),
            source_analysis_id=getattr(item, "source_analysis_id", None),
            portfolio_id=getattr(item, "portfolio_id", None),
            created_at=item.created_at,
            updated_at=item.updated_at,
        )


@router.get(
    "/{portfolio_id}",
    response_model=list[PortfolioItemResponse],
    summary="List items in a portfolio",
    description=(
        "Return all portfolio items (and their projects) contained in the specified portfolio."
    ),
)
def list_portfolio_items(portfolio_id: int) -> list[PortfolioItemResponse]:
    """List all portfolio items associated with a specific portfolio."""
    with get_session() as session:
        portfolio = session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if portfolio is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found.",
            )

        items = (
            session.query(PortfolioItem)
            .filter(PortfolioItem.portfolio_id == portfolio_id)
            .order_by(PortfolioItem.updated_at.desc())
            .all()
        )

        responses: list[PortfolioItemResponse] = []
        for item in items:
            markdown = _extract_markdown(item.content)
            responses.append(
                PortfolioItemResponse(
                    id=item.id,
                    project_id=item.project_id,
                    title=item.title,
                    markdown=markdown,
                    is_user_edited=bool(item.is_user_edited),
                    source_analysis_id=getattr(item, "source_analysis_id", None),
                    portfolio_id=getattr(item, "portfolio_id", None),
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                )
            )

        return responses


@router.delete(
    "/{portfolio_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a portfolio",
    description="Delete a portfolio and its associated portfolio items.",
)
def delete_portfolio(portfolio_id: int) -> Response:
    """Delete a portfolio by ID.

    Associated PortfolioItem rows are deleted via ORM cascade rules.
    """
    with get_session() as session:
        portfolio = session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if portfolio is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found.",
            )

        session.delete(portfolio)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


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

        query = session.query(PortfolioItem).filter(
            PortfolioItem.user_id == user.id,
            PortfolioItem.project_id == request.project_id,
            PortfolioItem.source_analysis_id == request.source_analysis_id,
        )
        if request.portfolio_id is None:
            query = query.filter(PortfolioItem.portfolio_id.is_(None))
        else:
            query = query.filter(PortfolioItem.portfolio_id == request.portfolio_id)

        item = query.order_by(PortfolioItem.updated_at.desc()).first()

        if item is None:
            item = PortfolioItem(
                project_id=request.project_id,
                portfolio_id=request.portfolio_id,
                user_id=user.id,
                title=request.title or project.name,
                content=encoded_content,
                is_user_edited=True,
                source_analysis_id=request.source_analysis_id,
            )
            session.add(item)
        else:
            item.title = request.title or project.name
            item.content = encoded_content
            item.portfolio_id = request.portfolio_id
            item.is_user_edited = True
            item.source_analysis_id = request.source_analysis_id

        session.flush()

        markdown = _extract_markdown(item.content)

        return PortfolioItemResponse(
            id=item.id,
            project_id=item.project_id,
            title=item.title,
            markdown=markdown,
            is_user_edited=bool(item.is_user_edited),
            source_analysis_id=getattr(item, "source_analysis_id", None),
            portfolio_id=getattr(item, "portfolio_id", None),
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
