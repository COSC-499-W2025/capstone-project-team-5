"""Tests for user and user profile API endpoints."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from capstone_project_team_5.api.main import app
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import User, UserProfile


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
    username = "testuser"

    # Clean up any existing user with this username first
    with get_session() as session:
        # First delete any profile for this user to avoid cascade issues
        session.query(UserProfile).filter(
            UserProfile.user_id.in_(session.query(User.id).filter(User.username == username))
        ).delete(synchronize_session=False)
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

    # Cleanup using delete without loading relationships
    with get_session() as session:
        # Delete profile first, then user
        session.query(UserProfile).filter(UserProfile.user_id == user_id).delete(
            synchronize_session=False
        )
        session.query(User).filter(User.id == user_id).delete(synchronize_session=False)
        session.commit()


class TestGetCurrentUserInfo:
    """Tests for GET /api/users/me endpoint."""

    def test_get_current_user_info_success(
        self, client: TestClient, test_user: tuple[str, int]
    ) -> None:
        """Test getting current user info with valid authentication."""
        username, user_id = test_user

        response = client.get("/api/users/me", headers={"X-Username": username})

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
        assert data["username"] == username
        assert "created_at" in data

    def test_get_current_user_info_no_auth(self, client: TestClient) -> None:
        """Test getting current user info without authentication fails."""
        response = client.get("/api/users/me")

        assert response.status_code == 401
        assert "authentication" in response.json()["detail"].lower()

    def test_missing_auth_header(self, client: TestClient) -> None:
        """Test that missing X-Username header returns 401."""
        response = client.get("/api/users/me")

        assert response.status_code == 401


class TestGetProfile:
    """Tests for GET /api/users/{username}/profile endpoint."""

    def test_get_profile_success(self, client: TestClient, test_user: tuple[str, int]) -> None:
        """Test getting existing profile."""
        username, _ = test_user

        # Create profile first
        client.post(
            f"/api/users/{username}/profile",
            json={"first_name": "John", "last_name": "Doe"},
            headers={"X-Username": username},
        )

        # Get profile
        response = client.get(f"/api/users/{username}/profile", headers={"X-Username": username})

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "John"
        assert data["last_name"] == "Doe"

    def test_get_profile_not_found(self, client: TestClient, test_user: tuple[str, int]) -> None:
        """Test getting nonexistent profile fails."""
        username, _ = test_user

        response = client.get(f"/api/users/{username}/profile", headers={"X-Username": username})

        assert response.status_code == 404


class TestCreateProfile:
    """Tests for POST /api/users/{username}/profile endpoint."""

    def test_create_profile_minimal(self, client: TestClient, test_user: tuple[str, int]) -> None:
        """Test creating profile with minimal data."""
        username, _ = test_user

        response = client.post(
            f"/api/users/{username}/profile",
            json={"first_name": "John"},
            headers={"X-Username": username},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == "John"
        assert "id" in data

    def test_create_profile_duplicate(self, client: TestClient, test_user: tuple[str, int]) -> None:
        """Test creating duplicate profile fails."""
        username, _ = test_user

        # Create first profile
        client.post(
            f"/api/users/{username}/profile",
            json={"first_name": "John"},
            headers={"X-Username": username},
        )

        # Try to create again
        response = client.post(
            f"/api/users/{username}/profile",
            json={"first_name": "Jane"},
            headers={"X-Username": username},
        )

        assert response.status_code == 409


class TestUpsertProfile:
    """Tests for PATCH /api/users/{username}/profile endpoint."""

    def test_upsert_profile_creates(self, client: TestClient, test_user: tuple[str, int]) -> None:
        """Test PATCH creates profile if it doesn't exist."""
        username, _ = test_user

        response = client.patch(
            f"/api/users/{username}/profile",
            json={"first_name": "John", "email": "john@example.com"},
            headers={"X-Username": username},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "John"
        assert data["email"] == "john@example.com"

    def test_upsert_profile_updates(self, client: TestClient, test_user: tuple[str, int]) -> None:
        """Test PATCH updates existing profile."""
        username, _ = test_user

        # Create profile
        client.post(
            f"/api/users/{username}/profile",
            json={"first_name": "John", "last_name": "Doe"},
            headers={"X-Username": username},
        )

        # Update with PATCH
        response = client.patch(
            f"/api/users/{username}/profile",
            json={"first_name": "Jane"},
            headers={"X-Username": username},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Jane"
        assert data["last_name"] == "Doe"  # Unchanged
