"""Test suite for user profile service."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import capstone_project_team_5.data.db as db_module
from capstone_project_team_5.data.models import Base, User
from capstone_project_team_5.services.user_profile import (
    create_user_profile,
    delete_user_profile,
    get_user_profile,
    update_user_profile,
    upsert_user_profile,
)


@pytest.fixture(scope="function")
def tmp_db(monkeypatch, tmp_path):
    """Create a temporary test database."""
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(db_module, "_engine", engine)
    monkeypatch.setattr(db_module, "_SessionLocal", sessionmaker(bind=engine))
    yield
    engine.dispose()


@pytest.fixture
def test_user(tmp_db):
    """Create a test user and return username."""
    with db_module.get_session() as s:
        u = User(username="testuser", password_hash="hash")
        s.add(u)
        s.commit()
        return "testuser"


def test_get_returns_none_when_no_profile(tmp_db, test_user):
    """Test get returns None for nonexistent user or missing profile."""
    assert get_user_profile("nonexistent") is None
    assert get_user_profile(test_user) is None


def test_get_returns_profile_data(test_user):
    """Test get returns profile data when it exists."""
    create_user_profile(
        test_user,
        {"first_name": "John", "last_name": "Doe", "email": "john@example.com"},
    )
    result = get_user_profile(test_user)
    assert result is not None
    assert result["first_name"] == "John"
    assert result["email"] == "john@example.com"
    assert "id" in result and "updated_at" in result


def test_create_profile_with_all_fields(test_user):
    """Test creates profile with all fields successfully."""
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
    result = create_user_profile(test_user, profile_data)
    assert result is not None
    for key, value in profile_data.items():
        assert result[key] == value


def test_create_rejects_duplicate(test_user):
    """Test create returns None when profile already exists."""
    create_user_profile(test_user, {"first_name": "First"})
    assert create_user_profile(test_user, {"first_name": "Second"}) is None


def test_create_returns_none_for_nonexistent_user(tmp_db):
    """Test create returns None when user doesn't exist."""
    assert create_user_profile("nonexistent", {"first_name": "John"}) is None


def test_update_partial_fields_and_set_to_none(test_user):
    """Test update modifies only provided fields and can set to None."""
    create_user_profile(
        test_user,
        {"first_name": "John", "last_name": "Doe", "phone": "555-1234"},
    )
    result = update_user_profile(
        test_user,
        {"first_name": "Jane", "phone": None},  # Update one, clear one
    )
    assert result is not None
    assert result["first_name"] == "Jane"
    assert result["last_name"] == "Doe"  # Unchanged
    assert result["phone"] is None  # Cleared


def test_update_returns_none_when_no_profile(tmp_db, test_user):
    """Test update returns None for nonexistent user or missing profile."""
    assert update_user_profile("nonexistent", {"first_name": "X"}) is None
    assert update_user_profile(test_user, {"first_name": "X"}) is None


def test_upsert_creates_and_updates(test_user):
    """Test upsert creates when missing and updates when exists."""
    # Create via upsert
    result = upsert_user_profile(test_user, {"first_name": "New"})
    assert result is not None
    assert result["first_name"] == "New"

    # Update via upsert
    result = upsert_user_profile(test_user, {"first_name": "Updated", "city": "NYC"})
    assert result["first_name"] == "Updated"
    assert result["city"] == "NYC"


def test_delete_profile(test_user):
    """Test delete removes profile and allows recreation."""
    create_user_profile(test_user, {"first_name": "ToDelete"})
    assert delete_user_profile(test_user) is True
    assert get_user_profile(test_user) is None
    # Can recreate after deletion
    assert create_user_profile(test_user, {"first_name": "New"}) is not None


def test_delete_returns_false_when_nothing_to_delete(tmp_db, test_user):
    """Test delete returns False for nonexistent user or missing profile."""
    assert delete_user_profile("nonexistent") is False
    assert delete_user_profile(test_user) is False
