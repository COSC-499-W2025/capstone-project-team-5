from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from capstone_project_team_5.data.db import Base

if TYPE_CHECKING:
    from capstone_project_team_5.data.models import User
    from capstone_project_team_5.data.models.project import Project


class Resume(Base):
    """
    A collection of resume projects for a user.
    """

    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="My Resume")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="resumes")
    resume_projects: Mapped[list[ResumeProject]] = relationship(
        "ResumeProject", back_populates="resume", cascade="all, delete-orphan"
    )


class ResumeProject(Base):
    """
    Stores relevant resume information derived from a given project.
    """

    __tablename__ = "resume_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resume_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )

    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Stores snapshot of key analysis such as practices and tools (stored as JSON string)
    analysis_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    resume: Mapped[Resume] = relationship("Resume", back_populates="resume_projects")
    project: Mapped[Project] = relationship("Project")
    bullet_points: Mapped[list[ResumeBulletPoint]] = relationship(
        "ResumeBulletPoint", back_populates="resume_project", cascade="all, delete-orphan"
    )


class ResumeBulletPoint(Base):
    """
    Individual bullet points for a resume project.
    """

    __tablename__ = "resume_bullet_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resume_project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("resume_projects.id", ondelete="CASCADE"), nullable=False
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    resume_project: Mapped[ResumeProject] = relationship(
        "ResumeProject", back_populates="bullet_points"
    )
