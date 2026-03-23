"""Tests for tutorial status API endpoints."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from conftest import auth_headers
from fastapi.testclient import TestClient

from capstone_project_team_5.api.main import app
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import User


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def test_user() -> Generator[tuple[str, int]]:
    username = "tutorialuser"

    with get_session() as session:
        session.query(User).filter(User.username == username).delete(synchronize_session=False)
        session.commit()

    with get_session() as session:
        user = User(username=username, password_hash="test_hash")
        session.add(user)
        session.commit()
        session.refresh(user)
        user_id = user.id

    yield username, user_id

    with get_session() as session:
        session.query(User).filter(User.username == username).delete(synchronize_session=False)


def test_get_tutorial_status_default_false(client: TestClient, test_user: tuple[str, int]) -> None:
    username, _ = test_user
    resp = client.get("/api/users/me/tutorial-status", headers=auth_headers(username))
    assert resp.status_code == 200
    assert resp.json() == {"completed": False}


def test_get_tutorial_status_unauthenticated(client: TestClient) -> None:
    resp = client.get("/api/users/me/tutorial-status")
    assert resp.status_code in (401, 403)


def test_update_tutorial_status(client: TestClient, test_user: tuple[str, int]) -> None:
    username, _ = test_user
    headers = auth_headers(username)

    resp = client.patch(
        "/api/users/me/tutorial-status",
        json={"completed": True},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json() == {"completed": True}

    resp = client.get("/api/users/me/tutorial-status", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == {"completed": True}


def test_update_tutorial_status_idempotent(client: TestClient, test_user: tuple[str, int]) -> None:
    username, _ = test_user
    headers = auth_headers(username)

    client.patch("/api/users/me/tutorial-status", json={"completed": True}, headers=headers)
    resp = client.patch(
        "/api/users/me/tutorial-status",
        json={"completed": True},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json() == {"completed": True}


def test_update_tutorial_status_invalid_body(
    client: TestClient, test_user: tuple[str, int]
) -> None:
    username, _ = test_user
    resp = client.patch(
        "/api/users/me/tutorial-status",
        json={"completed": "not_a_bool"},
        headers=auth_headers(username),
    )
    assert resp.status_code == 422


def test_me_response_unchanged(client: TestClient, test_user: tuple[str, int]) -> None:
    """Ensure /api/users/me does not leak tutorial_completed."""
    username, _ = test_user
    resp = client.get("/api/users/me", headers=auth_headers(username))
    assert resp.status_code == 200
    data = resp.json()
    assert "tutorial_completed" not in data
    assert "id" in data
    assert "username" in data
