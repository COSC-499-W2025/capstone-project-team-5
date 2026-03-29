"""ORM model for user-skill proficiency associations."""

from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from capstone_project_team_5.constants.skill_detection_constants import ProficiencyLevel
from capstone_project_team_5.data.db import Base


class UserSkill(Base):
    """Per-user proficiency level for a skill.

    Attributes:
        id: Auto-incrementing primary key.
        user_id: Foreign key to the user.
        skill_id: Foreign key to the skill.
        proficiency_level: One of expert/proficient/intermediate/beginner.
    """

    __tablename__ = "UserSkill"
    __table_args__ = (
        UniqueConstraint("user_id", "skill_id", name="uq_user_skill"),
        CheckConstraint(
            "proficiency_level IN ('expert', 'proficient', 'intermediate', 'beginner')",
            name="ck_proficiency_level",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    skill_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("Skill.id", ondelete="CASCADE"),
        nullable=False,
    )
    proficiency_level: Mapped[ProficiencyLevel] = mapped_column(String, nullable=False)

    user = relationship("User")
    skill = relationship("Skill")
