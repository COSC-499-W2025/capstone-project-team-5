"""Service helpers for project thumbnail URLs."""

from __future__ import annotations

from pathlib import PurePosixPath
from urllib.parse import urlparse

from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import Project

ALLOWED_URL_SCHEMES = {"http", "https"}
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}


def set_project_thumbnail_url(project_id: int, thumbnail_url: str) -> bool:
    """Set the thumbnail URL on a project."""

    url = thumbnail_url.strip()
    if not url:
        return False

    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_URL_SCHEMES or not parsed.netloc:
        return False
    extension = PurePosixPath(parsed.path).suffix.lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        return False

    try:
        with get_session() as session:
            project = session.query(Project).filter(Project.id == project_id).first()
            if project is None:
                return False

            project.thumbnail_url = url
            return True
    except Exception:
        return False


def get_project_thumbnail_url(project_id: int) -> str | None:
    """Return the thumbnail URL for a project."""

    try:
        with get_session() as session:
            project = session.query(Project).filter(Project.id == project_id).first()
            if project is None:
                return None
            return project.thumbnail_url
    except Exception:
        return None


def clear_project_thumbnail_url(project_id: int) -> bool:
    """Clear the thumbnail URL for a project."""

    try:
        with get_session() as session:
            project = session.query(Project).filter(Project.id == project_id).first()
            if project is None:
                return False

            if project.thumbnail_url is None:
                return False

            project.thumbnail_url = None
            return True
    except Exception:
        return False
