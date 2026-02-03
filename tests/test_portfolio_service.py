import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import capstone_project_team_5.data.db as db_module
from capstone_project_team_5.data.models import Base, Project, User
from capstone_project_team_5.data.models.upload_record import UploadRecord
from capstone_project_team_5.services.portfolio import (
    get_portfolio_item,
    save_portfolio_item,
)


@pytest.fixture(scope="function")
def tmp_db(monkeypatch, tmp_path):
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


def test_save_new_portfolio_item(seeded_user_project):
    username, project_id = seeded_user_project

    result = save_portfolio_item(
        username=username,
        project_id=project_id,
        title="My Portfolio Item",
        content="Some content",
        is_user_edited=True,
    )

    assert result is True

    item = get_portfolio_item(username, project_id)
    assert item is not None
    assert item["title"] == "My Portfolio Item"
    assert item["content"] == "Some content"
    assert item["is_user_edited"] is True


def test_update_existing_portfolio_item(seeded_user_project):
    username, project_id = seeded_user_project

    save_portfolio_item(
        username=username,
        project_id=project_id,
        title="Original Title",
        content="Some content",
        is_user_edited=True,
    )

    result = save_portfolio_item(
        username=username,
        project_id=project_id,
        title="Updated Title",
        content="Updated content",
        is_user_edited=False,
    )

    assert result is True

    item = get_portfolio_item(username, project_id)
    assert item["title"] == "Updated Title"
    assert item["content"] == "Updated content"
    assert item["is_user_edited"] is False
    assert item["updated_at"] is not None


def test_save_portfolio_item_user_not_found(tmp_db):
    result = save_portfolio_item(
        username="missing_user",
        project_id=1,
        title="Should Fail",
        content="No user",
    )

    assert result is False


def test_get_portfolio_item_not_found(seeded_user_project):
    username, project_id = seeded_user_project

    item = get_portfolio_item(username, project_id)
    assert item is None
