"""Tests for work experience and education API endpoints."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from capstone_project_team_5.api.main import app
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import Education, User, WorkExperience


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the API."""
    return TestClient(app)


@pytest.fixture
def test_user() -> Generator[tuple[str, int]]:
    """Create a test user in the database.

    Returns:
        tuple: (username, user_id)
    """
    username = "testuser_resume"

    # Clean up any existing data for this user
    with get_session() as session:
        user_ids = session.query(User.id).filter(User.username == username)
        session.query(WorkExperience).filter(WorkExperience.user_id.in_(user_ids)).delete(
            synchronize_session=False
        )
        session.query(Education).filter(Education.user_id.in_(user_ids)).delete(
            synchronize_session=False
        )
        session.query(User).filter(User.username == username).delete(synchronize_session=False)
        session.commit()

    # Create new user
    with get_session() as session:
        user = User(username=username, password_hash="test_hash")
        session.add(user)
        session.commit()
        session.refresh(user)
        user_id = user.id

    yield username, user_id

    # Cleanup
    with get_session() as session:
        session.query(WorkExperience).filter(WorkExperience.user_id == user_id).delete(
            synchronize_session=False
        )
        session.query(Education).filter(Education.user_id == user_id).delete(
            synchronize_session=False
        )
        session.query(User).filter(User.id == user_id).delete(synchronize_session=False)
        session.commit()


# ---- Work Experience Tests ----


class TestListWorkExperiences:
    """Tests for GET /api/users/{username}/work-experiences."""

    def test_list_empty(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.get(
            f"/api/users/{username}/work-experiences",
            headers={"X-Username": username},
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_list_returns_ordered(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        client.post(
            f"/api/users/{username}/work-experiences",
            json={"company": "Second", "title": "Dev", "rank": 2},
            headers={"X-Username": username},
        )
        client.post(
            f"/api/users/{username}/work-experiences",
            json={"company": "First", "title": "Dev", "rank": 1},
            headers={"X-Username": username},
        )
        response = client.get(
            f"/api/users/{username}/work-experiences",
            headers={"X-Username": username},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["company"] == "First"
        assert data[1]["company"] == "Second"

    def test_no_auth_returns_401(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.get(f"/api/users/{username}/work-experiences")
        assert response.status_code == 401

    def test_wrong_user_returns_403(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.get(
            f"/api/users/{username}/work-experiences",
            headers={"X-Username": "otheruser"},
        )
        assert response.status_code == 403


class TestCreateWorkExperience:
    """Tests for POST /api/users/{username}/work-experiences."""

    def test_create_minimal(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.post(
            f"/api/users/{username}/work-experiences",
            json={"company": "Google", "title": "SWE"},
            headers={"X-Username": username},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["company"] == "Google"
        assert data["title"] == "SWE"
        assert "id" in data

    def test_create_full(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.post(
            f"/api/users/{username}/work-experiences",
            json={
                "company": "Google",
                "title": "SWE",
                "location": "MTV",
                "start_date": "2020-06-01",
                "end_date": "2023-08-15",
                "description": "Built things",
                "is_current": False,
                "rank": 1,
            },
            headers={"X-Username": username},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["start_date"] == "2020-06-01"
        assert data["end_date"] == "2023-08-15"

    def test_create_invalid_dates_returns_400(
        self, client: TestClient, test_user: tuple[str, int]
    ) -> None:
        username, _ = test_user
        response = client.post(
            f"/api/users/{username}/work-experiences",
            json={
                "company": "Google",
                "title": "SWE",
                "start_date": "2023-01-01",
                "end_date": "2022-01-01",
            },
            headers={"X-Username": username},
        )
        assert response.status_code == 400

    def test_create_is_current_with_end_date_returns_400(
        self, client: TestClient, test_user: tuple[str, int]
    ) -> None:
        username, _ = test_user
        response = client.post(
            f"/api/users/{username}/work-experiences",
            json={
                "company": "Google",
                "title": "SWE",
                "is_current": True,
                "end_date": "2023-12-31",
            },
            headers={"X-Username": username},
        )
        assert response.status_code == 400


class TestGetWorkExperience:
    """Tests for GET /api/users/{username}/work-experiences/{id}."""

    def test_get_success(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        create_resp = client.post(
            f"/api/users/{username}/work-experiences",
            json={"company": "Google", "title": "SWE"},
            headers={"X-Username": username},
        )
        work_exp_id = create_resp.json()["id"]
        response = client.get(
            f"/api/users/{username}/work-experiences/{work_exp_id}",
            headers={"X-Username": username},
        )
        assert response.status_code == 200
        assert response.json()["company"] == "Google"

    def test_get_not_found(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.get(
            f"/api/users/{username}/work-experiences/9999",
            headers={"X-Username": username},
        )
        assert response.status_code == 404


class TestUpdateWorkExperience:
    """Tests for PATCH /api/users/{username}/work-experiences/{id}."""

    def test_partial_update(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        create_resp = client.post(
            f"/api/users/{username}/work-experiences",
            json={"company": "Original", "title": "Dev", "location": "NYC"},
            headers={"X-Username": username},
        )
        work_exp_id = create_resp.json()["id"]
        response = client.patch(
            f"/api/users/{username}/work-experiences/{work_exp_id}",
            json={"company": "Updated"},
            headers={"X-Username": username},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["company"] == "Updated"
        assert data["title"] == "Dev"
        assert data["location"] == "NYC"

    def test_update_not_found(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.patch(
            f"/api/users/{username}/work-experiences/9999",
            json={"company": "X"},
            headers={"X-Username": username},
        )
        assert response.status_code == 404

    def test_update_is_current_clears_end_date(
        self, client: TestClient, test_user: tuple[str, int]
    ) -> None:
        username, _ = test_user
        create_resp = client.post(
            f"/api/users/{username}/work-experiences",
            json={
                "company": "Google",
                "title": "SWE",
                "end_date": "2023-12-31",
            },
            headers={"X-Username": username},
        )
        work_exp_id = create_resp.json()["id"]
        response = client.patch(
            f"/api/users/{username}/work-experiences/{work_exp_id}",
            json={"is_current": True},
            headers={"X-Username": username},
        )
        assert response.status_code == 200
        assert response.json()["is_current"] is True
        assert response.json()["end_date"] is None


class TestDeleteWorkExperience:
    """Tests for DELETE /api/users/{username}/work-experiences/{id}."""

    def test_delete_success(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        create_resp = client.post(
            f"/api/users/{username}/work-experiences",
            json={"company": "ToDelete", "title": "X"},
            headers={"X-Username": username},
        )
        work_exp_id = create_resp.json()["id"]
        response = client.delete(
            f"/api/users/{username}/work-experiences/{work_exp_id}",
            headers={"X-Username": username},
        )
        assert response.status_code == 204

        # Verify it's gone
        get_resp = client.get(
            f"/api/users/{username}/work-experiences/{work_exp_id}",
            headers={"X-Username": username},
        )
        assert get_resp.status_code == 404

    def test_delete_not_found(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.delete(
            f"/api/users/{username}/work-experiences/9999",
            headers={"X-Username": username},
        )
        assert response.status_code == 404


# ---- Education Tests ----


class TestListEducations:
    """Tests for GET /api/users/{username}/educations."""

    def test_list_empty(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.get(
            f"/api/users/{username}/educations",
            headers={"X-Username": username},
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_list_returns_ordered(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        client.post(
            f"/api/users/{username}/educations",
            json={"institution": "Second U", "degree": "MSc", "rank": 2},
            headers={"X-Username": username},
        )
        client.post(
            f"/api/users/{username}/educations",
            json={"institution": "First U", "degree": "BSc", "rank": 1},
            headers={"X-Username": username},
        )
        response = client.get(
            f"/api/users/{username}/educations",
            headers={"X-Username": username},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["institution"] == "First U"
        assert data[1]["institution"] == "Second U"

    def test_no_auth_returns_401(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.get(f"/api/users/{username}/educations")
        assert response.status_code == 401

    def test_wrong_user_returns_403(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.get(
            f"/api/users/{username}/educations",
            headers={"X-Username": "otheruser"},
        )
        assert response.status_code == 403


class TestCreateEducation:
    """Tests for POST /api/users/{username}/educations."""

    def test_create_minimal(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.post(
            f"/api/users/{username}/educations",
            json={"institution": "UBC", "degree": "BSc"},
            headers={"X-Username": username},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["institution"] == "UBC"
        assert data["degree"] == "BSc"
        assert "id" in data

    def test_create_full(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.post(
            f"/api/users/{username}/educations",
            json={
                "institution": "UBC",
                "degree": "BSc",
                "field_of_study": "Computer Science",
                "gpa": 3.8,
                "start_date": "2020-09-01",
                "end_date": "2024-05-15",
                "is_current": False,
                "rank": 1,
            },
            headers={"X-Username": username},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["gpa"] == 3.8
        assert data["field_of_study"] == "Computer Science"

    def test_create_invalid_gpa_returns_400(
        self, client: TestClient, test_user: tuple[str, int]
    ) -> None:
        username, _ = test_user
        response = client.post(
            f"/api/users/{username}/educations",
            json={"institution": "UBC", "degree": "BSc", "gpa": 6.0},
            headers={"X-Username": username},
        )
        assert response.status_code == 400

    def test_create_invalid_dates_returns_400(
        self, client: TestClient, test_user: tuple[str, int]
    ) -> None:
        username, _ = test_user
        response = client.post(
            f"/api/users/{username}/educations",
            json={
                "institution": "UBC",
                "degree": "BSc",
                "start_date": "2024-01-01",
                "end_date": "2020-01-01",
            },
            headers={"X-Username": username},
        )
        assert response.status_code == 400

    def test_create_is_current_with_end_date_returns_400(
        self, client: TestClient, test_user: tuple[str, int]
    ) -> None:
        username, _ = test_user
        response = client.post(
            f"/api/users/{username}/educations",
            json={
                "institution": "UBC",
                "degree": "BSc",
                "is_current": True,
                "end_date": "2024-05-15",
            },
            headers={"X-Username": username},
        )
        assert response.status_code == 400


class TestGetEducation:
    """Tests for GET /api/users/{username}/educations/{id}."""

    def test_get_success(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        create_resp = client.post(
            f"/api/users/{username}/educations",
            json={"institution": "UBC", "degree": "BSc"},
            headers={"X-Username": username},
        )
        edu_id = create_resp.json()["id"]
        response = client.get(
            f"/api/users/{username}/educations/{edu_id}",
            headers={"X-Username": username},
        )
        assert response.status_code == 200
        assert response.json()["institution"] == "UBC"

    def test_get_not_found(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.get(
            f"/api/users/{username}/educations/9999",
            headers={"X-Username": username},
        )
        assert response.status_code == 404


class TestUpdateEducation:
    """Tests for PATCH /api/users/{username}/educations/{id}."""

    def test_partial_update(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        create_resp = client.post(
            f"/api/users/{username}/educations",
            json={"institution": "UBC", "degree": "BSc", "gpa": 3.5},
            headers={"X-Username": username},
        )
        edu_id = create_resp.json()["id"]
        response = client.patch(
            f"/api/users/{username}/educations/{edu_id}",
            json={"gpa": 3.9},
            headers={"X-Username": username},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["gpa"] == 3.9
        assert data["institution"] == "UBC"

    def test_update_not_found(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.patch(
            f"/api/users/{username}/educations/9999",
            json={"gpa": 4.0},
            headers={"X-Username": username},
        )
        assert response.status_code == 404

    def test_update_is_current_clears_end_date(
        self, client: TestClient, test_user: tuple[str, int]
    ) -> None:
        username, _ = test_user
        create_resp = client.post(
            f"/api/users/{username}/educations",
            json={
                "institution": "UBC",
                "degree": "BSc",
                "end_date": "2024-05-15",
            },
            headers={"X-Username": username},
        )
        edu_id = create_resp.json()["id"]
        response = client.patch(
            f"/api/users/{username}/educations/{edu_id}",
            json={"is_current": True},
            headers={"X-Username": username},
        )
        assert response.status_code == 200
        assert response.json()["is_current"] is True
        assert response.json()["end_date"] is None


class TestDeleteEducation:
    """Tests for DELETE /api/users/{username}/educations/{id}."""

    def test_delete_success(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        create_resp = client.post(
            f"/api/users/{username}/educations",
            json={"institution": "ToDelete", "degree": "BSc"},
            headers={"X-Username": username},
        )
        edu_id = create_resp.json()["id"]
        response = client.delete(
            f"/api/users/{username}/educations/{edu_id}",
            headers={"X-Username": username},
        )
        assert response.status_code == 204

        # Verify it's gone
        get_resp = client.get(
            f"/api/users/{username}/educations/{edu_id}",
            headers={"X-Username": username},
        )
        assert get_resp.status_code == 404

    def test_delete_not_found(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.delete(
            f"/api/users/{username}/educations/9999",
            headers={"X-Username": username},
        )
        assert response.status_code == 404
