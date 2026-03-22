"""Tests for setup wizard status API endpoints."""

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
    username = "setupuser"

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


def test_get_setup_status_default(client: TestClient, test_user: tuple[str, int]) -> None:
    username, _ = test_user
    resp = client.get("/api/users/me/setup-status", headers=auth_headers(username))
    assert resp.status_code == 200
    assert resp.json() == {"completed": False, "step": 0}


def test_get_setup_status_unauthenticated(client: TestClient) -> None:
    resp = client.get("/api/users/me/setup-status")
    assert resp.status_code in (401, 403)


def test_update_setup_step(client: TestClient, test_user: tuple[str, int]) -> None:
    username, _ = test_user
    headers = auth_headers(username)

    resp = client.patch(
        "/api/users/me/setup-status",
        json={"step": 3},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["step"] == 3
    assert data["completed"] is False


def test_update_setup_completed(client: TestClient, test_user: tuple[str, int]) -> None:
    username, _ = test_user
    headers = auth_headers(username)

    resp = client.patch(
        "/api/users/me/setup-status",
        json={"completed": True},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["completed"] is True


def test_update_setup_partial(client: TestClient, test_user: tuple[str, int]) -> None:
    """PATCH with only step should not affect completed."""
    username, _ = test_user
    headers = auth_headers(username)

    client.patch("/api/users/me/setup-status", json={"completed": True}, headers=headers)

    resp = client.patch(
        "/api/users/me/setup-status",
        json={"step": 5},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["step"] == 5
    assert data["completed"] is True


def test_update_setup_step_validation(client: TestClient, test_user: tuple[str, int]) -> None:
    """Step must be between 0 and 6."""
    username, _ = test_user
    headers = auth_headers(username)

    resp = client.patch(
        "/api/users/me/setup-status",
        json={"step": 7},
        headers=headers,
    )
    assert resp.status_code == 422

    resp = client.patch(
        "/api/users/me/setup-status",
        json={"step": -1},
        headers=headers,
    )
    assert resp.status_code == 422


def test_me_response_no_setup_fields(client: TestClient, test_user: tuple[str, int]) -> None:
    """/api/users/me should not leak setup fields."""
    username, _ = test_user
    resp = client.get("/api/users/me", headers=auth_headers(username))
    assert resp.status_code == 200
    data = resp.json()
    assert "setup_completed" not in data
    assert "setup_step" not in data
