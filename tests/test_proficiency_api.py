"""Tests for proficiency API endpoints."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from capstone_project_team_5.api.main import app
from capstone_project_team_5.constants.skill_detection_constants import SkillType
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import Skill, User
from tests.conftest import auth_headers


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def user_and_skill(api_db: None) -> tuple[str, int]:
    """Create a user and a skill; return (username, skill_id)."""
    uid = uuid.uuid4().hex[:8]
    with get_session() as session:
        user = User(username=f"u_{uid}", password_hash="x")
        session.add(user)
        session.flush()

        skill = Skill(name=f"Python_{uid}", skill_type=SkillType.TOOL)
        session.add(skill)
        session.flush()

        return user.username, skill.id


def test_patch_proficiency_sets_level(client: TestClient, user_and_skill: tuple[str, int]) -> None:
    """PATCH /api/skills/{id}/proficiency sets the proficiency level."""
    username, skill_id = user_and_skill
    resp = client.patch(
        f"/api/skills/{skill_id}/proficiency",
        json={"proficiency_level": "expert"},
        headers=auth_headers(username),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["proficiency_level"] == "expert"
    assert data["is_manual_override"] is True


def test_patch_proficiency_null_reverts_override(
    client: TestClient, user_and_skill: tuple[str, int]
) -> None:
    """PATCH with null proficiency_level clears manual override."""
    username, skill_id = user_and_skill

    # First set manually
    client.patch(
        f"/api/skills/{skill_id}/proficiency",
        json={"proficiency_level": "expert"},
        headers=auth_headers(username),
    )

    # Then revert
    resp = client.patch(
        f"/api/skills/{skill_id}/proficiency",
        json={"proficiency_level": None},
        headers=auth_headers(username),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_manual_override"] is False


def test_patch_proficiency_requires_auth(
    client: TestClient, user_and_skill: tuple[str, int]
) -> None:
    """PATCH without auth returns 401."""
    _, skill_id = user_and_skill
    resp = client.patch(
        f"/api/skills/{skill_id}/proficiency",
        json={"proficiency_level": "expert"},
    )
    assert resp.status_code == 401


def test_patch_proficiency_skill_not_found(client: TestClient, api_db: None) -> None:
    """PATCH for non-existent skill returns 404."""
    uid = uuid.uuid4().hex[:8]
    with get_session() as session:
        user = User(username=f"u_{uid}", password_hash="x")
        session.add(user)
        session.flush()

    resp = client.patch(
        "/api/skills/99999/proficiency",
        json={"proficiency_level": "expert"},
        headers=auth_headers(f"u_{uid}"),
    )
    assert resp.status_code == 404


def test_get_all_skills_includes_proficiency(
    client: TestClient, user_and_skill: tuple[str, int]
) -> None:
    """GET /api/skills/ includes proficiency when authenticated."""
    username, skill_id = user_and_skill

    # Set proficiency
    client.patch(
        f"/api/skills/{skill_id}/proficiency",
        json={"proficiency_level": "proficient"},
        headers=auth_headers(username),
    )

    resp = client.get("/api/skills/", headers=auth_headers(username))
    assert resp.status_code == 200
    items = resp.json()["items"]
    matched = [s for s in items if s["id"] == skill_id]
    assert len(matched) == 1
    assert matched[0]["proficiency_level"] == "proficient"
