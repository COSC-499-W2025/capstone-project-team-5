"""Association table linking users to code analysis snapshots.

Each row represents a single user running a specific CodeAnalysis.
This keeps the existing CodeAnalysis schema unchanged while allowing
per-user timelines and analytics.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from capstone_project_team_5.data.db import Base


class UserCodeAnalysis(Base):
    """Link between a User and a CodeAnalysis entry."""

    __tablename__ = "user_code_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    analysis_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("code_analyses.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
