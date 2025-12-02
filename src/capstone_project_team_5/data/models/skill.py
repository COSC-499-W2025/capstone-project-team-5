"""ORM models for skills and project-skill associations.

This module defines the Skill and ProjectSkill tables for storing
detected tools and practices associated with projects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from capstone_project_team_5.constants.skill_detection_constants import SkillType
from capstone_project_team_5.data.db import Base

if TYPE_CHECKING:
    from capstone_project_team_5.data.models.project import Project


class Skill(Base):
    """A detected skill (tool or practice).

    Attributes:
        id: Auto-incrementing primary key.
        name: Unique name of the skill (e.g., "Git", "Unit Testing").
        skill_type: Type of skill - either 'tool' or 'practice'.
    """

    __tablename__ = "Skill"
    __table_args__ = (
        CheckConstraint("skill_type IN ('tool', 'practice')", name="ck_skill_type"),
        Index("ix_skill_type", "skill_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    skill_type: Mapped[SkillType] = mapped_column(String, nullable=False)

    # Relationship to projects through ProjectSkill
    project_skills: Mapped[list[ProjectSkill]] = relationship(
        "ProjectSkill", back_populates="skill", cascade="all, delete-orphan"
    )


class ProjectSkill(Base):
    """Many-to-many association between projects and skills.

    Attributes:
        id: Auto-incrementing primary key.
        project_id: Foreign key to the associated project.
        skill_id: Foreign key to the associated skill.
    """

    __tablename__ = "ProjectSkill"
    __table_args__ = (UniqueConstraint("project_id", "skill_id", name="uq_project_skill"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    skill_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("Skill.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="project_skills")
    skill: Mapped[Skill] = relationship("Skill", back_populates="project_skills")
