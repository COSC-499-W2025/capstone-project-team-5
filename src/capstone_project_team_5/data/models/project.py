"""ORM model representing discovered projects from uploads."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from capstone_project_team_5.data.db import Base

if TYPE_CHECKING:
    from capstone_project_team_5.data.models.upload_record import UploadRecord


class Project(Base):
    """Persisted metadata describing a discovered project within an upload."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    upload_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("upload_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    rel_path: Mapped[str] = mapped_column(String, nullable=False)
    has_git_repo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False)
    is_collaborative: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    upload: Mapped[UploadRecord] = relationship("UploadRecord", back_populates="projects")
