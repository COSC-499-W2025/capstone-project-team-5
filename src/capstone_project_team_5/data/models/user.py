"""User account model for authentication in the TUI.

This defines a minimal users table to support login / signup flows.
Passwords are stored as salted PBKDF2 hashes, never in plaintext.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from capstone_project_team_5.data.db import Base
from capstone_project_team_5.data.models.portfolio_item import PortfolioItem
from capstone_project_team_5.data.models.resume import Resume

if TYPE_CHECKING:
    from capstone_project_team_5.data.models.education import Education
    from capstone_project_team_5.data.models.portfolio import Portfolio
    from capstone_project_team_5.data.models.user_profile import UserProfile
    from capstone_project_team_5.data.models.work_experience import WorkExperience


class User(Base):
    """Application user account.

    Attributes:
        id: Auto-incrementing primary key.
        username: Unique handle used for login.
        password_hash: Salted hash of the user's password.
        created_at: UTC timestamp when the account was created.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    portfolio_items: Mapped[list[PortfolioItem]] = relationship(
        "PortfolioItem", back_populates="user", cascade="all, delete-orphan"
    )
    portfolios: Mapped[list[Portfolio]] = relationship(
        "Portfolio", back_populates="user", cascade="all, delete-orphan"
    )
    resumes: Mapped[list[Resume]] = relationship(
        "Resume", back_populates="user", cascade="all, delete-orphan"
    )
    profile: Mapped[UserProfile | None] = relationship(
        "UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    education_entries: Mapped[list[Education]] = relationship(
        "Education", back_populates="user", cascade="all, delete-orphan"
    )
    work_experiences: Mapped[list[WorkExperience]] = relationship(
        "WorkExperience", back_populates="user", cascade="all, delete-orphan"
    )
