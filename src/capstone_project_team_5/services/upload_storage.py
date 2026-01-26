"""Helpers for storing and retrieving uploaded ZIP archives."""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def get_upload_storage_root() -> Path:
    """Return the root directory for stored ZIP archives."""
    env_root = os.getenv("ZIP2JOB_UPLOAD_DIR")
    if env_root:
        return Path(env_root).expanduser().resolve()

    project_root = Path(__file__).resolve().parents[3]
    return project_root / ".zip2job_uploads"


def get_upload_zip_path(upload_id: int, filename: str) -> Path:
    """Return the expected path for a stored upload ZIP."""
    safe_name = Path(filename).name
    return get_upload_storage_root() / str(upload_id) / safe_name


def store_upload_zip(upload_id: int, filename: str, source_path: Path) -> Path:
    """Persist a ZIP archive for later analysis."""
    target_path = get_upload_zip_path(upload_id, filename)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target_path)
    return target_path
