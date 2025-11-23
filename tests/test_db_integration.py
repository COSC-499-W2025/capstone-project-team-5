from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from sqlalchemy.orm import Session

from capstone_project_team_5.data.db import Base, get_session, init_db
from capstone_project_team_5.data.models import ConsentRecord, UploadRecord


@contextmanager
def _temporary_db_url(url: str) -> Iterator[None]:
    original = os.getenv("DB_URL")
    os.environ["DB_URL"] = url
    try:
        yield
    finally:
        if original is None:
            os.environ.pop("DB_URL", None)
        else:
            os.environ["DB_URL"] = original


@pytest.fixture(autouse=True)
def in_memory_db() -> Iterator[None]:
    with _temporary_db_url("sqlite:///:memory:"):
        # Reset any cached engine/session factory so tests get a fresh in-memory DB
        import capstone_project_team_5.data.db as app_db

        app_db._engine = None
        app_db._SessionLocal = None

        init_db()
        yield


def _collect_consents(session: Session) -> list[ConsentRecord]:
    return session.query(ConsentRecord).all()


def _collect_uploads(session: Session) -> list[UploadRecord]:
    return session.query(UploadRecord).all()


def test_tables_created() -> None:
    assert {table.name for table in Base.metadata.sorted_tables} >= {
        "consent_records",
        "upload_records",
    }


def test_consent_record_persistence() -> None:
    sample = ConsentRecord(
        consent_given=True,
        use_external_services=False,
        external_services={"GitHub API": True},
        default_ignore_patterns=["node_modules"],
    )
    with get_session() as session:
        session.add(sample)

    with get_session() as session:
        rows = _collect_consents(session)

    assert len(rows) == 1
    stored = rows[0]
    assert stored.consent_given is True
    assert stored.use_external_services is False
    assert stored.external_services == {"GitHub API": True}
    assert stored.default_ignore_patterns == ["node_modules"]


def test_upload_record_persistence() -> None:
    sample = UploadRecord(
        filename="project.zip",
        size_bytes=1024,
        file_count=5,
    )
    with get_session() as session:
        session.add(sample)

    with get_session() as session:
        rows = _collect_uploads(session)

    assert len(rows) == 1
    stored = rows[0]
    assert stored.filename == "project.zip"
    assert stored.size_bytes == 1024
    assert stored.file_count == 5
