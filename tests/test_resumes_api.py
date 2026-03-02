"""Tests for resume API endpoints."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from capstone_project_team_5.api.main import app
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import Project, UploadRecord, User
from capstone_project_team_5.data.models.resume import Resume


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
    username = "testuser_resumes"

    # Clean up any existing data for this user
    with get_session() as session:
        user = session.query(User).filter(User.username == username).first()
        if user:
            resumes = session.query(Resume).filter(Resume.user_id == user.id).all()
            for r in resumes:
                session.delete(r)
            session.flush()
            session.delete(user)
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
        resumes = session.query(Resume).filter(Resume.user_id == user_id).all()
        for r in resumes:
            session.delete(r)
        session.flush()
        session.query(User).filter(User.id == user_id).delete(synchronize_session=False)
        session.commit()


@pytest.fixture
def test_project(test_user: tuple[str, int]) -> Generator[int]:
    """Create an UploadRecord + Project for resume tests.

    Yields:
        int: The project ID.
    """
    with get_session() as session:
        upload = UploadRecord(filename="test.zip", size_bytes=1024, file_count=5)
        session.add(upload)
        session.flush()

        project = Project(
            upload_id=upload.id,
            name="Test Project",
            rel_path="test-project",
            has_git_repo=False,
            file_count=5,
        )
        session.add(project)
        session.commit()
        session.refresh(project)
        project_id = project.id
        upload_id = upload.id

    yield project_id

    # Cleanup
    with get_session() as session:
        session.query(Project).filter(Project.id == project_id).delete(synchronize_session=False)
        session.query(UploadRecord).filter(UploadRecord.id == upload_id).delete(
            synchronize_session=False
        )
        session.commit()


# ---- Helper to create a resume project via the API ----


def _create_resume(
    client: TestClient,
    username: str,
    project_id: int,
    *,
    title: str = "My Resume Project",
    description: str = "A cool project",
    bullet_points: list[str] | None = None,
    analysis_snapshot: list[str] | None = None,
) -> dict:
    """Helper to POST a resume project and return the JSON response."""
    payload: dict = {
        "project_id": project_id,
        "title": title,
        "description": description,
    }
    if bullet_points is not None:
        payload["bullet_points"] = bullet_points
    if analysis_snapshot is not None:
        payload["analysis_snapshot"] = analysis_snapshot
    resp = client.post(
        f"/api/users/{username}/resumes",
        json=payload,
        headers={"X-Username": username},
    )
    return resp.json()


# ---- List Resumes ----


class TestListResumes:
    """Tests for GET /api/users/{username}/resumes."""

    def test_list_empty(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.get(
            f"/api/users/{username}/resumes",
            headers={"X-Username": username},
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_list_returns_projects(
        self,
        client: TestClient,
        test_user: tuple[str, int],
        test_project: int,
    ) -> None:
        username, _ = test_user
        _create_resume(client, username, test_project, title="Listed Project")
        response = client.get(
            f"/api/users/{username}/resumes",
            headers={"X-Username": username},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Listed Project"

    def test_no_auth_returns_401(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.get(f"/api/users/{username}/resumes")
        assert response.status_code == 401

    def test_wrong_user_returns_403(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.get(
            f"/api/users/{username}/resumes",
            headers={"X-Username": "otheruser"},
        )
        assert response.status_code == 403


# ---- Get Resume ----


class TestGetResume:
    """Tests for GET /api/users/{username}/resumes/{project_id}."""

    def test_get_success(
        self,
        client: TestClient,
        test_user: tuple[str, int],
        test_project: int,
    ) -> None:
        username, _ = test_user
        _create_resume(
            client,
            username,
            test_project,
            title="Get Me",
            description="desc",
            bullet_points=["bullet1", "bullet2"],
            analysis_snapshot=["Python", "Flask"],
        )
        response = client.get(
            f"/api/users/{username}/resumes/{test_project}",
            headers={"X-Username": username},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Get Me"
        assert data["description"] == "desc"
        assert data["bullet_points"] == ["bullet1", "bullet2"]
        assert data["analysis_snapshot"] == ["Python", "Flask"]
        assert data["project_id"] == test_project
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_get_not_found(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.get(
            f"/api/users/{username}/resumes/9999",
            headers={"X-Username": username},
        )
        assert response.status_code == 404

    def test_no_auth_returns_401(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.get(f"/api/users/{username}/resumes/1")
        assert response.status_code == 401

    def test_wrong_user_returns_403(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.get(
            f"/api/users/{username}/resumes/1",
            headers={"X-Username": "otheruser"},
        )
        assert response.status_code == 403


# ---- Create Resume ----


class TestCreateResume:
    """Tests for POST /api/users/{username}/resumes."""

    def test_create_minimal(
        self,
        client: TestClient,
        test_user: tuple[str, int],
        test_project: int,
    ) -> None:
        username, _ = test_user
        response = client.post(
            f"/api/users/{username}/resumes",
            json={"project_id": test_project, "title": "Minimal"},
            headers={"X-Username": username},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Minimal"
        assert data["project_id"] == test_project
        assert "id" in data

    def test_create_full(
        self,
        client: TestClient,
        test_user: tuple[str, int],
        test_project: int,
    ) -> None:
        username, _ = test_user
        response = client.post(
            f"/api/users/{username}/resumes",
            json={
                "project_id": test_project,
                "title": "Full Resume",
                "description": "A web app",
                "bullet_points": ["Built REST API", "Wrote tests"],
                "analysis_snapshot": ["Python", "FastAPI", "SQLAlchemy"],
            },
            headers={"X-Username": username},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Full Resume"
        assert data["description"] == "A web app"
        assert data["bullet_points"] == ["Built REST API", "Wrote tests"]
        assert data["analysis_snapshot"] == ["Python", "FastAPI", "SQLAlchemy"]

    def test_create_upserts(
        self,
        client: TestClient,
        test_user: tuple[str, int],
        test_project: int,
    ) -> None:
        username, _ = test_user
        # First create
        _create_resume(client, username, test_project, title="First Version")
        # Second create with same project_id should upsert
        response = client.post(
            f"/api/users/{username}/resumes",
            json={
                "project_id": test_project,
                "title": "Second Version",
                "bullet_points": ["Updated bullet"],
            },
            headers={"X-Username": username},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Second Version"
        assert data["bullet_points"] == ["Updated bullet"]

        # Verify only one resume project exists for this project_id
        list_resp = client.get(
            f"/api/users/{username}/resumes",
            headers={"X-Username": username},
        )
        assert len(list_resp.json()) == 1

    def test_create_invalid_project_returns_400(
        self,
        client: TestClient,
        test_user: tuple[str, int],
    ) -> None:
        username, _ = test_user
        response = client.post(
            f"/api/users/{username}/resumes",
            json={"project_id": 999999, "title": "Bad Project"},
            headers={"X-Username": username},
        )
        assert response.status_code == 400

    def test_no_auth_returns_401(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.post(
            f"/api/users/{username}/resumes",
            json={"project_id": 1, "title": "No Auth"},
        )
        assert response.status_code == 401

    def test_wrong_user_returns_403(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.post(
            f"/api/users/{username}/resumes",
            json={"project_id": 1, "title": "Wrong User"},
            headers={"X-Username": "otheruser"},
        )
        assert response.status_code == 403


# ---- Update Resume ----


class TestUpdateResume:
    """Tests for PATCH /api/users/{username}/resumes/{project_id}."""

    def test_update_title_only(
        self,
        client: TestClient,
        test_user: tuple[str, int],
        test_project: int,
    ) -> None:
        username, _ = test_user
        _create_resume(
            client,
            username,
            test_project,
            title="Original",
            description="Keep me",
            bullet_points=["b1"],
        )
        response = client.patch(
            f"/api/users/{username}/resumes/{test_project}",
            json={"title": "Updated Title"},
            headers={"X-Username": username},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["description"] == "Keep me"
        assert data["bullet_points"] == ["b1"]

    def test_update_bullets_only(
        self,
        client: TestClient,
        test_user: tuple[str, int],
        test_project: int,
    ) -> None:
        username, _ = test_user
        _create_resume(
            client,
            username,
            test_project,
            title="Keep Title",
            description="Keep Desc",
            bullet_points=["old bullet"],
        )
        response = client.patch(
            f"/api/users/{username}/resumes/{test_project}",
            json={"bullet_points": ["new bullet 1", "new bullet 2"]},
            headers={"X-Username": username},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Keep Title"
        assert data["description"] == "Keep Desc"
        assert data["bullet_points"] == ["new bullet 1", "new bullet 2"]

    def test_update_not_found(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.patch(
            f"/api/users/{username}/resumes/9999",
            json={"title": "Nope"},
            headers={"X-Username": username},
        )
        assert response.status_code == 404

    def test_update_save_failure_returns_400(
        self,
        client: TestClient,
        test_user: tuple[str, int],
        test_project: int,
    ) -> None:
        username, _ = test_user
        _create_resume(client, username, test_project, title="Original")

        with patch("capstone_project_team_5.api.routes.resumes.save_resume", return_value=False):
            response = client.patch(
                f"/api/users/{username}/resumes/{test_project}",
                json={"title": "Will Fail"},
                headers={"X-Username": username},
            )

        assert response.status_code == 400
        assert (
            response.json()["detail"]
            == "Failed to update resume. Check that the project_id is valid."
        )

    def test_no_auth_returns_401(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.patch(
            f"/api/users/{username}/resumes/1",
            json={"title": "No Auth"},
        )
        assert response.status_code == 401

    def test_wrong_user_returns_403(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.patch(
            f"/api/users/{username}/resumes/1",
            json={"title": "Wrong User"},
            headers={"X-Username": "otheruser"},
        )
        assert response.status_code == 403


# ---- Delete Resume ----


class TestDeleteResume:
    """Tests for DELETE /api/users/{username}/resumes/{project_id}."""

    def test_delete_success(
        self,
        client: TestClient,
        test_user: tuple[str, int],
        test_project: int,
    ) -> None:
        username, _ = test_user
        _create_resume(client, username, test_project, title="To Delete")
        response = client.delete(
            f"/api/users/{username}/resumes/{test_project}",
            headers={"X-Username": username},
        )
        assert response.status_code == 204

        # Verify it's gone
        get_resp = client.get(
            f"/api/users/{username}/resumes/{test_project}",
            headers={"X-Username": username},
        )
        assert get_resp.status_code == 404

    def test_delete_not_found(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.delete(
            f"/api/users/{username}/resumes/9999",
            headers={"X-Username": username},
        )
        assert response.status_code == 404

    def test_no_auth_returns_401(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.delete(f"/api/users/{username}/resumes/1")
        assert response.status_code == 401

    def test_wrong_user_returns_403(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.delete(
            f"/api/users/{username}/resumes/1",
            headers={"X-Username": "otheruser"},
        )
        assert response.status_code == 403


# ---- Generate Resume PDF ----


class TestGenerateResumePdf:
    """Tests for POST /api/users/{username}/resumes/generate."""

    def test_generate_no_profile_returns_404(
        self,
        client: TestClient,
        test_user: tuple[str, int],
    ) -> None:
        username, _ = test_user
        with patch(
            "capstone_project_team_5.api.routes.resumes.generate_resume_pdf",
            return_value=None,
        ):
            response = client.post(
                f"/api/users/{username}/resumes/generate",
                json={"template_name": "jake"},
                headers={"X-Username": username},
            )
        assert response.status_code == 404

    def test_generate_success(
        self,
        client: TestClient,
        test_user: tuple[str, int],
        tmp_path: Path,
    ) -> None:
        username, _ = test_user
        # Create a fake PDF file
        fake_pdf = tmp_path / "resume.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake content")

        def mock_generate(username, output_path, template_name="jake", **kwargs):
            # Copy the fake PDF to the expected output location
            import shutil

            dest = Path(f"{output_path}.pdf")
            shutil.copy(fake_pdf, dest)
            return dest

        with patch(
            "capstone_project_team_5.api.routes.resumes.generate_resume_pdf",
            side_effect=mock_generate,
        ):
            response = client.post(
                f"/api/users/{username}/resumes/generate",
                json={"template_name": "jake"},
                headers={"X-Username": username},
            )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"

    def test_generate_compiler_not_found(
        self,
        client: TestClient,
        test_user: tuple[str, int],
    ) -> None:
        username, _ = test_user
        with patch(
            "capstone_project_team_5.api.routes.resumes.generate_resume_pdf",
            side_effect=FileNotFoundError("pdflatex not found"),
        ):
            response = client.post(
                f"/api/users/{username}/resumes/generate",
                json={"template_name": "jake"},
                headers={"X-Username": username},
            )
        assert response.status_code == 502

    def test_no_auth_returns_401(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.post(
            f"/api/users/{username}/resumes/generate",
            json={"template_name": "jake"},
        )
        assert response.status_code == 401

    def test_wrong_user_returns_403(self, client: TestClient, test_user: tuple[str, int]) -> None:
        username, _ = test_user
        response = client.post(
            f"/api/users/{username}/resumes/generate",
            json={"template_name": "jake"},
            headers={"X-Username": "otheruser"},
        )
        assert response.status_code == 403
