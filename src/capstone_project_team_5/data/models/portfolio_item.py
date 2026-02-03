"""ORM model for storing generated portfolio items (résumé entries, summaries).

This module defines the PortfolioItem table that captures generated insights
and reports about projects, which can be deleted without affecting the
underlying project data.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from capstone_project_team_5.data.db import Base

if TYPE_CHECKING:
    from capstone_project_team_5.data.models import User
    from capstone_project_team_5.data.models.portfolio import Portfolio
    from capstone_project_team_5.data.models.project import Project


class PortfolioItem(Base):
    """Persisted portfolio item (generated insight or report).

    Attributes:
        id: Auto-incrementing primary key.
        project_id: Foreign key to the associated project (nullable, SET NULL on delete).
        portfolio_id: Optional foreign key to a logical portfolio grouping.
        user_id: Foreign key to the user who owns this portfolio item.
        title: Title of the portfolio item.
        content: Text content of the portfolio item.
        is_user_edited: If content has been edited by user or not.
        is_showcase: Whether this is a featured portfolio item.
        source_analysis_id: Optional reference to CodeAnalysis that generated this.
        created_at: UTC timestamp of when the item was created.
        updated_at: UTC timestamp of when the item was last modified.
    """

    __tablename__ = "portfolio_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    project_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    portfolio_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("portfolios.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    is_user_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_showcase: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    source_analysis_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("code_analyses.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    project: Mapped[Project | None] = relationship("Project", back_populates="portfolio_items")
    portfolio: Mapped[Portfolio | None] = relationship("Portfolio", back_populates="items")
    user: Mapped[User] = relationship("User", back_populates="portfolio_items")
