"""Tests for consent API endpoints (slim 4-endpoint design).

Endpoints under test:
- GET  /api/consent/available-services
- POST /api/consent  (upsert)
- GET  /api/consent/latest
- GET  /api/consent/llm/config

All endpoints use the shared X-Username header (optional) instead of X-User-Id.
"""

from __future__ import annotations

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
    """Create a test user in the database and clean up after the test."""
    with get_session() as session:
        # Reuse existing user if leftover from a prior test, else create
        user = session.query(User).filter(User.username == "test_consent_user").first()
        if user is None:
            user = User(username="test_consent_user", password_hash="test_hash_12345")
            session.add(user)
            session.flush()
            session.refresh(user)
        user_id = user.id

    yield user  # type: ignore[misc]

    # Use query-level delete to avoid ORM cascade loading related tables
    with get_session() as session:
        session.query(ConsentRecord).filter(ConsentRecord.user_id == user_id).delete()
        session.query(User).filter(User.id == user_id).delete()


@pytest.fixture(autouse=True)
def _clean_consent_records() -> None:  # type: ignore[misc]
    """Remove all consent records before each test for isolation."""
    with get_session() as session:
        session.query(ConsentRecord).delete()


# ------------------------------------------------------------------ #
#  GET /api/consent/available-services                                #
# ------------------------------------------------------------------ #


class TestAvailableServices:
    """Tests for GET /api/consent/available-services."""

    def test_returns_all_fields(self, client: TestClient) -> None:
        response = client.get("/api/consent/available-services")

        assert response.status_code == 200
        data = response.json()

        assert data["external_services"] == ConsentTool.AVAILABLE_EXTERNAL_SERVICES
        assert data["ai_models"] == ConsentTool.AVAILABLE_AI_MODELS
        assert data["common_ignore_patterns"] == ConsentTool.COMMON_IGNORE_PATTERNS

    def test_contains_expected_values(self, client: TestClient) -> None:
        response = client.get("/api/consent/available-services")
        data = response.json()

        assert "GitHub API" in data["external_services"]
        assert "Gemini 2.5 Flash (Google)" in data["ai_models"]
        assert ".git" in data["common_ignore_patterns"]
        assert "node_modules" in data["common_ignore_patterns"]
        assert "__pycache__" in data["common_ignore_patterns"]


# ------------------------------------------------------------------ #
#  POST /api/consent  (upsert)                                       #
# ------------------------------------------------------------------ #


class TestUpsertConsent:
    """Tests for POST /api/consent."""

    def test_create_global_consent_minimal(self, client: TestClient) -> None:
        """Create a global record with only required fields."""
        payload = {"consent_given": True}

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
        assert "updated_at" in data

    def test_create_user_consent_full(self, client: TestClient, test_user: User) -> None:
        """Create a user-specific record with all fields."""
        payload = {
            "consent_given": True,
            "use_external_services": True,
            "external_services": {
                "GitHub API": {"allowed": True},
                "llm": {
                    "allowed": True,
                    "model_preferences": ["Gemini 2.5 Flash (Google)"],
                },
            },
            "default_ignore_patterns": [".git", "node_modules"],
        }

        response = client.post(
            "/api/consent",
            json=payload,
            headers={"X-Username": test_user.username},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == test_user.id
        assert data["consent_given"] is True
        assert data["use_external_services"] is True
        assert data["external_services"]["llm"]["allowed"] is True
        assert data["default_ignore_patterns"] == [".git", "node_modules"]

    def test_upsert_updates_existing_global_record(self, client: TestClient) -> None:
        """Second POST to global scope updates the existing record."""
        client.post("/api/consent", json={"consent_given": True})

        response = client.post(
            "/api/consent",
            json={"consent_given": False, "use_external_services": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["consent_given"] is False
        assert data["use_external_services"] is True

        # Only one global record should exist
        with get_session() as session:
            count = session.query(ConsentRecord).filter(ConsentRecord.user_id.is_(None)).count()
            assert count == 1

    def test_upsert_updates_existing_user_record(self, client: TestClient, test_user: User) -> None:
        """Second POST for a user updates their existing record."""
        headers = {"X-Username": test_user.username}
        client.post(
            "/api/consent",
            json={"consent_given": True},
            headers=headers,
        )

        response = client.post(
            "/api/consent",
            json={
                "consent_given": True,
                "use_external_services": True,
                "external_services": {"llm": {"allowed": True}},
            },
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["use_external_services"] is True
        assert data["user_id"] == test_user.id

        # Only one record for this user
        with get_session() as session:
            count = (
                session.query(ConsentRecord).filter(ConsentRecord.user_id == test_user.id).count()
            )
            assert count == 1

    def test_create_consent_unknown_user_404(self, client: TestClient) -> None:
        """POST with a non-existent username returns 404."""
        response = client.post(
            "/api/consent",
            json={"consent_given": True},
            headers={"X-Username": "ghost_user_does_not_exist"},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_revoke_consent_via_upsert(self, client: TestClient) -> None:
        """Revoking consent = POST with consent_given: False (replaces DELETE)."""
        # First grant consent
        resp = client.post("/api/consent", json={"consent_given": True})
        assert resp.status_code == 201
        assert resp.json()["consent_given"] is True

        # Now revoke
        resp = client.post(
            "/api/consent",
            json={"consent_given": False, "use_external_services": False},
        )
        assert resp.status_code == 200  # update, not create
        data = resp.json()
        assert data["consent_given"] is False
        assert data["use_external_services"] is False

        # Verify latest reflects the revocation
        latest = client.get("/api/consent/latest")
        assert latest.status_code == 200
        assert latest.json()["consent_given"] is False

    def test_user_and_global_records_are_independent(
        self, client: TestClient, test_user: User
    ) -> None:
        """User-specific and global records don't interfere."""
        # Create global record
        client.post("/api/consent", json={"consent_given": False})
        # Create user record
        client.post(
            "/api/consent",
            json={"consent_given": True},
            headers={"X-Username": test_user.username},
        )

        with get_session() as session:
            global_count = (
                session.query(ConsentRecord).filter(ConsentRecord.user_id.is_(None)).count()
            )
            user_count = (
                session.query(ConsentRecord).filter(ConsentRecord.user_id == test_user.id).count()
            )
            assert global_count == 1
            assert user_count == 1


# ------------------------------------------------------------------ #
#  GET /api/consent/latest                                            #
# ------------------------------------------------------------------ #


class TestGetLatestConsent:
    """Tests for GET /api/consent/latest."""

    def test_latest_global_record(self, client: TestClient) -> None:
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

    def test_latest_user_record(self, client: TestClient, test_user: User) -> None:
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
            headers={"X-Username": test_user.username},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == test_user.id

    def test_fallback_to_global(self, client: TestClient, test_user: User) -> None:
        """User with no record falls back to global when flag is True."""
        with get_session() as session:
            session.add(ConsentRecord(consent_given=True, use_external_services=False))

        response = client.get(
            "/api/consent/latest",
            headers={"X-Username": test_user.username},
        )

        assert response.status_code == 200
        assert response.json()["user_id"] is None  # global record

    def test_no_fallback_returns_404(self, client: TestClient, test_user: User) -> None:
        """Without fallback, missing user record returns 404."""
        response = client.get(
            "/api/consent/latest?fallback_to_global=false",
            headers={"X-Username": test_user.username},
        )

        assert response.status_code == 404

    def test_no_records_at_all_returns_404(self, client: TestClient) -> None:
        response = client.get("/api/consent/latest")

        assert response.status_code == 404


# ------------------------------------------------------------------ #
#  GET /api/consent/llm/config                                        #
# ------------------------------------------------------------------ #


class TestLLMConfig:
    """Tests for GET /api/consent/llm/config."""

    def test_llm_allowed(self, client: TestClient) -> None:
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

    def test_llm_not_allowed(self, client: TestClient) -> None:
        with get_session() as session:
            session.add(
                ConsentRecord(
                    consent_given=True,
                    use_external_services=False,
                )
            )

        response = client.get("/api/consent/llm/config")

        assert response.status_code == 200
        data = response.json()
        assert data["is_allowed"] is False
        assert data["model_preferences"] == []

    def test_no_consent_record(self, client: TestClient) -> None:
        response = client.get("/api/consent/llm/config")

        assert response.status_code == 200
        data = response.json()
        assert data["is_allowed"] is False

    def test_user_specific_llm_config(self, client: TestClient, test_user: User) -> None:
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
            headers={"X-Username": test_user.username},
        )

        assert response.status_code == 200
        assert response.json()["is_allowed"] is True

    def test_llm_config_fallback_to_global(self, client: TestClient, test_user: User) -> None:
        """LLM config falls back to global record when user has none."""
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

        response = client.get(
            "/api/consent/llm/config",
            headers={"X-Username": test_user.username},
        )

        assert response.status_code == 200
        assert response.json()["is_allowed"] is True


# ------------------------------------------------------------------ #
#  Auth consistency — X-Username everywhere                           #
# ------------------------------------------------------------------ #


class TestAuthConsistency:
    """Verify consent endpoints use X-Username (not X-User-Id)."""

    def test_x_user_id_header_is_ignored(self, client: TestClient) -> None:
        """Old X-User-Id header should have no effect — treated as anonymous."""
        response = client.post(
            "/api/consent",
            json={"consent_given": True},
            headers={"X-User-Id": "1"},
        )

        assert response.status_code == 201
        assert response.json()["user_id"] is None  # anonymous / global

    def test_x_username_creates_user_record(self, client: TestClient, test_user: User) -> None:
        response = client.post(
            "/api/consent",
            json={"consent_given": True},
            headers={"X-Username": test_user.username},
        )

        assert response.status_code == 201
        assert response.json()["user_id"] == test_user.id
