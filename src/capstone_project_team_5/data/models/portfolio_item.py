"""ORM model for storing generated portfolio items (résumé entries, summaries).

This module defines the PortfolioItem table that captures generated insights
and reports about projects, which can be deleted without affecting the
underlying project data.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from capstone_project_team_5.data.db import Base

if TYPE_CHECKING:
    from capstone_project_team_5.data.models.project import Project


class PortfolioItem(Base):
    """Persisted portfolio item (generated insight or report).

    Attributes:
        id: Auto-incrementing primary key.
        project_id: Foreign key to the associated project (nullable, SET NULL on delete).
        title: Title of the portfolio item.
        content: JSON or text content of the portfolio item.
        created_at: UTC timestamp of when the item was created.
    """

    __tablename__ = "portfolio_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    project: Mapped[Project | None] = relationship("Project", back_populates="portfolio_items")
