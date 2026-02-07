"""Content-addressed storage for uploaded file artifacts."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO
from zipfile import BadZipFile, ZipFile

from capstone_project_team_5.models.upload import InvalidZipError

_OBJECTS_DIR_NAME = "objects"
_MANIFESTS_DIR_NAME = "manifests"
_ANALYSIS_CACHE_DIR_NAME = "analysis_cache"
_STREAM_CHUNK_SIZE = 1024 * 1024


def get_artifact_store_root() -> Path:
    """Return root directory for content-addressed artifact storage."""
    env_root = os.getenv("ZIP2JOB_ARTIFACT_DIR")
    if env_root:
        return Path(env_root).expanduser().resolve()

    project_root = Path(__file__).resolve().parents[3]
    return project_root / ".zip2job_artifacts"


def get_objects_root() -> Path:
    """Return the objects root directory."""
    return get_artifact_store_root() / _OBJECTS_DIR_NAME


def get_manifests_root() -> Path:
    """Return the manifests root directory."""
    return get_artifact_store_root() / _MANIFESTS_DIR_NAME


def get_analysis_cache_root() -> Path:
    """Return the analysis cache root directory."""
    return get_artifact_store_root() / _ANALYSIS_CACHE_DIR_NAME


def _normalize_zip_path(name: str) -> str | None:
    normalized = name.replace("\\", "/").lstrip("/")
    if not normalized or normalized.endswith("/"):
        return None
    parts = PurePosixPath(normalized).parts
    if any(part in {"..", "."} for part in parts):
        return None
    return "/".join(part for part in parts if part)


def _hash_stream(source: BinaryIO) -> tuple[str, int]:
    hasher = hashlib.sha256()
    size = 0
    for chunk in iter(lambda: source.read(_STREAM_CHUNK_SIZE), b""):
        hasher.update(chunk)
        size += len(chunk)
    return hasher.hexdigest(), size


def _write_stream_and_hash(source: BinaryIO, destination: BinaryIO) -> tuple[str, int]:
    hasher = hashlib.sha256()
    size = 0
    for chunk in iter(lambda: source.read(_STREAM_CHUNK_SIZE), b""):
        destination.write(chunk)
        hasher.update(chunk)
        size += len(chunk)
    destination.flush()
    os.fsync(destination.fileno())
    return hasher.hexdigest(), size


def _object_path(content_hash: str) -> Path:
    prefix = content_hash[:2]
    return get_objects_root() / prefix / content_hash


def ingest_zip(zip_path: Path | str, upload_id: int) -> dict[str, Any]:
    """Ingest a zip file into the content store and write a manifest.

    Returns the manifest content as a dict.
    """
    path = Path(zip_path)
    if path.suffix.lower() != ".zip" or not path.is_file():
        raise InvalidZipError(f"Expected a .zip file. Received: {path.name}")

    manifest: dict[str, Any] = {
        "upload_id": upload_id,
        "created_at": datetime.now(UTC).isoformat(),
        "files": {},
    }

    objects_root = get_objects_root()
    objects_root.mkdir(parents=True, exist_ok=True)

    try:
        with ZipFile(path) as archive:
            for info in archive.infolist():
                normalized = _normalize_zip_path(info.filename)
                if normalized is None:
                    continue
                with archive.open(info) as source:
                    content_hash, size = _hash_stream(source)
                object_path = _object_path(content_hash)
                if not object_path.exists():
                    object_path.parent.mkdir(parents=True, exist_ok=True)
                    temp_path: Path | None = None
                    try:
                        with tempfile.NamedTemporaryFile(
                            mode="wb",
                            dir=object_path.parent,
                            suffix=".tmp",
                            delete=False,
                        ) as temp_file:
                            temp_path = Path(temp_file.name)
                            with archive.open(info) as source:
                                final_hash, final_size = _write_stream_and_hash(source, temp_file)
                        if final_hash != content_hash:
                            raise RuntimeError(
                                "Content hash mismatch while streaming archive entry."
                            )
                        if object_path.exists():
                            temp_path.unlink(missing_ok=True)
                        else:
                            os.replace(temp_path, object_path)
                        size = final_size
                        content_hash = final_hash
                    except Exception:
                        if temp_path is not None:
                            with contextlib.suppress(FileNotFoundError):
                                temp_path.unlink()
                        raise

                manifest["files"][normalized] = {
                    "hash": content_hash,
                    "size": size,
                }
    except BadZipFile as exc:
        raise InvalidZipError(f"{path.name} is not a valid ZIP archive") from exc

    manifests_root = get_manifests_root()
    manifests_root.mkdir(parents=True, exist_ok=True)
    manifest_path = manifests_root / f"{upload_id}.json"
    temp_manifest = manifest_path.with_suffix(".tmp")
    temp_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_manifest.replace(manifest_path)
    return manifest


def load_manifest(upload_id: int) -> dict[str, Any] | None:
    """Load a manifest for the given upload ID."""
    manifest_path = get_manifests_root() / f"{upload_id}.json"
    if not manifest_path.exists():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def materialize_project_tree(project_rel_path: str, upload_ids: list[int], dest_root: Path) -> Path:
    """Materialize a merged project tree from multiple uploads."""
    dest_root.mkdir(parents=True, exist_ok=True)
    project_rel_path = project_rel_path.strip("/")
    target_root = dest_root / project_rel_path if project_rel_path else dest_root

    for upload_id in upload_ids:
        manifest = load_manifest(upload_id)
        if not manifest:
            continue
        files: dict[str, dict[str, Any]] = manifest.get("files", {})
        for file_path, meta in files.items():
            if project_rel_path:
                prefix = f"{project_rel_path}/"
                if not file_path.startswith(prefix):
                    continue
                relative = file_path[len(prefix) :]
                if not relative:
                    continue
            else:
                relative = file_path

            safe_path = _normalize_zip_path(relative)
            if safe_path is None:
                continue
            dest_path = target_root / safe_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            content_hash = str(meta.get("hash", ""))
            if not content_hash:
                continue
            object_path = _object_path(content_hash)
            if not object_path.exists():
                continue
            if dest_path.exists():
                dest_path.unlink()
            dest_path.write_bytes(object_path.read_bytes())

    return target_root


def compute_project_fingerprint(project_rel_path: str, upload_ids: list[int]) -> str:
    """Compute a stable fingerprint for merged project content."""
    project_rel_path = project_rel_path.strip("/")
    merged: dict[str, tuple[str, int]] = {}
    for upload_id in upload_ids:
        manifest = load_manifest(upload_id)
        if not manifest:
            continue
        files: dict[str, dict[str, Any]] = manifest.get("files", {})
        for file_path, meta in files.items():
            if project_rel_path:
                prefix = f"{project_rel_path}/"
                if not file_path.startswith(prefix):
                    continue
                relative = file_path[len(prefix) :]
            else:
                relative = file_path
            safe_path = _normalize_zip_path(relative)
            if safe_path is None:
                continue
            content_hash = str(meta.get("hash", ""))
            size = int(meta.get("size", 0))
            merged[safe_path] = (content_hash, size)

    entries = sorted((path, data[0], data[1]) for path, data in merged.items())
    hasher = hashlib.sha256()
    for path, content_hash, size in entries:
        hasher.update(path.encode("utf-8"))
        hasher.update(b"\x00")
        hasher.update(content_hash.encode("utf-8"))
        hasher.update(b"\x00")
        hasher.update(str(size).encode("utf-8"))
        hasher.update(b"\x00")
    return hasher.hexdigest()


def compute_project_file_count(project_rel_path: str, upload_ids: list[int]) -> int:
    """Compute file count for the merged project view."""
    project_rel_path = project_rel_path.strip("/")
    merged: dict[str, tuple[str, int]] = {}
    for upload_id in upload_ids:
        manifest = load_manifest(upload_id)
        if not manifest:
            continue
        files: dict[str, dict[str, Any]] = manifest.get("files", {})
        for file_path, meta in files.items():
            if project_rel_path:
                prefix = f"{project_rel_path}/"
                if not file_path.startswith(prefix):
                    continue
                relative = file_path[len(prefix) :]
            else:
                relative = file_path
            safe_path = _normalize_zip_path(relative)
            if safe_path is None:
                continue
            content_hash = str(meta.get("hash", ""))
            size = int(meta.get("size", 0))
            merged[safe_path] = (content_hash, size)
    return len(merged)


def load_analysis_cache(project_id: int) -> dict[str, Any] | None:
    """Load cached analysis for a project."""
    cache_path = get_analysis_cache_root() / f"project_{project_id}.json"
    if not cache_path.exists():
        return None
    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def write_analysis_cache(project_id: int, fingerprint: str, payload: dict[str, Any]) -> None:
    """Persist analysis cache for a project."""
    cache_root = get_analysis_cache_root()
    cache_root.mkdir(parents=True, exist_ok=True)
    cache_path = cache_root / f"project_{project_id}.json"
    temp_path = cache_path.with_suffix(".tmp")
    cache_payload = {
        "project_id": project_id,
        "fingerprint": fingerprint,
        "created_at": datetime.now(UTC).isoformat(),
        "payload": payload,
    }
    temp_path.write_text(json.dumps(cache_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(cache_path)
