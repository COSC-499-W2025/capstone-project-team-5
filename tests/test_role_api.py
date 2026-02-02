"""Tests for project role information in project endpoints."""

from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

from fastapi.testclient import TestClient

from capstone_project_team_5.api.main import app


def _create_zip_bytes(entries: list[tuple[str, bytes]]) -> bytes:
    """Helper to create a ZIP file in memory."""
    buffer = BytesIO()
    with ZipFile(buffer, "w") as zf:
        for name, content in entries:
            zf.writestr(name, content)
    return buffer.getvalue()


def _upload_single_project(client: TestClient, name: str) -> int:
    """Helper to upload a simple project and return its ID."""
    zip_bytes = _create_zip_bytes([(f"{name}/main.py", b"print('hello')\n")])
    response = client.post(
        "/api/projects/upload",
        files={"file": (f"{name}.zip", zip_bytes, "application/zip")},
    )
    assert response.status_code == 201
    return response.json()["projects"][0]["id"]


def test_get_project_includes_role_fields() -> None:
    """Test GET /api/projects/{id} includes role and contribution fields."""
    client = TestClient(app)
    project_id = _upload_single_project(client, "test_no_role")

    response = client.get(f"/api/projects/{project_id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == project_id
    assert "user_role" in payload
    assert "user_contribution_percentage" in payload
    assert payload["user_role"] is None
    assert payload["user_contribution_percentage"] is None


def test_patch_project_set_role() -> None:
    """Test PATCH /api/projects/{id} can set user role."""
    client = TestClient(app)
    project_id = _upload_single_project(client, "test_set_role")

    # Set the role via PATCH
    response = client.patch(
        f"/api/projects/{project_id}",
        json={"user_role": "Lead Developer", "user_contribution_percentage": 85.5},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["user_role"] == "Lead Developer"
    assert payload["user_contribution_percentage"] == 85.5

    # Verify via GET endpoint
    get_response = client.get(f"/api/projects/{project_id}")
    assert get_response.status_code == 200
    get_payload = get_response.json()
    assert get_payload["user_role"] == "Lead Developer"
    assert get_payload["user_contribution_percentage"] == 85.5


def test_patch_project_update_role() -> None:
    """Test PATCH /api/projects/{id} can update existing role."""
    client = TestClient(app)
    project_id = _upload_single_project(client, "test_update_role")

    # Set initial role
    initial_response = client.patch(
        f"/api/projects/{project_id}",
        json={"user_role": "Contributor", "user_contribution_percentage": 25.0},
    )
    assert initial_response.status_code == 200
    initial_payload = initial_response.json()
    assert initial_payload["user_role"] == "Contributor"
    assert initial_payload["user_contribution_percentage"] == 25.0

    # Update to new role
    response = client.patch(
        f"/api/projects/{project_id}",
        json={"user_role": "Team Lead", "user_contribution_percentage": 90.0},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["user_role"] == "Team Lead"
    assert payload["user_contribution_percentage"] == 90.0


def test_patch_project_clear_role() -> None:
    """Test PATCH /api/projects/{id} can clear role by setting to None."""
    client = TestClient(app)
    project_id = _upload_single_project(client, "test_clear_role")

    # Set a role
    setup_response = client.patch(
        f"/api/projects/{project_id}",
        json={"user_role": "Developer"},
    )
    assert setup_response.status_code == 200
    setup_payload = setup_response.json()
    assert setup_payload["user_role"] == "Developer"

    # Clear the role
    response = client.patch(
        f"/api/projects/{project_id}",
        json={"user_role": None, "user_contribution_percentage": None},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["user_role"] is None
    assert payload["user_contribution_percentage"] is None


def test_list_projects_includes_role() -> None:
    """Test GET /api/projects returns role fields in project summaries."""
    client = TestClient(app)
    project_id = _upload_single_project(client, "test_summary_role")

    # Set a role
    setup_response = client.patch(
        f"/api/projects/{project_id}",
        json={"user_role": "Backend Developer", "user_contribution_percentage": 60.0},
    )
    assert setup_response.status_code == 200
    setup_payload = setup_response.json()
    assert setup_payload["user_role"] == "Backend Developer"
    assert setup_payload["user_contribution_percentage"] == 60.0

    # List all projects
    response = client.get("/api/projects")
    assert response.status_code == 200
    projects = response.json()

    # Find our project
    project = next((p for p in projects if p["id"] == project_id), None)
    assert project is not None
    assert project["user_role"] == "Backend Developer"
    assert project["user_contribution_percentage"] == 60.0
