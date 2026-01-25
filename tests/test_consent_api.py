"""Tests for consent API endpoints."""

from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from capstone_project_team_5.api.main import app
from capstone_project_team_5.consent_tool import ConsentTool
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import ConsentRecord, User


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def test_user() -> User:
    """Create a test user in the database."""
    with get_session() as session:
        user = User(username="test_consent_user", password_hash="test_hash_12345")
        session.add(user)
        session.flush()
        session.refresh(user)
        user_id = user.id

    # Yield user ID and fetch fresh user object after test
    yield user

    # Cleanup
    with get_session() as session:
        user = session.query(User).filter(User.id == user_id).first()
        if user:
            session.delete(user)


class TestAvailableServices:
    """Tests for the /api/consent/available-services endpoint."""

    def test_get_available_services(self, client: TestClient) -> None:
        """Test retrieving available services, AI models, and ignore patterns."""
        response = client.get("/api/consent/available-services")

        assert response.status_code == 200
        data = response.json()

        assert "external_services" in data
        assert "ai_models" in data
        assert "common_ignore_patterns" in data

        # Verify data matches ConsentTool constants
        assert data["external_services"] == ConsentTool.AVAILABLE_EXTERNAL_SERVICES
        assert data["ai_models"] == ConsentTool.AVAILABLE_AI_MODELS
        assert data["common_ignore_patterns"] == ConsentTool.COMMON_IGNORE_PATTERNS

    def test_available_services_contains_expected_values(self, client: TestClient) -> None:
        """Test that available services include expected values."""
        response = client.get("/api/consent/available-services")
        data = response.json()

        # Check for expected services
        assert "GitHub API" in data["external_services"]
        assert "Gemini" in data["external_services"]

        # Check for expected AI models
        assert "Gemini 2.5 Flash (Google)" in data["ai_models"]

        # Check for expected ignore patterns
        assert ".git" in data["common_ignore_patterns"]
        assert "node_modules" in data["common_ignore_patterns"]
        assert "__pycache__" in data["common_ignore_patterns"]


class TestCreateConsentRecord:
    """Tests for creating consent records."""

    def test_create_minimal_consent_record(self, client: TestClient) -> None:
        """Test creating a consent record with minimal data."""
        payload = {
            "consent_given": True,
            "use_external_services": False,
        }

        response = client.post("/api/consent", json=payload)

        assert response.status_code == 201
        data = response.json()

        assert data["consent_given"] is True
        assert data["use_external_services"] is False
        assert data["external_services"] == {}
        assert data["default_ignore_patterns"] == []
        assert data["user_id"] is None
        assert "id" in data
        assert "created_at" in data

    def test_create_full_consent_record(self, client: TestClient, test_user: User) -> None:
        """Test creating a consent record with all fields."""
        payload = {
            "user_id": test_user.id,
            "consent_given": True,
            "use_external_services": True,
            "external_services": {
                "GitHub API": {"allowed": True},
                "Gemini": {"allowed": True},
                "llm": {
                    "allowed": True,
                    "model_preferences": ["Gemini 2.5 Flash (Google)"],
                },
            },
            "default_ignore_patterns": [".git", "node_modules", "__pycache__"],
        }

        response = client.post(
            "/api/consent",
            json=payload,
            headers={"X-User-Id": str(test_user.id)},
        )

        assert response.status_code == 201
        data = response.json()

        assert data["consent_given"] is True
        assert data["use_external_services"] is True
        assert data["user_id"] == test_user.id
        assert data["external_services"]["GitHub API"]["allowed"] is True
        assert data["external_services"]["llm"]["allowed"] is True
        assert data["default_ignore_patterns"] == [".git", "node_modules", "__pycache__"]

    def test_create_consent_with_invalid_user_id(self, client: TestClient) -> None:
        """Test creating a consent record with non-existent user ID."""
        invalid_user_id = 99999
        payload = {
            "user_id": invalid_user_id,  # Non-existent user
            "consent_given": True,
        }

        # Try to create as the non-existent user
        response = client.post(
            "/api/consent",
            json=payload,
            headers={"X-User-Id": str(invalid_user_id)},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestGetConsentRecords:
    """Tests for retrieving consent records."""

    def test_get_all_consent_records(self, client: TestClient) -> None:
        """Test retrieving all consent records."""
        # Create some test records
        with get_session() as session:
            session.add(ConsentRecord(consent_given=True, use_external_services=False))
            session.add(ConsentRecord(consent_given=True, use_external_services=True))

        response = client.get("/api/consent")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) >= 2

    def test_get_consent_records_with_limit(self, client: TestClient) -> None:
        """Test retrieving consent records with a limit."""
        # Create several test records
        with get_session() as session:
            for _ in range(5):
                session.add(ConsentRecord(consent_given=True, use_external_services=False))

        response = client.get("/api/consent?limit=2")

        assert response.status_code == 200
        data = response.json()

        assert len(data) <= 2

    def test_get_consent_records_filtered_by_user(
        self, client: TestClient, test_user: User
    ) -> None:
        """Test retrieving consent records filtered by user ID."""
        # Create records for the test user
        with get_session() as session:
            session.add(
                ConsentRecord(user_id=test_user.id, consent_given=True, use_external_services=True)
            )
            # Create a global record (no user_id)
            session.add(ConsentRecord(consent_given=True, use_external_services=False))

        # Get records as test_user (should see own + global by default)
        response = client.get(
            "/api/consent",
            headers={"X-User-Id": str(test_user.id)},
        )

        assert response.status_code == 200
        data = response.json()

        # Should return records for this user and global records
        for record in data:
            assert record["user_id"] in [test_user.id, None]

        # Get only user-specific records
        response = client.get(
            "/api/consent?include_global=false",
            headers={"X-User-Id": str(test_user.id)},
        )

        assert response.status_code == 200
        data = response.json()

        # Should only return user-specific records
        for record in data:
            assert record["user_id"] == test_user.id

    def test_get_consent_records_ordered_by_created_at(self, client: TestClient) -> None:
        """Test that consent records are ordered by creation date (newest first)."""
        response = client.get("/api/consent?limit=5")

        assert response.status_code == 200
        data = response.json()

        if len(data) >= 2:
            # Verify descending order
            dates = [datetime.fromisoformat(record["created_at"]) for record in data]
            assert dates == sorted(dates, reverse=True)


class TestGetLatestConsentRecord:
    """Tests for retrieving the latest consent record."""

    def test_get_latest_global_consent_record(self, client: TestClient) -> None:
        """Test retrieving the latest global consent record."""
        # Create a global record
        with get_session() as session:
            session.add(
                ConsentRecord(
                    consent_given=True,
                    use_external_services=True,
                    external_services={"test": {"allowed": True}},
                )
            )

        response = client.get("/api/consent/latest")

        assert response.status_code == 200
        data = response.json()

        assert data["consent_given"] is True
        assert data["user_id"] is None

    def test_get_latest_user_consent_record(self, client: TestClient, test_user: User) -> None:
        """Test retrieving the latest consent record for a specific user."""
        # Create a record for the test user
        with get_session() as session:
            session.add(
                ConsentRecord(
                    user_id=test_user.id,
                    consent_given=True,
                    use_external_services=True,
                )
            )

        response = client.get(
            "/api/consent/latest",
            headers={"X-User-Id": str(test_user.id)},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["user_id"] == test_user.id
        assert data["consent_given"] is True

    def test_get_latest_consent_not_found(self, client: TestClient) -> None:
        """Test retrieving latest consent when none exists for filter."""
        # Try to get for a non-existent user
        response = client.get(
            "/api/consent/latest?fallback_to_global=false",
            headers={"X-User-Id": "99999"},
        )

        assert response.status_code == 404
        detail = response.json()["detail"].lower()
        assert "not found" in detail or "no consent record" in detail


class TestGetConsentRecordById:
    """Tests for retrieving a specific consent record by ID."""

    def test_get_consent_record_by_id(self, client: TestClient) -> None:
        """Test retrieving a consent record by its ID."""
        # Create a consent record
        with get_session() as session:
            record = ConsentRecord(consent_given=True, use_external_services=False)
            session.add(record)
            session.flush()
            session.refresh(record)
            record_id = record.id

        response = client.get(f"/api/consent/{record_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == record_id
        assert data["consent_given"] is True

    def test_get_consent_record_not_found(self, client: TestClient) -> None:
        """Test retrieving a non-existent consent record."""
        response = client.get("/api/consent/99999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestUpdateConsentRecord:
    """Tests for updating consent records."""

    def test_update_consent_record_partial(self, client: TestClient) -> None:
        """Test partial update of a consent record."""
        # Create a consent record
        with get_session() as session:
            record = ConsentRecord(
                consent_given=True,
                use_external_services=False,
                default_ignore_patterns=[".git"],
            )
            session.add(record)
            session.flush()
            session.refresh(record)
            record_id = record.id

        # Update only use_external_services
        payload = {"use_external_services": True}
        response = client.patch(f"/api/consent/{record_id}", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == record_id
        assert data["consent_given"] is True  # Unchanged
        assert data["use_external_services"] is True  # Updated
        assert data["default_ignore_patterns"] == [".git"]  # Unchanged

    def test_update_consent_record_full(self, client: TestClient) -> None:
        """Test full update of a consent record."""
        # Create a consent record
        with get_session() as session:
            record = ConsentRecord(consent_given=True, use_external_services=False)
            session.add(record)
            session.flush()
            session.refresh(record)
            record_id = record.id

        # Update all fields
        payload = {
            "consent_given": False,
            "use_external_services": True,
            "external_services": {"GitHub API": {"allowed": True}},
            "default_ignore_patterns": [".git", "node_modules"],
        }
        response = client.patch(f"/api/consent/{record_id}", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert data["consent_given"] is False
        assert data["use_external_services"] is True
        assert data["external_services"] == {"GitHub API": {"allowed": True}}
        assert data["default_ignore_patterns"] == [".git", "node_modules"]

    def test_update_nonexistent_consent_record(self, client: TestClient) -> None:
        """Test updating a non-existent consent record."""
        payload = {"consent_given": False}
        response = client.patch("/api/consent/99999", json=payload)

        assert response.status_code == 404


class TestDeleteConsentRecord:
    """Tests for deleting consent records."""

    def test_delete_consent_record(self, client: TestClient) -> None:
        """Test deleting a consent record."""
        # Create a consent record
        with get_session() as session:
            record = ConsentRecord(consent_given=True, use_external_services=False)
            session.add(record)
            session.flush()
            session.refresh(record)
            record_id = record.id

        response = client.delete(f"/api/consent/{record_id}")

        assert response.status_code == 204

        # Verify it was deleted
        with get_session() as session:
            deleted_record = (
                session.query(ConsentRecord).filter(ConsentRecord.id == record_id).first()
            )
            assert deleted_record is None

    def test_delete_nonexistent_consent_record(self, client: TestClient) -> None:
        """Test deleting a non-existent consent record."""
        response = client.delete("/api/consent/99999")

        assert response.status_code == 404


class TestLLMConfig:
    """Tests for the LLM configuration endpoint."""

    def test_get_llm_config_allowed(self, client: TestClient) -> None:
        """Test getting LLM config when LLM is allowed."""
        # Create a consent record with LLM enabled
        with get_session() as session:
            session.add(
                ConsentRecord(
                    consent_given=True,
                    use_external_services=True,
                    external_services={
                        "llm": {
                            "allowed": True,
                            "model_preferences": ["Gemini 2.5 Flash (Google)"],
                        }
                    },
                )
            )

        response = client.get("/api/consent/llm/config")

        assert response.status_code == 200
        data = response.json()

        assert data["is_allowed"] is True
        assert data["model_preferences"] == ["Gemini 2.5 Flash (Google)"]

    def test_get_llm_config_not_allowed(self, client: TestClient) -> None:
        """Test getting LLM config when LLM is not allowed."""
        # Create a consent record without LLM
        with get_session() as session:
            session.add(
                ConsentRecord(
                    consent_given=True,
                    use_external_services=False,
                    external_services={},
                )
            )

        response = client.get("/api/consent/llm/config")

        assert response.status_code == 200
        data = response.json()

        assert data["is_allowed"] is False
        assert data["model_preferences"] == []

    def test_get_llm_config_no_consent_record(self, client: TestClient) -> None:
        """Test getting LLM config when no consent record exists."""
        # Clean up all consent records for this test
        with get_session() as session:
            session.query(ConsentRecord).delete()

        response = client.get("/api/consent/llm/config")

        assert response.status_code == 200
        data = response.json()

        assert data["is_allowed"] is False
        assert data["model_preferences"] == []

    def test_get_llm_config_for_user(self, client: TestClient, test_user: User) -> None:
        """Test getting LLM config for a specific user."""
        # Create a user-specific consent record with LLM
        with get_session() as session:
            session.add(
                ConsentRecord(
                    user_id=test_user.id,
                    consent_given=True,
                    use_external_services=True,
                    external_services={
                        "llm": {
                            "allowed": True,
                            "model_preferences": ["Gemini 2.5 Flash (Google)"],
                        }
                    },
                )
            )

        response = client.get(
            "/api/consent/llm/config",
            headers={"X-User-Id": str(test_user.id)},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["is_allowed"] is True
        assert data["model_preferences"] == ["Gemini 2.5 Flash (Google)"]

    def test_get_llm_config_fallback_to_global(self, client: TestClient, test_user: User) -> None:
        """Test that LLM config falls back to global record if no user-specific record exists."""
        # Create only a global consent record with LLM
        with get_session() as session:
            session.add(
                ConsentRecord(
                    user_id=None,
                    consent_given=True,
                    use_external_services=True,
                    external_services={
                        "llm": {
                            "allowed": True,
                            "model_preferences": ["Gemini 2.5 Flash (Google)"],
                        }
                    },
                )
            )

        # Request for a user that has no consent record
        response = client.get(
            "/api/consent/llm/config",
            headers={"X-User-Id": str(test_user.id)},
        )

        assert response.status_code == 200
        data = response.json()

        # Should fall back to global record
        assert data["is_allowed"] is True
        assert data["model_preferences"] == ["Gemini 2.5 Flash (Google)"]


class TestAuthenticationAndAuthorization:
    """Tests for authentication and authorization in consent API."""

    def test_create_consent_for_self_allowed(self, client: TestClient, test_user: User) -> None:
        """Test that users can create consent records for themselves."""
        payload = {
            "user_id": test_user.id,
            "consent_given": True,
            "use_external_services": False,
        }

        response = client.post(
            "/api/consent",
            json=payload,
            headers={"X-User-Id": str(test_user.id)},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == test_user.id

    def test_create_consent_for_different_user_forbidden(
        self, client: TestClient, test_user: User
    ) -> None:
        """Test that users cannot create consent records for other users."""
        # Try to create a record for a different user
        other_user_id = test_user.id + 1

        payload = {
            "user_id": other_user_id,
            "consent_given": True,
            "use_external_services": False,
        }

        response = client.post(
            "/api/consent",
            json=payload,
            headers={"X-User-Id": str(test_user.id)},
        )

        assert response.status_code == 403
        assert "can only create consent records for yourself" in response.json()["detail"]

    def test_get_consent_records_filtered_to_current_user(
        self, client: TestClient, test_user: User
    ) -> None:
        """Test that users only see their own records and global records."""
        # Create another user
        with get_session() as session:
            other_user = User(username="other_user", password_hash="hash123")
            session.add(other_user)
            session.flush()
            session.refresh(other_user)
            other_user_id = other_user.id

            # Create records for test_user, other_user, and global
            session.add(
                ConsentRecord(
                    user_id=test_user.id,
                    consent_given=True,
                    use_external_services=False,
                )
            )
            session.add(
                ConsentRecord(
                    user_id=other_user_id,
                    consent_given=True,
                    use_external_services=False,
                )
            )
            session.add(
                ConsentRecord(
                    user_id=None,
                    consent_given=True,
                    use_external_services=False,
                )
            )

        # Get records as test_user
        response = client.get(
            "/api/consent",
            headers={"X-User-Id": str(test_user.id)},
        )

        assert response.status_code == 200
        data = response.json()

        # Should only see own records and global records
        for record in data:
            assert record["user_id"] in [test_user.id, None]

        # Cleanup other_user
        with get_session() as session:
            other_user = session.query(User).filter(User.id == other_user_id).first()
            if other_user:
                session.delete(other_user)

    def test_update_own_consent_record_allowed(self, client: TestClient, test_user: User) -> None:
        """Test that users can update their own consent records."""
        # Create a record for test_user
        with get_session() as session:
            record = ConsentRecord(
                user_id=test_user.id,
                consent_given=True,
                use_external_services=False,
            )
            session.add(record)
            session.flush()
            session.refresh(record)
            record_id = record.id

        # Update as test_user
        response = client.patch(
            f"/api/consent/{record_id}",
            json={"consent_given": False},
            headers={"X-User-Id": str(test_user.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["consent_given"] is False

    def test_update_other_user_consent_forbidden(self, client: TestClient, test_user: User) -> None:
        """Test that users cannot update other users' consent records."""
        # Create another user and their consent record
        with get_session() as session:
            other_user = User(username="other_user_2", password_hash="hash123")
            session.add(other_user)
            session.flush()
            session.refresh(other_user)
            other_user_id = other_user.id

            record = ConsentRecord(
                user_id=other_user_id,
                consent_given=True,
                use_external_services=False,
            )
            session.add(record)
            session.flush()
            session.refresh(record)
            record_id = record.id

        # Try to update as test_user
        response = client.patch(
            f"/api/consent/{record_id}",
            json={"consent_given": False},
            headers={"X-User-Id": str(test_user.id)},
        )

        assert response.status_code == 403
        assert "do not have permission" in response.json()["detail"]

        # Cleanup
        with get_session() as session:
            other_user = session.query(User).filter(User.id == other_user_id).first()
            if other_user:
                session.delete(other_user)

    def test_delete_own_consent_record_allowed(self, client: TestClient, test_user: User) -> None:
        """Test that users can delete their own consent records."""
        # Create a record for test_user
        with get_session() as session:
            record = ConsentRecord(
                user_id=test_user.id,
                consent_given=True,
                use_external_services=False,
            )
            session.add(record)
            session.flush()
            session.refresh(record)
            record_id = record.id

        # Delete as test_user
        response = client.delete(
            f"/api/consent/{record_id}",
            headers={"X-User-Id": str(test_user.id)},
        )

        assert response.status_code == 204

    def test_delete_other_user_consent_forbidden(self, client: TestClient, test_user: User) -> None:
        """Test that users cannot delete other users' consent records."""
        # Create another user and their consent record
        with get_session() as session:
            other_user = User(username="other_user_3", password_hash="hash123")
            session.add(other_user)
            session.flush()
            session.refresh(other_user)
            other_user_id = other_user.id

            record = ConsentRecord(
                user_id=other_user_id,
                consent_given=True,
                use_external_services=False,
            )
            session.add(record)
            session.flush()
            session.refresh(record)
            record_id = record.id

        # Try to delete as test_user
        response = client.delete(
            f"/api/consent/{record_id}",
            headers={"X-User-Id": str(test_user.id)},
        )

        assert response.status_code == 403
        assert "do not have permission" in response.json()["detail"]

        # Cleanup
        with get_session() as session:
            other_user = session.query(User).filter(User.id == other_user_id).first()
            if other_user:
                session.delete(other_user)

    def test_get_record_by_id_ownership_check(self, client: TestClient, test_user: User) -> None:
        """Test that users cannot view other users' consent records by ID."""
        # Create another user and their consent record
        with get_session() as session:
            other_user = User(username="other_user_4", password_hash="hash123")
            session.add(other_user)
            session.flush()
            session.refresh(other_user)
            other_user_id = other_user.id

            record = ConsentRecord(
                user_id=other_user_id,
                consent_given=True,
                use_external_services=False,
            )
            session.add(record)
            session.flush()
            session.refresh(record)
            record_id = record.id

        # Try to view as test_user
        response = client.get(
            f"/api/consent/{record_id}",
            headers={"X-User-Id": str(test_user.id)},
        )

        assert response.status_code == 403
        assert "do not have permission" in response.json()["detail"]

        # Cleanup
        with get_session() as session:
            other_user = session.query(User).filter(User.id == other_user_id).first()
            if other_user:
                session.delete(other_user)

    def test_global_records_accessible_by_all(self, client: TestClient) -> None:
        """Test that global records (user_id=None) are accessible by anyone."""
        # Create a global record
        with get_session() as session:
            record = ConsentRecord(
                user_id=None,
                consent_given=True,
                use_external_services=False,
            )
            session.add(record)
            session.flush()
            session.refresh(record)
            record_id = record.id

        # Access without authentication
        response = client.get(f"/api/consent/{record_id}")
        assert response.status_code == 200

        # Update without authentication (global records can be updated by anyone)
        response = client.patch(
            f"/api/consent/{record_id}",
            json={"consent_given": False},
        )
        assert response.status_code == 200

        # Delete without authentication
        response = client.delete(f"/api/consent/{record_id}")
        assert response.status_code == 204
