"""ORM model for storing language-specific code analysis results.

This module defines the CodeAnalysis table that captures detailed metrics
from static code analysis (C/C++, Python, Java, etc.) for projects.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from capstone_project_team_5.data.db import Base

if TYPE_CHECKING:
    from capstone_project_team_5.data.models.project import Project


class CodeAnalysis(Base):
    """Persisted code analysis results for a project.

    Attributes:
        id: Auto-incrementing primary key.
        project_id: Foreign key to the associated project.
        language: Programming language analyzed (e.g., "C/C++", "Python", "Java").
        analysis_type: Type of analysis performed (e.g., "local", "ast", "tree-sitter").
        metrics_json: JSON string containing language-specific metrics.
        summary_text: Human-readable summary of the analysis.
        created_at: UTC timestamp of when the analysis was performed.
    """

    __tablename__ = "code_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    language: Mapped[str] = mapped_column(String, nullable=False)
    analysis_type: Mapped[str] = mapped_column(String, nullable=False, default="local")
    metrics_json: Mapped[str] = mapped_column(Text, nullable=False)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    project: Mapped[Project] = relationship("Project", back_populates="code_analyses")
