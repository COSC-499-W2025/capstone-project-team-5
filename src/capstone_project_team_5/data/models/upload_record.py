"""ORM model for storing zip file upload metadata.

This module defines the ZipUploadRecord table that captures metadata
about successfully processed zip archives including filename, size,
and file count for audit and analytics purposes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from capstone_project_team_5.data.db import Base

if TYPE_CHECKING:
    from capstone_project_team_5.data.models.artifact_source import ArtifactSource
    from capstone_project_team_5.data.models.project import Project


class UploadRecord(Base):
    """Persisted metadata for processed zip uploads.

    Attributes:
        id: Auto-incrementing primary key.
        filename: Name of the uploaded zip file.
        size_bytes: Size of the zip file in bytes.
        file_count: Number of files extracted (excluding ignored patterns).
        created_at: UTC timestamp of when the upload was processed.
    """

    __tablename__ = "upload_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    projects: Mapped[list[Project]] = relationship(
        "Project", back_populates="upload", cascade="all, delete-orphan"
    )
    artifact_sources: Mapped[list[ArtifactSource]] = relationship(
        "ArtifactSource", back_populates="upload", cascade="all, delete-orphan"
    )
