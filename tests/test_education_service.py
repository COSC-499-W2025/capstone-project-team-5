"""Test suite for education service."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import capstone_project_team_5.data.db as db_module
from capstone_project_team_5.data.models import Base, User
from capstone_project_team_5.services.education import (
    create_education,
    delete_education,
    get_education,
    get_educations,
    update_education,
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


def test_nonexistent_user_and_education_handling(tmp_db, test_user):
    """Test handling of nonexistent users and education entries."""
    # Nonexistent user
    assert get_educations("nonexistent") is None
    assert create_education("nonexistent", {"institution": "MIT", "degree": "BS"}) is None
    assert update_education("nonexistent", 1, {"institution": "MIT"}) is None
    assert delete_education("nonexistent", 1) is False

    # Existing user, no education entries
    assert get_educations(test_user) == []
    assert update_education(test_user, 999, {"institution": "MIT"}) is None
    assert delete_education(test_user, 999) is False


def test_create_get_and_ordering(test_user):
    """Test create, get by ID, required fields, and ordering by rank."""
    # Create with all fields
    education_data = {
        "institution": "Massachusetts Institute of Technology",
        "degree": "Bachelor of Science",
        "field_of_study": "Computer Science",
        "gpa": 3.85,
        "start_date": date(2018, 9, 1),
        "end_date": date(2022, 5, 15),
        "achievements": '["Dean\'s List", "Summa Cum Laude"]',
        "is_current": False,
        "rank": 1,
    }
    result = create_education(test_user, education_data)
    assert result is not None
    assert result["institution"] == "Massachusetts Institute of Technology"
    assert result["gpa"] == 3.85
    assert "id" in result

    # Get by ID
    fetched = get_education(test_user, result["id"])
    assert fetched is not None
    assert fetched["institution"] == "Massachusetts Institute of Technology"

    # Required fields validation
    assert create_education(test_user, {"institution": "Only"}) is None
    assert create_education(test_user, {"degree": "Only"}) is None

    # Ordering by rank
    create_education(test_user, {"institution": "Third", "degree": "MS", "rank": 3})
    create_education(test_user, {"institution": "First", "degree": "PhD", "rank": 0})
    institutions = [r["institution"] for r in get_educations(test_user)]
    assert institutions == ["First", "Massachusetts Institute of Technology", "Third"]


def test_update_and_delete(test_user):
    """Test partial update and delete operations."""
    created = create_education(
        test_user,
        {"institution": "Original", "degree": "BS", "field_of_study": "Math"},
    )

    # Partial update
    result = update_education(
        test_user, created["id"], {"institution": "Updated", "is_current": True}
    )
    assert result["institution"] == "Updated"
    assert result["degree"] == "BS"  # Unchanged
    assert result["field_of_study"] == "Math"  # Unchanged

    # Delete
    assert delete_education(test_user, created["id"]) is True
    assert get_education(test_user, created["id"]) is None


def test_date_validation_and_is_current_behavior(test_user):
    """Test date validation rules and is_current auto-clearing end_date."""
    d = {"institution": "MIT", "degree": "BS"}
    # end_date before start_date rejected
    assert (
        create_education(
            test_user, {**d, "start_date": date(2023, 1, 1), "end_date": date(2022, 1, 1)}
        )
        is None
    )
    # is_current=True with end_date rejected
    assert (
        create_education(test_user, {**d, "is_current": True, "end_date": date(2023, 12, 31)})
        is None
    )

    # Create valid, then test update validation
    created = create_education(
        test_user, {**d, "start_date": date(2020, 1, 1), "end_date": date(2024, 1, 1)}
    )
    assert update_education(test_user, created["id"], {"end_date": date(2019, 1, 1)}) is None

    # is_current=True auto-clears end_date
    result = update_education(test_user, created["id"], {"is_current": True})
    assert result["is_current"] is True and result["end_date"] is None


def test_gpa_validation(test_user):
    """Test GPA validation on create and update."""
    # Invalid GPA rejected on create
    assert create_education(test_user, {"institution": "MIT", "degree": "BS", "gpa": -0.5}) is None
    assert create_education(test_user, {"institution": "MIT", "degree": "BS", "gpa": 5.5}) is None

    # Valid GPA accepted
    result = create_education(test_user, {"institution": "MIT", "degree": "BS", "gpa": 3.75})
    assert result["gpa"] == 3.75

    # Invalid GPA rejected on update
    assert update_education(test_user, result["id"], {"gpa": 6.0}) is None
    assert get_education(test_user, result["id"])["gpa"] == 3.75  # Unchanged


def test_cross_user_access_prevented(tmp_db):
    """Test that users cannot access each other's education entries."""
    with db_module.get_session() as s:
        u1 = User(username="user1", password_hash="hash")
        u2 = User(username="user2", password_hash="hash")
        s.add_all([u1, u2])
        s.commit()

    created = create_education("user1", {"institution": "MIT", "degree": "BS"})
    edu_id = created["id"]

    # user2 cannot access, update, or delete user1's education
    assert get_education("user2", edu_id) is None
    assert update_education("user2", edu_id, {"institution": "Hacked"}) is None
    assert delete_education("user2", edu_id) is False

    # user1 still has access
    assert get_education("user1", edu_id) is not None
