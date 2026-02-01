"""Service helpers for project thumbnails stored on disk."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import Project
from capstone_project_team_5.services.upload_storage import get_upload_storage_root

MAX_THUMBNAIL_BYTES = 2 * 1024 * 1024
THUMBNAIL_DIR_NAME = "thumbnails"
THUMBNAIL_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")

IMAGE_TYPE_TO_MIME = {
    "png": "image/png",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
    "bmp": "image/bmp",
}
IMAGE_TYPE_TO_EXTENSION = {
    "png": ".png",
    "jpeg": ".jpg",
    "gif": ".gif",
    "webp": ".webp",
    "bmp": ".bmp",
}
CONTENT_TYPE_ALIASES = {
    "image/jpg": "image/jpeg",
    "image/pjpeg": "image/jpeg",
}
EXTENSION_TO_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
}


@dataclass(frozen=True)
class ThumbnailInfo:
    image_type: str
    mime_type: str
    extension: str


def get_thumbnail_storage_root() -> Path:
    """Return the root directory for stored thumbnails."""
    return get_upload_storage_root() / THUMBNAIL_DIR_NAME


def get_project_thumbnail_path(project_id: int) -> Path | None:
    """Return the stored thumbnail path for a project, if any."""
    root = get_thumbnail_storage_root()
    if not root.exists():
        return None
    for ext in THUMBNAIL_EXTENSIONS:
        candidate = root / f"{project_id}{ext}"
        if candidate.exists():
            return candidate
    return None


def get_thumbnail_media_type(path: Path) -> str | None:
    """Return the MIME type for a thumbnail path."""
    return EXTENSION_TO_MIME.get(path.suffix.lower())


def has_project_thumbnail(project_id: int) -> bool:
    """Return True if a thumbnail exists for the project."""
    return get_project_thumbnail_path(project_id) is not None


def set_project_thumbnail(
    project_id: int,
    *,
    filename: str | None,
    content_type: str | None,
    data: bytes,
) -> tuple[bool, str | None]:
    """Store a thumbnail for a project."""
    if not _project_exists(project_id):
        return False, "Project not found."

    try:
        info = _validate_thumbnail_upload(filename=filename, content_type=content_type, data=data)
    except ValueError as exc:
        return False, str(exc)

    try:
        root = get_thumbnail_storage_root()
        root.mkdir(parents=True, exist_ok=True)
        _delete_existing_thumbnails(project_id)
        target = root / f"{project_id}{info.extension}"
        target.write_bytes(data)
        return True, None
    except Exception:
        return False, "Failed to store thumbnail."


def clear_project_thumbnail(project_id: int) -> bool:
    """Remove the thumbnail for a project."""
    if not _project_exists(project_id):
        return False
    return _delete_existing_thumbnails(project_id)


def _delete_existing_thumbnails(project_id: int) -> bool:
    root = get_thumbnail_storage_root()
    removed = False
    for ext in THUMBNAIL_EXTENSIONS:
        path = root / f"{project_id}{ext}"
        if path.exists():
            path.unlink(missing_ok=True)
            removed = True
    return removed


def _project_exists(project_id: int) -> bool:
    with get_session() as session:
        return session.query(Project.id).filter(Project.id == project_id).first() is not None


def _normalize_content_type(content_type: str | None) -> str | None:
    if content_type is None:
        return None
    normalized = content_type.strip().lower()
    return CONTENT_TYPE_ALIASES.get(normalized, normalized)


def _detect_image_type(data: bytes) -> str | None:
    if len(data) >= 8 and data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if len(data) >= 3 and data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if len(data) >= 6 and data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if len(data) >= 2 and data[:2] == b"BM":
        return "bmp"
    return None


def _validate_thumbnail_upload(
    *, filename: str | None, content_type: str | None, data: bytes
) -> ThumbnailInfo:
    if not data:
        raise ValueError("Thumbnail file is empty.")
    if len(data) > MAX_THUMBNAIL_BYTES:
        raise ValueError("Thumbnail exceeds 2 MiB.")

    image_type = _detect_image_type(data)
    if image_type is None or image_type not in IMAGE_TYPE_TO_MIME:
        raise ValueError("Unsupported thumbnail image type.")

    normalized_type = _normalize_content_type(content_type)
    expected_mime = IMAGE_TYPE_TO_MIME[image_type]
    if normalized_type and normalized_type not in IMAGE_TYPE_TO_MIME.values():
        raise ValueError("Unsupported thumbnail content type.")
    if normalized_type and normalized_type != expected_mime:
        raise ValueError("Thumbnail content type does not match image data.")

    extension = IMAGE_TYPE_TO_EXTENSION[image_type]
    return ThumbnailInfo(image_type=image_type, mime_type=expected_mime, extension=extension)
