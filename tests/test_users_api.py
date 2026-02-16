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
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def test_user() -> Generator[tuple[str, int]]:
    """Create a test user in the database.

    Returns:
        tuple: (username, user_id)
    """
    username = "testuser"

    # Clean up any existing user with this username first using raw SQL to avoid cascade issues
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


@pytest.fixture
def other_user() -> Generator[tuple[str, int]]:
    """Create another test user in the database.

    Returns:
        tuple: (username, user_id)
    """
    username = "otheruser"

    # Clean up any existing user with this username first using raw SQL to avoid cascade issues
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
        assert "Authentication required" in response.json()["detail"]

    def test_get_current_user_info_nonexistent(self, client: TestClient) -> None:
        """Test getting current user info for nonexistent user fails."""
        response = client.get("/api/users/me", headers={"X-Username": "nonexistent"})

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestGetUserInfo:
    """Tests for GET /api/users/{username} endpoint."""

    def test_get_user_info_success(self, client: TestClient, test_user: tuple[str, int]) -> None:
        """Test getting user info for own account."""
        username, user_id = test_user
        response = client.get(f"/api/users/{username}", headers={"X-Username": username})

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
        assert data["username"] == username

    def test_get_user_info_forbidden(
        self, client: TestClient, test_user: tuple[str, int], other_user: tuple[str, int]
    ) -> None:
        """Test getting user info for different user fails."""
        username, _ = test_user
        other_username, _ = other_user

        response = client.get(f"/api/users/{username}", headers={"X-Username": other_username})

        assert response.status_code == 403
        assert "permission" in response.json()["detail"]

    def test_get_user_info_nonexistent(
        self, client: TestClient, test_user: tuple[str, int]
    ) -> None:
        """Test getting info for nonexistent user fails."""
        username, _ = test_user
        response = client.get("/api/users/nonexistent", headers={"X-Username": username})

        assert response.status_code == 403  # First checks permission, so 403 expected


class TestGetUserWithProfile:
    """Tests for GET /api/users/{username}/full endpoint."""

    def test_get_user_with_profile_no_profile(
        self, client: TestClient, test_user: tuple[str, int]
    ) -> None:
        """Test getting user with profile when no profile exists."""
        username, user_id = test_user
        response = client.get(f"/api/users/{username}/full", headers={"X-Username": username})

        assert response.status_code == 200
        data = response.json()
        assert data["user"]["id"] == user_id
        assert data["user"]["username"] == username
        assert data["profile"] is None

    def test_get_user_with_profile_has_profile(
        self, client: TestClient, test_user: tuple[str, int]
    ) -> None:
        """Test getting user with profile when profile exists."""
        username, user_id = test_user

        # Create a profile first
        profile_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
        }
        create_response = client.post(
            f"/api/users/{username}/profile",
            json=profile_data,
            headers={"X-Username": username},
        )
        assert create_response.status_code == 201

        # Get user with profile
        response = client.get(f"/api/users/{username}/full", headers={"X-Username": username})

        assert response.status_code == 200
        data = response.json()
        assert data["user"]["id"] == user_id
        assert data["user"]["username"] == username
        assert data["profile"] is not None
        assert data["profile"]["first_name"] == "John"
        assert data["profile"]["last_name"] == "Doe"
        assert data["profile"]["email"] == "john@example.com"


class TestGetProfile:
    """Tests for GET /api/users/{username}/profile endpoint."""

    def test_get_profile_not_found(self, client: TestClient, test_user: tuple[str, int]) -> None:
        """Test getting profile when it doesn't exist."""
        username, _ = test_user
        response = client.get(f"/api/users/{username}/profile", headers={"X-Username": username})

        assert response.status_code == 404
        assert "Profile not found" in response.json()["detail"]

    def test_get_profile_success(self, client: TestClient, test_user: tuple[str, int]) -> None:
        """Test getting existing profile."""
        username, user_id = test_user

        # Create profile
        profile_data = {
            "first_name": "Jane",
            "email": "jane@example.com",
            "city": "Boston",
        }
        create_response = client.post(
            f"/api/users/{username}/profile",
            json=profile_data,
            headers={"X-Username": username},
        )
        assert create_response.status_code == 201

        # Get profile
        response = client.get(f"/api/users/{username}/profile", headers={"X-Username": username})

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == user_id
        assert data["first_name"] == "Jane"
        assert data["email"] == "jane@example.com"
        assert data["city"] == "Boston"
        assert "id" in data
        assert "updated_at" in data

    def test_get_profile_forbidden(
        self, client: TestClient, test_user: tuple[str, int], other_user: tuple[str, int]
    ) -> None:
        """Test getting profile for different user fails."""
        username, _ = test_user
        other_username, _ = other_user

        response = client.get(
            f"/api/users/{username}/profile", headers={"X-Username": other_username}
        )

        assert response.status_code == 403


class TestCreateProfile:
    """Tests for POST /api/users/{username}/profile endpoint."""

    def test_create_profile_minimal(self, client: TestClient, test_user: tuple[str, int]) -> None:
        """Test creating profile with minimal data."""
        username, user_id = test_user
        profile_data = {"first_name": "John"}

        response = client.post(
            f"/api/users/{username}/profile",
            json=profile_data,
            headers={"X-Username": username},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == user_id
        assert data["first_name"] == "John"
        assert "id" in data

    def test_create_profile_full(self, client: TestClient, test_user: tuple[str, int]) -> None:
        """Test creating profile with all fields."""
        username, user_id = test_user
        profile_data = {
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane@example.com",
            "phone": "555-1234",
            "address": "123 Main St",
            "city": "Boston",
            "state": "MA",
            "zip_code": "02101",
            "linkedin_url": "https://linkedin.com/in/janesmith",
            "github_username": "janesmith",
            "website": "https://jane.dev",
        }

        response = client.post(
            f"/api/users/{username}/profile",
            json=profile_data,
            headers={"X-Username": username},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == user_id
        for key, value in profile_data.items():
            assert data[key] == value

    def test_create_profile_duplicate(self, client: TestClient, test_user: tuple[str, int]) -> None:
        """Test creating duplicate profile fails."""
        username, _ = test_user

        # Create first profile
        response1 = client.post(
            f"/api/users/{username}/profile",
            json={"first_name": "First"},
            headers={"X-Username": username},
        )
        assert response1.status_code == 201

        # Try to create again
        response2 = client.post(
            f"/api/users/{username}/profile",
            json={"first_name": "Second"},
            headers={"X-Username": username},
        )
        assert response2.status_code == 409
        assert "already exists" in response2.json()["detail"]

    def test_create_profile_forbidden(
        self, client: TestClient, test_user: tuple[str, int], other_user: tuple[str, int]
    ) -> None:
        """Test creating profile for different user fails."""
        username, _ = test_user
        other_username, _ = other_user

        response = client.post(
            f"/api/users/{username}/profile",
            json={"first_name": "John"},
            headers={"X-Username": other_username},
        )

        assert response.status_code == 403

    def test_create_profile_nonexistent_user(
        self, client: TestClient, test_user: tuple[str, int]
    ) -> None:
        """Test creating profile for nonexistent user fails."""
        username, _ = test_user

        response = client.post(
            "/api/users/nonexistent/profile",
            json={"first_name": "John"},
            headers={"X-Username": username},
        )

        assert response.status_code == 403  # Permission check happens first


class TestUpdateProfile:
    """Tests for PUT /api/users/{username}/profile endpoint."""

    def test_update_profile_success(self, client: TestClient, test_user: tuple[str, int]) -> None:
        """Test updating existing profile."""
        username, _ = test_user

        # Create profile
        create_response = client.post(
            f"/api/users/{username}/profile",
            json={"first_name": "John", "last_name": "Doe", "phone": "555-1234"},
            headers={"X-Username": username},
        )
        assert create_response.status_code == 201

        # Update profile - PUT requires all fields (full replacement)
        update_data = {
            "first_name": "Jane",
            "last_name": "Doe",  # Must include to keep it
            "phone": None,  # Clear phone
        }
        response = client.put(
            f"/api/users/{username}/profile",
            json=update_data,
            headers={"X-Username": username},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Jane"
        assert data["last_name"] == "Doe"
        assert data["phone"] is None  # Cleared

    def test_update_profile_not_found(self, client: TestClient, test_user: tuple[str, int]) -> None:
        """Test updating nonexistent profile fails."""
        username, _ = test_user

        response = client.put(
            f"/api/users/{username}/profile",
            json={"first_name": "Jane"},
            headers={"X-Username": username},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestUpsertProfile:
    """Tests for PATCH /api/users/{username}/profile endpoint."""

    def test_upsert_profile_creates(self, client: TestClient, test_user: tuple[str, int]) -> None:
        """Test upsert creates profile when it doesn't exist."""
        username, user_id = test_user

        response = client.patch(
            f"/api/users/{username}/profile",
            json={"first_name": "New"},
            headers={"X-Username": username},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == user_id
        assert data["first_name"] == "New"

    def test_upsert_profile_updates(self, client: TestClient, test_user: tuple[str, int]) -> None:
        """Test upsert updates profile when it exists."""
        username, _ = test_user

        # Create profile
        create_response = client.post(
            f"/api/users/{username}/profile",
            json={"first_name": "Original", "city": "NYC"},
            headers={"X-Username": username},
        )
        assert create_response.status_code == 201

        # Upsert (update)
        response = client.patch(
            f"/api/users/{username}/profile",
            json={"first_name": "Updated"},
            headers={"X-Username": username},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["city"] == "NYC"  # Unchanged


class TestDeleteProfile:
    """Tests for DELETE /api/users/{username}/profile endpoint."""

    def test_delete_profile_success(self, client: TestClient, test_user: tuple[str, int]) -> None:
        """Test deleting existing profile."""
        username, _ = test_user

        # Create profile
        create_response = client.post(
            f"/api/users/{username}/profile",
            json={"first_name": "ToDelete"},
            headers={"X-Username": username},
        )
        assert create_response.status_code == 201

        # Delete profile
        response = client.delete(f"/api/users/{username}/profile", headers={"X-Username": username})

        assert response.status_code == 204

        # Verify deleted
        get_response = client.get(
            f"/api/users/{username}/profile", headers={"X-Username": username}
        )
        assert get_response.status_code == 404

    def test_delete_profile_not_found(self, client: TestClient, test_user: tuple[str, int]) -> None:
        """Test deleting nonexistent profile fails."""
        username, _ = test_user

        response = client.delete(f"/api/users/{username}/profile", headers={"X-Username": username})

        assert response.status_code == 404

    def test_delete_profile_forbidden(
        self, client: TestClient, test_user: tuple[str, int], other_user: tuple[str, int]
    ) -> None:
        """Test deleting profile for different user fails."""
        username, _ = test_user
        other_username, _ = other_user

        response = client.delete(
            f"/api/users/{username}/profile", headers={"X-Username": other_username}
        )

        assert response.status_code == 403


class TestAuthenticationEdgeCases:
    """Tests for authentication and authorization edge cases."""

    def test_missing_auth_header(self, client: TestClient, test_user: tuple[str, int]) -> None:
        """Test that missing auth header returns 401."""
        username, _ = test_user

        endpoints = [
            ("GET", f"/api/users/{username}"),
            ("GET", f"/api/users/{username}/full"),
            ("GET", f"/api/users/{username}/profile"),
            ("POST", f"/api/users/{username}/profile"),
            ("PUT", f"/api/users/{username}/profile"),
            ("PATCH", f"/api/users/{username}/profile"),
            ("DELETE", f"/api/users/{username}/profile"),
        ]

        for method, url in endpoints:
            response = client.request(method, url, json={} if method != "GET" else None)
            assert response.status_code == 401, f"{method} {url} should return 401 without auth"
