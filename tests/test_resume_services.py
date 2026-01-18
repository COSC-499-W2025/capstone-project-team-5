"""Test suite for resume service functions."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import capstone_project_team_5.data.db as db_module
from capstone_project_team_5.data.models import Base, Project, User
from capstone_project_team_5.data.models.upload_record import UploadRecord
from capstone_project_team_5.services.resume import (
    delete_resume,
    get_all_resumes,
    get_resume,
    save_resume,
    update_resume_bullets,
)


@pytest.fixture(scope="function")
def tmp_db(monkeypatch, tmp_path):
    """Create a temporary test database."""

    db_file = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_file}")
    TestingSessionLocal = sessionmaker(bind=engine)

    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(db_module, "_engine", engine)
    monkeypatch.setattr(db_module, "_SessionLocal", TestingSessionLocal)

    yield

    engine.dispose()


@pytest.fixture
def seeded_user_project(tmp_db):
    """Create a test user and project."""

    with db_module.get_session() as session:
        # User
        user = User(username="testuser", password_hash="hash")
        session.add(user)
        session.flush()

        # UploadRecord
        upload = UploadRecord(
            filename="test.zip",
            size_bytes=1234,
            file_count=3,
        )
        session.add(upload)
        session.flush()

        # Project linked to upload
        project = Project(
            upload_id=upload.id,
            name="Test Project",
            rel_path="test_project",
            has_git_repo=False,
            file_count=3,
            is_collaborative=False,
        )
        session.add(project)
        session.commit()

        return user.username, project.id


@pytest.fixture
def multiple_projects(tmp_db):
    """Create a user with multiple projects."""

    with db_module.get_session() as session:
        # User
        user = User(username="multiuser", password_hash="hash")
        session.add(user)
        session.flush()

        # Upload
        upload = UploadRecord(
            filename="multi.zip",
            size_bytes=5000,
            file_count=10,
        )
        session.add(upload)
        session.flush()

        # Multiple projects
        project_ids = []
        for i in range(3):
            project = Project(
                upload_id=upload.id,
                name=f"Project {i}",
                rel_path=f"project-{i}",
                has_git_repo=False,
                file_count=5,
                is_collaborative=False,
            )
            session.add(project)
            session.flush()
            project_ids.append(project.id)

        session.commit()
        return user.username, project_ids


class TestSaveResume:
    """Tests for save_resume function."""

    def test_save_new_resume(self, seeded_user_project):
        """Test saving a new resume project."""

        username, project_id = seeded_user_project

        success = save_resume(
            username=username,
            project_id=project_id,
            title="Python Web App",
            description="Flask application with PostgreSQL",
            bullet_points=[
                "Built RESTful API with Flask",
                "Implemented JWT authentication",
                "Designed database schema",
            ],
            analysis_snapshot=["Python", "Flask", "PostgreSQL", "Docker"],
        )

        assert success is True

        # Verify data was saved
        resume = get_resume(username, project_id)
        assert resume is not None
        assert resume["title"] == "Python Web App"
        assert resume["description"] == "Flask application with PostgreSQL"
        assert len(resume["bullet_points"]) == 3
        assert resume["bullet_points"][0] == "Built RESTful API with Flask"
        assert resume["analysis_snapshot"] == ["Python", "Flask", "PostgreSQL", "Docker"]

    def test_update_existing_resume(self, seeded_user_project):
        """Test updating an existing resume project."""

        username, project_id = seeded_user_project

        # Save initial version
        save_resume(
            username=username,
            project_id=project_id,
            title="Initial Title",
            description="Initial Description",
            bullet_points=["Bullet 1", "Bullet 2"],
            analysis_snapshot=["Python"],
        )

        # Update with new data
        success = save_resume(
            username=username,
            project_id=project_id,
            title="Updated Title",
            description="Updated Description",
            bullet_points=["New Bullet 1", "New Bullet 2", "New Bullet 3"],
            analysis_snapshot=["Python", "Flask"],
        )

        assert success is True

        # Verify update
        resume = get_resume(username, project_id)
        assert resume["title"] == "Updated Title"
        assert resume["description"] == "Updated Description"
        assert len(resume["bullet_points"]) == 3
        assert resume["bullet_points"][0] == "New Bullet 1"
        assert resume["analysis_snapshot"] == ["Python", "Flask"]

    def test_save_resume_nonexistent_user(self, seeded_user_project):
        """Test saving resume with non-existent user."""

        _, project_id = seeded_user_project

        success = save_resume(
            username="nonexistent_user",
            project_id=project_id,
            title="Test",
            description="Test",
            bullet_points=["Test"],
            analysis_snapshot=["Test"],
        )

        assert success is False

    def test_save_resume_nonexistent_project(self, seeded_user_project):
        """Test saving resume with non-existent project."""

        username, _ = seeded_user_project

        success = save_resume(
            username=username,
            project_id=99999,  # Non-existent project ID
            title="Test",
            description="Test",
            bullet_points=["Test"],
            analysis_snapshot=["Test"],
        )

        assert success is False

    def test_save_resume_empty_bullets(self, seeded_user_project):
        """Test saving resume with empty bullet points list."""

        username, project_id = seeded_user_project

        success = save_resume(
            username=username,
            project_id=project_id,
            title="No Bullets",
            description="Test",
            bullet_points=[],
            analysis_snapshot=["Python"],
        )

        assert success is True

        # Verify no bullets were created
        resume = get_resume(username, project_id)
        assert len(resume["bullet_points"]) == 0

    def test_save_resume_with_none_snapshot(self, seeded_user_project):
        """Test saving resume with None as analysis_snapshot."""

        username, project_id = seeded_user_project

        success = save_resume(
            username=username,
            project_id=project_id,
            title="Test",
            description="Test",
            bullet_points=["Bullet 1"],
            analysis_snapshot=None,
        )

        assert success is True

        resume = get_resume(username, project_id)
        assert resume["analysis_snapshot"] == []


class TestGetResume:
    """Tests for get_resume function."""

    def test_get_existing_resume(self, seeded_user_project):
        """Test retrieving an existing resume."""

        username, project_id = seeded_user_project

        save_resume(
            username=username,
            project_id=project_id,
            title="Python Web App",
            description="Flask application",
            bullet_points=["Bullet 1", "Bullet 2"],
            analysis_snapshot=["Python", "Flask"],
        )

        resume = get_resume(username, project_id)

        assert resume is not None
        assert resume["title"] == "Python Web App"
        assert resume["description"] == "Flask application"
        assert len(resume["bullet_points"]) == 2
        assert resume["bullet_points"][0] == "Bullet 1"
        assert resume["analysis_snapshot"] == ["Python", "Flask"]
        assert resume["project_id"] == project_id
        assert resume["project_name"] == "Test Project"
        assert resume["rel_path"] == "test_project"
        assert "created_at" in resume
        assert "updated_at" in resume
        assert "id" in resume
        assert "resume_id" in resume

    def test_get_nonexistent_resume(self, seeded_user_project):
        """Test retrieving a resume that doesn't exist."""

        username, project_id = seeded_user_project

        resume = get_resume(username, project_id)
        assert resume is None

    def test_get_resume_nonexistent_user(self, seeded_user_project):
        """Test retrieving resume with non-existent user."""

        _, project_id = seeded_user_project

        resume = get_resume("nonexistent_user", project_id)
        assert resume is None

    def test_get_resume_wrong_user(self, tmp_db, seeded_user_project):
        """Test that users can't access other users' resumes."""

        username, project_id = seeded_user_project

        # Create another user
        with db_module.get_session() as session:
            other_user = User(username="other_user", password_hash="hash")
            session.add(other_user)
            session.commit()

        # Save resume for username
        save_resume(
            username=username,
            project_id=project_id,
            title="Test",
            description="Test",
            bullet_points=["Test"],
            analysis_snapshot=["Python"],
        )

        # Try to get it as other_user
        resume = get_resume("other_user", project_id)
        assert resume is None


class TestDeleteResume:
    """Tests for delete_resume function."""

    def test_delete_existing_resume(self, seeded_user_project):
        """Test deleting an existing resume."""

        username, project_id = seeded_user_project

        # Save a resume first
        save_resume(
            username=username,
            project_id=project_id,
            title="Test",
            description="Test",
            bullet_points=["Bullet 1"],
            analysis_snapshot=["Python"],
        )

        # Verify it exists
        resume = get_resume(username, project_id)
        assert resume is not None

        # Delete it
        success = delete_resume(username, project_id)
        assert success is True

        # Verify it's gone
        resume = get_resume(username, project_id)
        assert resume is None

    def test_delete_nonexistent_resume(self, seeded_user_project):
        """Test deleting a resume that doesn't exist."""

        username, project_id = seeded_user_project

        success = delete_resume(username, project_id)
        assert success is False

    def test_delete_cascades_to_bullets(self, seeded_user_project):
        """Test that deleting resume also deletes bullet points."""

        username, project_id = seeded_user_project

        # Save resume with bullets
        save_resume(
            username=username,
            project_id=project_id,
            title="Test",
            description="Test",
            bullet_points=["Bullet 1", "Bullet 2", "Bullet 3"],
            analysis_snapshot=["Python"],
        )

        # Get bullet point count before deletion
        from capstone_project_team_5.data.models.resume import ResumeBulletPoint

        with db_module.get_session() as session:
            bullet_count_before = session.query(ResumeBulletPoint).count()
            assert bullet_count_before == 3

        # Delete resume
        delete_resume(username, project_id)

        # Verify bullets are also deleted
        with db_module.get_session() as session:
            bullet_count_after = session.query(ResumeBulletPoint).count()
            assert bullet_count_after == 0


class TestGetAllResumes:
    """Tests for get_all_resumes function."""

    def test_get_all_resumes_empty(self, seeded_user_project):
        """Test getting all resumes when user has none."""

        username, _ = seeded_user_project

        resumes = get_all_resumes(username)
        assert resumes == []

    def test_get_all_resumes_multiple(self, multiple_projects):
        """Test getting all resumes when user has multiple."""

        username, project_ids = multiple_projects

        # Save resumes for each project
        for i, proj_id in enumerate(project_ids):
            save_resume(
                username=username,
                project_id=proj_id,
                title=f"Resume {i}",
                description=f"Description {i}",
                bullet_points=[f"Bullet {i}"],
                analysis_snapshot=[f"Skill {i}"],
            )

        # Get all resumes
        resumes = get_all_resumes(username)
        assert len(resumes) == 3

        # Verify structure
        for resume in resumes:
            assert "id" in resume
            assert "title" in resume
            assert "description" in resume
            assert "project_name" in resume
            assert "bullet_points" in resume
            assert "analysis_snapshot" in resume
            assert "created_at" in resume
            assert "updated_at" in resume

    def test_get_all_resumes_nonexistent_user(self, tmp_db):
        """Test getting all resumes for non-existent user."""

        resumes = get_all_resumes("nonexistent_user")
        assert resumes == []

    def test_get_all_resumes_ordered_by_update(self, multiple_projects):
        """Test that resumes are ordered by updated_at descending."""

        username, project_ids = multiple_projects

        # Create resumes in order
        for i, proj_id in enumerate(project_ids):
            save_resume(
                username=username,
                project_id=proj_id,
                title=f"Resume {i}",
                description=f"Description {i}",
                bullet_points=[f"Bullet {i}"],
                analysis_snapshot=[f"Skill {i}"],
            )

        # Update the first one (should now be most recent)
        save_resume(
            username=username,
            project_id=project_ids[0],
            title="Updated Resume 0",
            description="Updated",
            bullet_points=["Updated"],
            analysis_snapshot=["Updated"],
        )

        resumes = get_all_resumes(username)
        # Most recently updated should be first
        assert resumes[0]["title"] == "Updated Resume 0"


class TestUpdateResumeBullets:
    """Tests for update_resume_bullets function."""

    def test_update_bullets(self, seeded_user_project):
        """Test updating only bullet points."""

        username, project_id = seeded_user_project

        # Save initial resume
        save_resume(
            username=username,
            project_id=project_id,
            title="Original Title",
            description="Original Description",
            bullet_points=["Old Bullet 1", "Old Bullet 2"],
            analysis_snapshot=["Python"],
        )

        # Update only bullets
        success = update_resume_bullets(
            username=username,
            project_id=project_id,
            bullet_points=["New Bullet 1", "New Bullet 2", "New Bullet 3"],
        )

        assert success is True

        # Verify bullets changed but title/description didn't
        resume = get_resume(username, project_id)
        assert resume["title"] == "Original Title"
        assert resume["description"] == "Original Description"
        assert len(resume["bullet_points"]) == 3
        assert resume["bullet_points"][0] == "New Bullet 1"

    def test_update_bullets_nonexistent_resume(self, seeded_user_project):
        """Test updating bullets for non-existent resume."""

        username, project_id = seeded_user_project

        success = update_resume_bullets(
            username=username,
            project_id=project_id,
            bullet_points=["Test"],
        )

        assert success is False

    def test_update_bullets_empty_list(self, seeded_user_project):
        """Test updating with empty bullet list."""

        username, project_id = seeded_user_project

        # Save initial resume
        save_resume(
            username=username,
            project_id=project_id,
            title="Test",
            description="Test",
            bullet_points=["Bullet 1", "Bullet 2"],
            analysis_snapshot=["Python"],
        )

        # Update with empty list
        success = update_resume_bullets(username=username, project_id=project_id, bullet_points=[])

        assert success is True

        # Verify bullets are removed
        resume = get_resume(username, project_id)
        assert len(resume["bullet_points"]) == 0


class TestResumeIntegration:
    """Integration tests combining multiple operations."""

    def test_full_resume_lifecycle(self, seeded_user_project):
        """Test complete lifecycle: create, read, update, delete."""

        username, project_id = seeded_user_project

        # Create
        success = save_resume(
            username=username,
            project_id=project_id,
            title="Initial Resume",
            description="Initial Description",
            bullet_points=["Bullet 1"],
            analysis_snapshot=["Python"],
        )
        assert success is True

        # Read
        resume = get_resume(username, project_id)
        assert resume is not None
        assert resume["title"] == "Initial Resume"

        # Update bullets
        success = update_resume_bullets(
            username, project_id, ["Updated Bullet 1", "Updated Bullet 2"]
        )
        assert success is True

        # Verify update
        resume = get_resume(username, project_id)
        assert len(resume["bullet_points"]) == 2

        # Update full resume
        success = save_resume(
            username=username,
            project_id=project_id,
            title="Updated Resume",
            description="Updated Description",
            bullet_points=["Final Bullet"],
            analysis_snapshot=["Python", "Flask"],
        )
        assert success is True

        # Verify final state
        resume = get_resume(username, project_id)
        assert resume["title"] == "Updated Resume"
        assert len(resume["bullet_points"]) == 1

        # Delete
        success = delete_resume(username, project_id)
        assert success is True

        # Verify deletion
        resume = get_resume(username, project_id)
        assert resume is None

    def test_multiple_users_separate_resumes(self, tmp_db, seeded_user_project):
        """Test that multiple users can have separate resumes for same project."""

        _, project_id = seeded_user_project

        # Create another user
        with db_module.get_session() as session:
            user1 = User(username="user1", password_hash="hash1")
            user2 = User(username="user2", password_hash="hash2")
            session.add(user1)
            session.add(user2)
            session.commit()

        # Both save resumes for same project
        save_resume(
            username="user1",
            project_id=project_id,
            title="User 1 Resume",
            description="User 1",
            bullet_points=["User 1 Bullet"],
            analysis_snapshot=["Python"],
        )

        save_resume(
            username="user2",
            project_id=project_id,
            title="User 2 Resume",
            description="User 2",
            bullet_points=["User 2 Bullet"],
            analysis_snapshot=["JavaScript"],
        )

        # Verify each user sees only their resume
        resume1 = get_resume("user1", project_id)
        resume2 = get_resume("user2", project_id)

        assert resume1["title"] == "User 1 Resume"
        assert resume2["title"] == "User 2 Resume"
        assert resume1["bullet_points"][0] == "User 1 Bullet"
        assert resume2["bullet_points"][0] == "User 2 Bullet"

    def test_resume_persists_across_sessions(self, seeded_user_project):
        """Test that resume data persists across multiple session operations."""

        username, project_id = seeded_user_project

        # Save in first "session"
        save_resume(
            username=username,
            project_id=project_id,
            title="Persistent Resume",
            description="Should persist",
            bullet_points=["Bullet 1", "Bullet 2"],
            analysis_snapshot=["Python", "Flask"],
        )

        # Read in second "session"
        resume1 = get_resume(username, project_id)
        assert resume1 is not None

        # Update in third "session"
        update_resume_bullets(username, project_id, ["New Bullet"])

        # Read again in fourth "session"
        resume2 = get_resume(username, project_id)
        assert len(resume2["bullet_points"]) == 1
        assert resume2["title"] == "Persistent Resume"  # Title unchanged
