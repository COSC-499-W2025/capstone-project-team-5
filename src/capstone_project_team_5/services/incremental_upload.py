"""Service for handling incremental uploads of project artifacts."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

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
            found_projects = (
                session.query(Project).filter(Project.name == project_name).all()
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
                    existing_project.updated_at = __import__(
                        "datetime"
                    ).datetime.now(__import__("datetime").UTC)

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

    file_count = 0

    with ZipFile(zip_path) as archive:
        for info in archive.infolist():
            if info.filename.endswith("/"):
                continue

            # Extract to project subdirectory
            target_path = project_dir / Path(info.filename).name

            with archive.open(info) as source, open(target_path, "wb") as target:
                target.write(source.read())

            file_count += 1

    return file_count
