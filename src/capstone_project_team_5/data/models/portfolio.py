"""ORM model representing a logical portfolio grouping of portfolio items.

This table groups :class:`PortfolioItem` rows under a named portfolio for a
given user.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from capstone_project_team_5.data.db import Base

if TYPE_CHECKING:
    from capstone_project_team_5.data.models.portfolio_item import PortfolioItem
    from capstone_project_team_5.data.models.user import User


class Portfolio(Base):
    """Logical portfolio grouping for a user's portfolio items."""

    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    user: Mapped[User] = relationship("User", back_populates="portfolios")
    items: Mapped[list[PortfolioItem]] = relationship(
        "PortfolioItem",
        back_populates="portfolio",
        cascade="all, delete-orphan",
    )
