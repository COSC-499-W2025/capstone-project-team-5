from __future__ import annotations

import io
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi.testclient import TestClient

from capstone_project_team_5.api.main import app
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import Portfolio, User


def _create_zip_bytes(entries: list[tuple[str, bytes]]) -> bytes:
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for name, data in entries:
            archive.writestr(name, data)
    return buffer.getvalue()


def _create_user(username: str) -> None:
    with get_session() as session:
        user = session.query(User).filter(User.username == username).first()
        if user is None:
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

    # Create a portfolio to attach items to.
    portfolio_resp = client.post(
        "/api/portfolio",
        json={
            "username": username,
            "name": "Editing Portfolio",
        },
    )
    assert portfolio_resp.status_code == 200
    portfolio_id = portfolio_resp.json()["id"]

    # First edit (create portfolio item).
    first_response = client.post(
        "/api/portfolio/items",
        json={
            "username": username,
            "project_id": project_id,
            "title": "Edited Project",
            "markdown": "# First version",
            "source_analysis_id": None,
            "portfolio_id": portfolio_id,
        },
    )
    assert first_response.status_code == 200
    first_data = first_response.json()
    assert first_data["project_id"] == project_id
    assert first_data["markdown"] == "# First version"
    assert first_data["is_user_edited"] is True
    assert first_data["portfolio_id"] == portfolio_id

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
            "portfolio_id": portfolio_id,
        },
    )
    assert second_response.status_code == 200
    second_data = second_response.json()
    assert second_data["id"] == item_id
    assert second_data["markdown"] == "# Second version"
    assert second_data["portfolio_id"] == portfolio_id


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


def test_create_and_list_portfolios() -> None:
    client = TestClient(app)

    username = "portfolio-user"
    _create_user(username)

    # Initially, user may or may not have portfolios depending on prior tests;
    # we only assert that creating a new one adds to the list.

    # Create a new portfolio.
    create_resp = client.post(
        "/api/portfolio",
        json={
            "username": username,
            "name": "My Showcase Portfolio",
        },
    )
    assert create_resp.status_code == 200
    created = create_resp.json()
    assert created["name"] == "My Showcase Portfolio"
    portfolio_id = created["id"]

    # Listing again should include the created portfolio.
    list_resp = client.get(f"/api/portfolio/user/{username}")
    assert list_resp.status_code == 200
    portfolios = list_resp.json()
    matching = [p for p in portfolios if p["id"] == portfolio_id]
    assert matching
    assert matching[0]["name"] == "My Showcase Portfolio"

    # Ensure it's persisted in the DB.
    with get_session() as session:
        stored = session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        assert stored is not None
        assert stored.name == "My Showcase Portfolio"


def test_delete_portfolio() -> None:
    client = TestClient(app)

    username = "delete-portfolio-user"
    _create_user(username)

    # Create a portfolio to delete.
    create_resp = client.post(
        "/api/portfolio",
        json={
            "username": username,
            "name": "Temporary Portfolio",
        },
    )
    assert create_resp.status_code == 200
    portfolio_id = create_resp.json()["id"]

    # Delete the portfolio.
    delete_resp = client.delete(f"/api/portfolio/{portfolio_id}")
    assert delete_resp.status_code == 204

    # Ensure it no longer appears in the user's portfolio list.
    list_resp = client.get(f"/api/portfolio/user/{username}")
    assert list_resp.status_code == 200
    portfolios = list_resp.json()
    assert all(p["id"] != portfolio_id for p in portfolios)
