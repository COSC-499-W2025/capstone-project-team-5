"""Education model for storing user educational history.

This model stores education entries for resume generation.
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


class Education(Base):
    """Education entry for a user's resume.

    Attributes:
        id: Auto-incrementing primary key.
        user_id: Foreign key to users table.
        institution: Name of school/university.
        degree: Degree type (e.g., Bachelor of Science, Master of Arts).
        field_of_study: Major/field of study.
        gpa: Grade point average.
        start_date: Start date of education.
        end_date: End date of education (None if current).
        achievements: JSON array of achievements, honors, or activities.
        is_current: Whether the user is currently enrolled.
        rank: User-defined ordering for resume display (lower = higher priority).
        updated_at: UTC timestamp when the record was last updated.
    """

    __tablename__ = "Education"
    __table_args__ = (CheckConstraint("rank >= 0", name="ck_education_rank_positive"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    institution: Mapped[str] = mapped_column(String(255), nullable=False)
    degree: Mapped[str] = mapped_column(String(255), nullable=False)
    field_of_study: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gpa: Mapped[float | None] = mapped_column(nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    achievements: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="education_entries")

    @validates("rank")
    def validate_rank(self, key: str, value: int) -> int:
        """Validate rank is non-negative."""
        if value < 0:
            raise ValueError("Rank must be non-negative")
        return value
