"""Tests for skills API endpoints."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from capstone_project_team_5.api.main import app
from capstone_project_team_5.api.schemas.skills import DEFAULT_LIMIT, MAX_LIMIT
from capstone_project_team_5.constants.skill_detection_constants import SkillType
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import Project, ProjectSkill, Skill, UploadRecord

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    return TestClient(app)


def _get_or_create_skill(session: Session, name: str, skill_type: SkillType) -> Skill:
    """Get an existing skill or create a new one."""
    skill = session.query(Skill).filter(Skill.name == name).first()
    if skill is None:
        skill = Skill(name=name, skill_type=skill_type)
        session.add(skill)
        session.flush()
    return skill


@pytest.fixture
def project_with_skills(api_db: None) -> int:
    """Create a project with associated skills and return the project ID."""
    unique_id = uuid.uuid4().hex[:8]

    with get_session() as session:
        upload = UploadRecord(filename=f"test_{unique_id}.zip", size_bytes=100, file_count=1)
        session.add(upload)
        session.flush()

        project = Project(
            upload_id=upload.id,
            name=f"TestProject_{unique_id}",
            rel_path=f"test/path/{unique_id}",
            file_count=10,
        )
        session.add(project)
        session.flush()

        tool1 = _get_or_create_skill(session, f"Docker_{unique_id}", SkillType.TOOL)
        tool2 = _get_or_create_skill(session, f"Git_{unique_id}", SkillType.TOOL)
        practice1 = _get_or_create_skill(session, f"Unit Testing_{unique_id}", SkillType.PRACTICE)
        practice2 = _get_or_create_skill(session, f"CI/CD_{unique_id}", SkillType.PRACTICE)

        for skill in [tool1, tool2, practice1, practice2]:
            session.add(ProjectSkill(project_id=project.id, skill_id=skill.id))
        session.flush()

        return project.id


@pytest.fixture
def project_with_many_skills(api_db: None) -> int:
    """Create a project with many skills for pagination testing."""
    unique_id = uuid.uuid4().hex[:8]

    with get_session() as session:
        upload = UploadRecord(filename=f"many_{unique_id}.zip", size_bytes=100, file_count=1)
        session.add(upload)
        session.flush()

        project = Project(
            upload_id=upload.id,
            name=f"ManySkillsProject_{unique_id}",
            rel_path=f"many/path/{unique_id}",
            file_count=10,
        )
        session.add(project)
        session.flush()

        for i in range(5):
            tool = _get_or_create_skill(session, f"Tool_{i}_{unique_id}", SkillType.TOOL)
            practice = _get_or_create_skill(
                session, f"Practice_{i}_{unique_id}", SkillType.PRACTICE
            )
            session.add(ProjectSkill(project_id=project.id, skill_id=tool.id))
            session.add(ProjectSkill(project_id=project.id, skill_id=practice.id))

        session.flush()
        return project.id


@pytest.fixture
def project_without_skills(api_db: None) -> int:
    """Create a project without any skills and return the project ID."""
    unique_id = uuid.uuid4().hex[:8]

    with get_session() as session:
        upload = UploadRecord(filename=f"empty_{unique_id}.zip", size_bytes=50, file_count=1)
        session.add(upload)
        session.flush()

        project = Project(
            upload_id=upload.id,
            name=f"EmptyProject_{unique_id}",
            rel_path=f"empty/path/{unique_id}",
            file_count=5,
        )
        session.add(project)
        session.flush()

        return project.id


def test_get_project_skills_returns_all_skills(
    client: TestClient, project_with_skills: int
) -> None:
    """Test that GET /projects/{id}/skills returns all tools and practices with counts."""
    response = client.get(f"/api/projects/{project_with_skills}/skills/")

    assert response.status_code == 200
    data = response.json()

    assert data["project_id"] == project_with_skills
    assert len(data["tools"]) == 2
    assert len(data["practices"]) == 2
    assert data["tools_count"] == 2
    assert data["practices_count"] == 2


def test_get_project_skills_empty_and_not_found(
    client: TestClient, project_without_skills: int
) -> None:
    """Test empty project returns empty arrays and non-existent project returns 404."""
    # Empty project
    response = client.get(f"/api/projects/{project_without_skills}/skills/")
    assert response.status_code == 200
    data = response.json()
    assert data["tools"] == []
    assert data["practices"] == []
    assert data["tools_count"] == 0

    # Not found
    response = client.get("/api/projects/99999/skills/")
    assert response.status_code == 404


def test_get_project_tools_paginated_response(client: TestClient, project_with_skills: int) -> None:
    """Test that GET /projects/{id}/skills/tools returns paginated response."""
    response = client.get(f"/api/projects/{project_with_skills}/skills/tools")

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "pagination" in data
    assert len(data["items"]) == 2
    assert data["pagination"]["total"] == 2
    assert data["pagination"]["limit"] == DEFAULT_LIMIT
    assert data["pagination"]["has_more"] is False

    for tool in data["items"]:
        assert tool["skill_type"] == "tool"


def test_get_project_tools_pagination_params(
    client: TestClient, project_with_many_skills: int
) -> None:
    """Test pagination through multiple pages for tools endpoint."""
    # First page
    response = client.get(f"/api/projects/{project_with_many_skills}/skills/tools?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["pagination"]["total"] == 5
    assert data["pagination"]["has_more"] is True

    # Last page
    response = client.get(f"/api/projects/{project_with_many_skills}/skills/tools?limit=2&offset=4")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["pagination"]["has_more"] is False


def test_get_project_tools_empty_and_not_found(
    client: TestClient, project_without_skills: int
) -> None:
    """Test empty tools and 404 for non-existent project."""
    response = client.get(f"/api/projects/{project_without_skills}/skills/tools")
    assert response.status_code == 200
    assert response.json()["items"] == []

    response = client.get("/api/projects/99999/skills/tools")
    assert response.status_code == 404


def test_get_project_tools_invalid_pagination_params(
    client: TestClient, project_with_skills: int
) -> None:
    """Test that invalid pagination parameters return 422."""
    assert (
        client.get(
            f"/api/projects/{project_with_skills}/skills/tools?limit={MAX_LIMIT + 1}"
        ).status_code
        == 422
    )
    assert (
        client.get(f"/api/projects/{project_with_skills}/skills/tools?limit=0").status_code == 422
    )
    assert (
        client.get(f"/api/projects/{project_with_skills}/skills/tools?offset=-1").status_code == 422
    )


def test_get_project_practices_paginated_response(
    client: TestClient, project_with_skills: int
) -> None:
    """Test that GET /projects/{id}/skills/practices returns paginated response."""
    response = client.get(f"/api/projects/{project_with_skills}/skills/practices")

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "pagination" in data
    assert len(data["items"]) == 2
    assert data["pagination"]["total"] == 2
    assert data["pagination"]["has_more"] is False

    for practice in data["items"]:
        assert practice["skill_type"] == "practice"


def test_get_project_practices_empty_and_not_found(
    client: TestClient, project_without_skills: int
) -> None:
    """Test empty practices and 404 for non-existent project."""
    response = client.get(f"/api/projects/{project_without_skills}/skills/practices")
    assert response.status_code == 200
    assert response.json()["items"] == []

    response = client.get("/api/projects/99999/skills/practices")
    assert response.status_code == 404


# --- Global skills endpoint tests ---


@pytest.fixture
def skills_in_db(api_db: None) -> tuple[list[int], list[int]]:
    """Create skills not associated with any project. Returns (tool_ids, practice_ids)."""
    unique_id = uuid.uuid4().hex[:8]

    with get_session() as session:
        tools = [
            _get_or_create_skill(session, f"GlobalTool_{i}_{unique_id}", SkillType.TOOL)
            for i in range(3)
        ]
        practices = [
            _get_or_create_skill(session, f"GlobalPractice_{i}_{unique_id}", SkillType.PRACTICE)
            for i in range(2)
        ]
        session.flush()
        return [t.id for t in tools], [p.id for p in practices]


def test_get_all_skills_returns_paginated_response(
    client: TestClient, skills_in_db: tuple[list[int], list[int]]
) -> None:
    """Test that GET /api/skills returns a paginated response with items and pagination keys."""
    response = client.get("/api/skills")
    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "pagination" in data
    assert isinstance(data["items"], list)
    assert data["pagination"]["total"] >= 5  # at least the 5 skills we created
    assert data["pagination"]["limit"] == DEFAULT_LIMIT
    assert data["pagination"]["offset"] == 0

    for item in data["items"]:
        assert "id" in item
        assert "name" in item
        assert "skill_type" in item


def test_get_all_skills_filter_by_type(
    client: TestClient, skills_in_db: tuple[list[int], list[int]]
) -> None:
    """Test that skill_type query param correctly filters results."""
    tools_resp = client.get("/api/skills?skill_type=tool")
    assert tools_resp.status_code == 200
    tools_data = tools_resp.json()
    for item in tools_data["items"]:
        assert item["skill_type"] == "tool"

    practices_resp = client.get("/api/skills?skill_type=practice")
    assert practices_resp.status_code == 200
    practices_data = practices_resp.json()
    for item in practices_data["items"]:
        assert item["skill_type"] == "practice"


def test_get_all_skills_pagination_params(
    client: TestClient, skills_in_db: tuple[list[int], list[int]]
) -> None:
    """Test limit and offset pagination on the global skills endpoint."""
    # Get total count first
    total = client.get("/api/skills").json()["pagination"]["total"]

    # First page
    resp = client.get("/api/skills?limit=2&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["pagination"]["limit"] == 2
    assert data["pagination"]["offset"] == 0
    assert data["pagination"]["has_more"] is (total > 2)

    # Offset past the end
    resp = client.get(f"/api/skills?limit=2&offset={total}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["pagination"]["has_more"] is False


def test_get_all_skills_invalid_params(client: TestClient, api_db: None) -> None:
    """Test that invalid pagination params return 422."""
    assert client.get(f"/api/skills?limit={MAX_LIMIT + 1}").status_code == 422
    assert client.get("/api/skills?limit=0").status_code == 422
    assert client.get("/api/skills?offset=-1").status_code == 422
