"""Service for handling incremental uploads of project artifacts."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile

from sqlalchemy import func

from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import ArtifactSource, Project, UploadRecord
from capstone_project_team_5.models.upload import ZipUploadResult
from capstone_project_team_5.services.upload import upload_zip as _upload_zip


def find_matching_projects(
    detected_projects: list[str],
) -> dict[str, list[int]]:
    """Find existing projects in the database by name.

    Args:
        detected_projects: List of project names detected in the new upload.

    Returns:
        Dictionary mapping project names to lists of matching project IDs.
    """
    matches: dict[str, list[int]] = {}

    with get_session() as session:
        for project_name in detected_projects:
            normalized_name = project_name.lower()
            found_projects = (
                session.query(Project).filter(func.lower(Project.name) == normalized_name).all()
            )
            if found_projects:
                matches[project_name] = [p.id for p in found_projects]

    return matches


def incremental_upload_zip(
    zip_path: Path | str,
    project_mapping: dict[str, int] | None = None,
) -> tuple[ZipUploadResult, list[tuple[int, int]]]:
    """Upload a ZIP file, optionally appending to existing projects.

    This function performs a standard ZIP upload, then optionally associates
    the new upload with existing projects via ArtifactSource records. This
    enables incremental additions to portfolios/résumés.

    Args:
        zip_path: Path to the zip file.
        project_mapping: Optional dict mapping detected project names to existing
                        project IDs to append to. If a detected project is in this
                        mapping, it will be associated with the existing project
                        instead of creating a new one. Format: {"project_name": project_id}

    Returns:
        Tuple of:
            - ZipUploadResult: The upload result (with newly created projects)
            - List of (existing_project_id, new_upload_id) tuples for incremental
              associations. Empty list if no incremental updates were made.
    """
    # Perform standard upload
    result = _upload_zip(zip_path)

    # If no mapping provided, return early
    if not project_mapping:
        return result, []

    incremental_associations: list[tuple[int, int]] = []

    with get_session() as session:
        # Get the upload record that was just created
        upload_record = (
            session.query(UploadRecord)
            .filter(UploadRecord.filename == result.filename)
            .order_by(UploadRecord.created_at.desc())
            .first()
        )

        if not upload_record:
            return result, []

        upload_id = upload_record.id

        # For each detected project, check if it should be appended to an
        # existing project
        for detected_project in result.projects:
            if detected_project.name in project_mapping:
                existing_project_id = project_mapping[detected_project.name]
                existing_project = (
                    session.query(Project).filter(Project.id == existing_project_id).first()
                )

                if existing_project:
                    # Create ArtifactSource record linking this upload to the
                    # existing project
                    artifact_source = ArtifactSource(
                        project_id=existing_project_id,
                        upload_id=upload_id,
                        artifact_count=detected_project.file_count,
                    )
                    session.add(artifact_source)
                    incremental_associations.append((existing_project_id, upload_id))

                    # Update the existing project's file count
                    existing_project.file_count += detected_project.file_count
                    existing_project.updated_at = datetime.now(UTC)

        session.commit()

    return result, incremental_associations


def get_project_uploads(project_id: int) -> list[dict[str, any]]:
    """Get all uploads that contributed to a project (both original and incremental).

    Args:
        project_id: ID of the project.

    Returns:
        List of dicts containing upload information and artifact counts.
    """
    uploads_info: list[dict[str, any]] = []

    with get_session() as session:
        project = session.query(Project).filter(Project.id == project_id).first()

        if not project:
            return uploads_info

        # The initial upload
        initial_upload = project.upload
        uploads_info.append(
            {
                "upload_id": initial_upload.id,
                "filename": initial_upload.filename,
                "file_count": initial_upload.file_count,
                "created_at": initial_upload.created_at,
                "artifact_count": None,  # All files from initial upload
                "is_incremental": False,
            }
        )

        # Incremental uploads
        for artifact_source in project.artifact_sources:
            upload = artifact_source.upload
            uploads_info.append(
                {
                    "upload_id": upload.id,
                    "filename": upload.filename,
                    "file_count": upload.file_count,
                    "created_at": upload.created_at,
                    "artifact_count": artifact_source.artifact_count,
                    "is_incremental": True,
                }
            )

    return uploads_info


def extract_and_merge_files(
    zip_path: Path | str,
    target_dir: Path,
    project_name: str,
) -> int:
    """Extract ZIP contents and merge into target directory.

    Args:
        zip_path: Path to the zip file.
        target_dir: Target directory to merge files into.
        project_name: Name of the project (for organizing files).

    Returns:
        Number of files extracted.

    Raises:
        InvalidZipError: If the file is not a valid zip archive.
    """
    from capstone_project_team_5.models.upload import InvalidZipError

    zip_path = Path(zip_path)
    if zip_path.suffix.lower() != ".zip" or not zip_path.is_file():
        raise InvalidZipError(f"Expected a .zip file. Received: {zip_path.name}")

    target_dir.mkdir(parents=True, exist_ok=True)
    project_dir = target_dir / project_name
    project_dir.mkdir(parents=True, exist_ok=True)

    index_path = target_dir / ".dedupe_index.json"
    # Load existing dedupe index if present; structure: {"hash": "relative/path"}
    dedupe_index: dict[str, str] = {}
    if index_path.exists():
        try:
            dedupe_index = json.loads(index_path.read_text(encoding="utf-8"))
        except Exception:
            dedupe_index = {}

    def compute_content_hash(data: bytes) -> str:
        """Compute a stable content hash for deduplication (SHA-256 hex)."""
        h = hashlib.sha256()
        h.update(data)
        return h.hexdigest()

    def _unique_target_path(base_dir: Path, filename: str, content_hash: str) -> Path:
        candidate = base_dir / filename
        if not candidate.exists():
            return candidate
        # If a file exists with same name but different content, disambiguate
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        alt_name = f"{stem}-{content_hash[:8]}{suffix}"
        alt_candidate = base_dir / alt_name

        # Check if the alternative name already exists (edge case: hash prefix collision)
        if not alt_candidate.exists():
            return alt_candidate

        # If alt_name also exists, append counter to ensure uniqueness
        counter = 1
        while True:
            numbered_name = f"{stem}-{content_hash[:8]}-{counter}{suffix}"
            numbered_candidate = base_dir / numbered_name
            if not numbered_candidate.exists():
                return numbered_candidate
            counter += 1

    written_count = 0
    files_manifest: list[dict[str, any]] = []

    with ZipFile(zip_path) as archive:
        for info in archive.infolist():
            if info.filename.endswith("/"):
                continue

            # Read file bytes and compute content hash
            with archive.open(info) as source:
                data = source.read()
            content_hash = compute_content_hash(data)

            filename = Path(info.filename).name
            actual_location = None

            # Skip writing if this exact content already exists in the system
            if content_hash in dedupe_index:
                # Validate that the indexed file actually exists and has correct size
                indexed_path = target_dir / dedupe_index[content_hash]
                if indexed_path.exists() and indexed_path.stat().st_size == len(data):
                    # File is deduplicated, track it but don't write
                    is_deduplicated = True
                    actual_location = dedupe_index[content_hash]
                    files_manifest.append(
                        {
                            "filename": filename,
                            "path": filename,
                            "is_deduplicated": True,
                            "actual_location": actual_location,
                            "hash": content_hash,
                        }
                    )
                    continue
                # If file doesn't exist or size mismatch, remove from index and continue to write
                del dedupe_index[content_hash]

            # Write the file (either new or recovering from corruption)
            target_path = _unique_target_path(project_dir, filename, content_hash)
            target_path.write_bytes(data)

            # Record into system-level dedupe index using project-relative path
            rel_record_path = str(target_path.relative_to(target_dir))
            dedupe_index[content_hash] = rel_record_path
            written_count += 1

            # Record in manifest
            files_manifest.append(
                {
                    "filename": filename,
                    "path": str(target_path.relative_to(project_dir)),
                    "is_deduplicated": False,
                    "hash": content_hash,
                }
            )

    # Persist the dedupe index
    try:
        index_path.write_text(
            json.dumps(dedupe_index, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except (OSError, json.JSONDecodeError) as e:
        logger = logging.getLogger(__name__)
        logger.warning(
            f"Failed to persist dedupe index at {index_path}: {e}. "
            "Deduplication may not work optimally in future uploads."
        )

    # Persist the files manifest
    try:
        manifest_path = project_dir / ".files_manifest.json"
        manifest_path.write_text(
            json.dumps(files_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except (OSError, json.JSONDecodeError) as e:
        logger = logging.getLogger(__name__)
        logger.warning(
            f"Failed to persist files manifest at {project_dir}: {e}. "
            "File metadata tracking may be incomplete."
        )

    return written_count
