"""Tests for UserSkill ORM model."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from capstone_project_team_5.constants.skill_detection_constants import (
    ProficiencyLevel,
    SkillType,
)
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import Skill, User, UserSkill


def test_create_user_skill(api_db: None) -> None:
    """UserSkill row can be created with proficiency level."""
    uid = uuid.uuid4().hex[:8]
    with get_session() as session:
        user = User(username=f"u_{uid}", password_hash="x")
        session.add(user)
        session.flush()

        skill = Skill(name=f"Python_{uid}", skill_type=SkillType.TOOL)
        session.add(skill)
        session.flush()

        us = UserSkill(
            user_id=user.id,
            skill_id=skill.id,
            proficiency_level=ProficiencyLevel.EXPERT,
        )
        session.add(us)
        session.flush()

        assert us.id is not None
        assert us.proficiency_level == ProficiencyLevel.EXPERT


def test_user_skill_unique_constraint(api_db: None) -> None:
    """Duplicate (user_id, skill_id) raises IntegrityError."""
    uid = uuid.uuid4().hex[:8]
    with pytest.raises(IntegrityError), get_session() as session:
        user = User(username=f"u_{uid}", password_hash="x")
        session.add(user)
        session.flush()

        skill = Skill(name=f"Go_{uid}", skill_type=SkillType.TOOL)
        session.add(skill)
        session.flush()

        session.add(
            UserSkill(
                user_id=user.id,
                skill_id=skill.id,
                proficiency_level=ProficiencyLevel.BEGINNER,
            )
        )
        session.add(
            UserSkill(
                user_id=user.id,
                skill_id=skill.id,
                proficiency_level=ProficiencyLevel.EXPERT,
            )
        )
        session.flush()
