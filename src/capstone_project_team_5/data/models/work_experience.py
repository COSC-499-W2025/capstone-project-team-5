"""WorkExperience model for storing user work history.

This model stores work experience entries for resume generation.
It has a 1:many relationship with the User model.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from capstone_project_team_5.data.db import Base

if TYPE_CHECKING:
    from capstone_project_team_5.data.models.user import User


class WorkExperience(Base):
    """Work experience entry for a user's resume.

    Attributes:
        id: Auto-incrementing primary key.
        user_id: Foreign key to users table.
        company: Name of the company/organization.
        title: Job title/position.
        location: Job location (city, state, or remote).
        start_date: Start date of employment.
        end_date: End date of employment (None if current).
        description: Brief description of the role.
        bullets: JSON array of bullet points describing responsibilities/achievements.
        is_current: Whether this is the user's current job.
        rank: User-defined ordering for resume display (lower = higher priority).
        updated_at: UTC timestamp when the record was last updated.
    """

    __tablename__ = "WorkExperience"
    __table_args__ = (CheckConstraint("rank >= 0", name="ck_workexperience_rank_positive"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    company: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    bullets: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="work_experiences")

    @validates("rank")
    def validate_rank(self, key: str, value: int) -> int:
        """Validate rank is non-negative."""
        if value < 0:
            raise ValueError("Rank must be non-negative")
        return value
