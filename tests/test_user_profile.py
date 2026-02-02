"""Test suite for UserProfile, Education, and WorkExperience models."""

from __future__ import annotations

import json
from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

import capstone_project_team_5.data.db as db_module
from capstone_project_team_5.data.models import Base, Education, User, UserProfile, WorkExperience


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
def user_id(tmp_db):
    """Create a test user and return its ID."""
    with db_module.get_session() as s:
        u = User(username="testuser", password_hash="hash")
        s.add(u)
        s.commit()
        return u.id


class TestUserProfile:
    """Tests for UserProfile model."""

    def test_create_and_relationship(self, user_id):
        """Test creating profile and user back-reference."""
        with db_module.get_session() as s:
            s.add(UserProfile(user_id=user_id, first_name="John", email="j@x.com"))
            s.commit()
            assert s.get(User, user_id).profile.first_name == "John"

    def test_unique_constraint(self, user_id):
        """Test only one profile per user."""
        with db_module.get_session() as s:
            s.add(UserProfile(user_id=user_id))
            s.commit()
        with pytest.raises(IntegrityError), db_module.get_session() as s:
            s.add(UserProfile(user_id=user_id))
            s.commit()

    def test_cascade_delete(self, user_id):
        """Test profile deleted with user."""
        with db_module.get_session() as s:
            s.add(UserProfile(user_id=user_id))
            s.commit()
        with db_module.get_session() as s:
            s.delete(s.get(User, user_id))
            s.commit()
        with db_module.get_session() as s:
            assert s.execute(select(UserProfile)).scalar_one_or_none() is None


class TestEducation:
    """Tests for Education model."""

    def test_create_with_fields(self, user_id):
        """Test creating education with all fields."""
        with db_module.get_session() as s:
            e = Education(
                user_id=user_id,
                institution="MIT",
                degree="BS",
                field_of_study="CS",
                gpa=3.8,
                start_date=date(2018, 9, 1),
                achievements=json.dumps(["Honor"]),
            )
            s.add(e)
            s.commit()
            assert e.id and e.gpa == 3.8

    def test_ordering_and_rank_validation(self, user_id):
        """Test rank ordering and validation."""
        with db_module.get_session() as s:
            s.add_all(
                [
                    Education(user_id=user_id, institution="B", degree="BS", rank=1),
                    Education(user_id=user_id, institution="A", degree="MS", rank=0),
                ]
            )
            s.commit()
            q = select(Education).where(Education.user_id == user_id).order_by(Education.rank)
            assert [e.institution for e in s.execute(q).scalars()] == ["A", "B"]
        with pytest.raises(ValueError, match="Rank"):
            Education(user_id=user_id, institution="X", degree="Y", rank=-1)

    def test_cascade_delete(self, user_id):
        """Test education deleted with user."""
        with db_module.get_session() as s:
            s.add(Education(user_id=user_id, institution="X", degree="Y"))
            s.commit()
        with db_module.get_session() as s:
            s.delete(s.get(User, user_id))
            s.commit()
        with db_module.get_session() as s:
            assert s.execute(select(Education)).scalar_one_or_none() is None


class TestWorkExperience:
    """Tests for WorkExperience model."""

    def test_create_with_fields(self, user_id):
        """Test creating work experience with all fields."""
        with db_module.get_session() as s:
            w = WorkExperience(
                user_id=user_id,
                company="Google",
                title="SWE",
                location="MTV",
                start_date=date(2022, 6, 1),
                bullets=json.dumps(["Built X"]),
                is_current=True,
            )
            s.add(w)
            s.commit()
            assert w.id and w.is_current

    def test_ordering_and_rank_validation(self, user_id):
        """Test rank ordering and validation."""
        with db_module.get_session() as s:
            s.add_all(
                [
                    WorkExperience(user_id=user_id, company="B", title="R2", rank=1),
                    WorkExperience(user_id=user_id, company="A", title="R1", rank=0),
                ]
            )
            s.commit()
            q = select(WorkExperience).where(WorkExperience.user_id == user_id)
            assert [w.company for w in s.execute(q.order_by(WorkExperience.rank)).scalars()] == [
                "A",
                "B",
            ]
        with pytest.raises(ValueError, match="Rank"):
            WorkExperience(user_id=user_id, company="X", title="Y", rank=-1)

    def test_cascade_delete(self, user_id):
        """Test work experience deleted with user."""
        with db_module.get_session() as s:
            s.add(WorkExperience(user_id=user_id, company="X", title="Y"))
            s.commit()
        with db_module.get_session() as s:
            s.delete(s.get(User, user_id))
            s.commit()
        with db_module.get_session() as s:
            assert s.execute(select(WorkExperience)).scalar_one_or_none() is None


class TestUserRelationships:
    """Tests for User relationships."""

    def test_user_has_all_relationships(self, user_id):
        """Test user has profile, education, and work experience."""
        with db_module.get_session() as s:
            s.add_all(
                [
                    UserProfile(user_id=user_id, first_name="T"),
                    Education(user_id=user_id, institution="U", degree="BS"),
                    WorkExperience(user_id=user_id, company="C", title="T"),
                ]
            )
            s.commit()
            u = s.get(User, user_id)
            assert u.profile and len(u.education_entries) == 1 and len(u.work_experiences) == 1
