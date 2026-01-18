"""User account model for authentication in the TUI.

This defines a minimal users table to support login / signup flows.
Passwords are stored as salted PBKDF2 hashes, never in plaintext.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from capstone_project_team_5.data.db import Base
from capstone_project_team_5.data.models.portfolio_item import PortfolioItem


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
