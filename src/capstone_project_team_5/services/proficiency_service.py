"""Service for computing and persisting skill proficiency levels."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from capstone_project_team_5.constants.skill_detection_constants import ProficiencyLevel
from capstone_project_team_5.data.models.code_analysis import CodeAnalysis
from capstone_project_team_5.data.models.project import Project
from capstone_project_team_5.data.models.skill import ProjectSkill
from capstone_project_team_5.data.models.user_code_analysis import UserCodeAnalysis
from capstone_project_team_5.data.models.user_skill import UserSkill


def _level_from_count(count: int) -> ProficiencyLevel:
    """Map project usage count to proficiency level."""
    if count >= 6:
        return ProficiencyLevel.EXPERT
    if count >= 4:
        return ProficiencyLevel.PROFICIENT
    if count >= 2:
        return ProficiencyLevel.INTERMEDIATE
    return ProficiencyLevel.BEGINNER


def compute_and_save_proficiency(
    session: Session,
    user_id: int,
) -> None:
    """Compute proficiency levels from project usage and upsert UserSkill rows.

    Counts distinct projects per skill for the user. Skips rows where
    ``is_manual_override`` is True.

    Args:
        session: Active SQLAlchemy session (caller manages commit).
        user_id: The user whose proficiencies to recompute.
    """
    # Get all project IDs owned by this user via UserCodeAnalysis → CodeAnalysis → Project
    user_project_ids_select = (
        session.query(Project.id)
        .join(CodeAnalysis, CodeAnalysis.project_id == Project.id)
        .join(UserCodeAnalysis, UserCodeAnalysis.analysis_id == CodeAnalysis.id)
        .filter(UserCodeAnalysis.user_id == user_id)
    )

    # Count projects per skill
    counts = (
        session.query(
            ProjectSkill.skill_id,
            func.count(func.distinct(ProjectSkill.project_id)).label("cnt"),
        )
        .filter(ProjectSkill.project_id.in_(user_project_ids_select))
        .group_by(ProjectSkill.skill_id)
        .all()
    )

    # Fetch existing UserSkill rows for this user
    existing = {us.skill_id: us for us in session.query(UserSkill).filter_by(user_id=user_id).all()}

    for skill_id, cnt in counts:
        level = _level_from_count(cnt)
        if skill_id in existing:
            us = existing[skill_id]
            if not us.is_manual_override:
                us.proficiency_level = level
        else:
            session.add(
                UserSkill(
                    user_id=user_id,
                    skill_id=skill_id,
                    proficiency_level=level,
                    is_manual_override=False,
                )
            )

    session.flush()
