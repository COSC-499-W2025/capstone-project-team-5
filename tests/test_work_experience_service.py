"""Test suite for work experience service."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import capstone_project_team_5.data.db as db_module
from capstone_project_team_5.data.models import Base, User
from capstone_project_team_5.services.work_experience import (
    create_work_experience,
    delete_work_experience,
    get_work_experience,
    get_work_experiences,
    update_work_experience,
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


def test_get_experiences_returns_none_for_nonexistent_user(tmp_db):
    """Test get_work_experiences returns None for nonexistent user."""
    assert get_work_experiences("nonexistent") is None
    # Also test create/update/delete return None/False for nonexistent user
    assert create_work_experience("nonexistent", {"company": "X", "title": "Y"}) is None
    assert update_work_experience("nonexistent", 1, {"company": "X"}) is None
    assert delete_work_experience("nonexistent", 1) is False


def test_get_experiences_returns_empty_list_when_none_exist(test_user):
    """Test get_work_experiences returns empty list when user has no entries."""
    result = get_work_experiences(test_user)
    assert result == []
    # Also test update/delete return None/False for nonexistent work exp
    assert update_work_experience(test_user, 999, {"company": "X"}) is None
    assert delete_work_experience(test_user, 999) is False


def test_create_and_get_work_experience_with_all_fields(test_user):
    """Test creating and retrieving work experience with all fields, ordering, and validation."""
    # Test create with all fields
    work_exp_data = {
        "company": "Google",
        "title": "Software Engineer",
        "location": "Mountain View, CA",
        "start_date": date(2020, 6, 1),
        "end_date": date(2023, 8, 15),
        "description": "Built large-scale distributed systems",
        "bullets": '["Led team of 5", "Reduced latency by 40%"]',
        "is_current": False,
        "rank": 1,
    }
    result = create_work_experience(test_user, work_exp_data)
    assert result is not None
    assert result["company"] == "Google"
    assert result["start_date"] == date(2020, 6, 1)
    assert "id" in result

    # Verify get by ID works
    fetched = get_work_experience(test_user, result["id"])
    assert fetched is not None
    assert fetched["company"] == "Google"

    # Test create requires company and title
    assert create_work_experience(test_user, {"company": "Only"}) is None
    assert create_work_experience(test_user, {"title": "Only"}) is None

    # Test ordering by rank
    create_work_experience(test_user, {"company": "Third", "title": "E", "rank": 3})
    create_work_experience(test_user, {"company": "First", "title": "E", "rank": 0})
    results = get_work_experiences(test_user)
    assert [r["company"] for r in results] == ["First", "Google", "Third"]


def test_update_partial_fields(test_user):
    """Test update modifies only provided fields."""
    created = create_work_experience(
        test_user,
        {"company": "Original", "title": "Dev", "location": "NYC"},
    )
    result = update_work_experience(
        test_user,
        created["id"],
        {"company": "Updated", "is_current": True},
    )
    assert result is not None
    assert result["company"] == "Updated"
    assert result["title"] == "Dev"  # Unchanged
    assert result["location"] == "NYC"  # Unchanged
    assert result["is_current"] is True


def test_delete_work_experience(test_user):
    """Test delete removes work experience."""
    created = create_work_experience(test_user, {"company": "ToDelete", "title": "X"})
    assert delete_work_experience(test_user, created["id"]) is True
    assert get_work_experience(test_user, created["id"]) is None


def test_validation_rejects_invalid_dates_on_create(test_user):
    """Test validation rejects invalid date combinations on create."""
    # end_date before start_date
    assert (
        create_work_experience(
            test_user,
            {
                "company": "Google",
                "title": "Engineer",
                "start_date": date(2023, 1, 1),
                "end_date": date(2022, 1, 1),
            },
        )
        is None
    )

    # is_current=True with end_date
    assert (
        create_work_experience(
            test_user,
            {
                "company": "Google",
                "title": "Engineer",
                "is_current": True,
                "end_date": date(2023, 12, 31),
            },
        )
        is None
    )


def test_validation_rejects_invalid_dates_on_update(test_user):
    """Test validation rejects invalid date on update."""
    created = create_work_experience(
        test_user,
        {"company": "Google", "title": "Engineer", "start_date": date(2020, 1, 1)},
    )
    # end_date before existing start_date
    assert update_work_experience(test_user, created["id"], {"end_date": date(2019, 1, 1)}) is None


def test_is_current_auto_clears_end_date(test_user):
    """Test that setting is_current=True auto-clears end_date."""
    created = create_work_experience(
        test_user,
        {
            "company": "Google",
            "title": "Engineer",
            "end_date": date(2023, 12, 31),
        },
    )
    result = update_work_experience(test_user, created["id"], {"is_current": True})
    assert result is not None
    assert result["is_current"] is True
    assert result["end_date"] is None
