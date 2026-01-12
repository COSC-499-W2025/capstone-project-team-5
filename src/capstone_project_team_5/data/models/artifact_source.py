"""ORM model for tracking artifact sources across incremental uploads."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from capstone_project_team_5.data.db import Base

if TYPE_CHECKING:
    from capstone_project_team_5.data.models.project import Project
    from capstone_project_team_5.data.models.upload_record import UploadRecord


class ArtifactSource(Base):
    """Tracks which upload contributed which artifacts to a project.

    This enables incremental uploads where multiple ZIP files contribute
    artifacts to the same project. For example, a user can upload an initial
    portfolio ZIP, then later upload additional project files to the same
    portfolio project.

    Attributes:
        id: Auto-incrementing primary key.
        project_id: Foreign key to the Project.
        upload_id: Foreign key to the UploadRecord that contributed artifacts.
        artifact_count: Number of artifacts added in this upload contribution.
        created_at: UTC timestamp when this record was created.
    """

    __tablename__ = "artifact_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    upload_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("upload_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    artifact_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    project: Mapped[Project] = relationship("Project", back_populates="artifact_sources")
    upload: Mapped[UploadRecord] = relationship("UploadRecord", back_populates="artifact_sources")
