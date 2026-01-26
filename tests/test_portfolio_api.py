from __future__ import annotations

import io
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi.testclient import TestClient

from capstone_project_team_5.api.main import app
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import User


def _create_zip_bytes(entries: list[tuple[str, bytes]]) -> bytes:
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for name, data in entries:
            archive.writestr(name, data)
    return buffer.getvalue()


def _create_user(username: str) -> None:
    with get_session() as session:
        user = User(username=username, password_hash="hash")
        session.add(user)
        session.commit()


def test_portfolio_edit_endpoint_creates_and_updates_item() -> None:
    client = TestClient(app)

    # Create a project via upload endpoint.
    zip_bytes = _create_zip_bytes(
        [
            ("proj/main.py", b"print('hello')\n"),
        ]
    )

    upload_response = client.post(
        "/api/projects/upload",
        files={"file": ("proj.zip", zip_bytes, "application/zip")},
    )
    assert upload_response.status_code == 201
    project_id = upload_response.json()["projects"][0]["id"]

    username = "editor"
    _create_user(username)

    # First edit (create portfolio item).
    first_response = client.post(
        "/api/portfolio/items",
        json={
            "username": username,
            "project_id": project_id,
            "title": "Edited Project",
            "markdown": "# First version",
            "source_analysis_id": None,
        },
    )
    assert first_response.status_code == 200
    first_data = first_response.json()
    assert first_data["project_id"] == project_id
    assert first_data["markdown"] == "# First version"
    assert first_data["is_user_edited"] is True

    item_id = first_data["id"]

    # Second edit (update same portfolio item).
    second_response = client.post(
        "/api/portfolio/items",
        json={
            "username": username,
            "project_id": project_id,
            "title": "Edited Project",
            "markdown": "# Second version",
            "source_analysis_id": None,
        },
    )
    assert second_response.status_code == 200
    second_data = second_response.json()
    assert second_data["id"] == item_id
    assert second_data["markdown"] == "# Second version"


def test_portfolio_edit_endpoint_missing_user_returns_404() -> None:
    client = TestClient(app)

    zip_bytes = _create_zip_bytes(
        [
            ("proj2/main.py", b"print('hello')\n"),
        ]
    )

    upload_response = client.post(
        "/api/projects/upload",
        files={"file": ("proj2.zip", zip_bytes, "application/zip")},
    )
    assert upload_response.status_code == 201
    project_id = upload_response.json()["projects"][0]["id"]

    response = client.post(
        "/api/portfolio/items",
        json={
            "username": "missing",
            "project_id": project_id,
            "title": "Should fail",
            "markdown": "# No user",
        },
    )
    assert response.status_code == 404
