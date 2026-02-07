"""Zip file upload and processing service."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import BadZipFile, ZipFile

from capstone_project_team_5.collab_detect import CollabDetector
from capstone_project_team_5.models.upload import (
    DetectedProject,
    DirectoryNode,
    FileNode,
    InvalidZipError,
    ZipUploadResult,
)


def _get_ignore_patterns() -> set[str]:
    """Get default ignore patterns."""
    from capstone_project_team_5.utils.ignore_patterns import get_default_ignore_patterns

    return set(get_default_ignore_patterns())


def _is_ignored(segments: list[str], ignore_patterns: set[str]) -> bool:
    """Check if any segment in the path matches ignore patterns.

    Args:
        segments: List of path segments.
        ignore_patterns: Set of patterns to ignore.

    Returns:
        True if any segment should be ignored.
    """
    return any(part in ignore_patterns for part in segments)


def _ensure_zip_file(path: Path) -> None:
    """Validate that the given path is a valid zip file.

    Args:
        path: Path to validate.

    Raises:
        InvalidZipError: If file is not a valid zip or doesn't exist.
    """
    if path.suffix.lower() != ".zip" or not path.is_file():
        raise InvalidZipError(f"Expected a .zip file. Received: {path.name}")
    try:
        with ZipFile(path):
            pass
    except (BadZipFile, OSError) as exc:
        raise InvalidZipError(f"{path.name} is not a valid ZIP archive") from exc


def _build_tree(names: Iterable[str], ignore_patterns: set[str]) -> DirectoryNode:
    """Build directory tree from zip file entries.

    Args:
        names: List of file/directory names from zip archive.
        ignore_patterns: Patterns to exclude from tree.

    Returns:
        Root DirectoryNode representing the tree structure.
    """
    root = DirectoryNode(name="", path="", children=[])
    nodes: dict[str, DirectoryNode] = {"": root}

    def _get_directory(path: str) -> DirectoryNode:
        if path not in nodes:
            parent_path, _, name = path.rpartition("/")
            parent = _get_directory(parent_path)
            node = DirectoryNode(name=name, path=path, children=[])
            parent.children.append(node)
            nodes[path] = node
        return nodes[path]

    for full_name in names:
        normalized = full_name.strip("/")
        if not normalized:
            continue
        segments = normalized.split("/")
        if _is_ignored(segments, ignore_patterns):
            continue

        if normalized.endswith("/"):
            directory_path = normalized[:-1]
            _get_directory(directory_path)
            continue

        parent_segments = segments[:-1]
        file_name = segments[-1]
        parent_path = "/".join(parent_segments)
        directory = _get_directory(parent_path)
        file_path = "/".join(segments)
        directory.children.append(FileNode(name=file_name, path=file_path))

    def _sort_children(directory: DirectoryNode) -> None:
        directory.children.sort(
            key=lambda node: (0 if isinstance(node, DirectoryNode) else 1, node.name)
        )
        for child in directory.children:
            if isinstance(child, DirectoryNode):
                _sort_children(child)

    _sort_children(root)
    return root


def _count_files(node: DirectoryNode | FileNode) -> int:
    """Recursively count all files in the tree.

    Args:
        node: Root node to count from.

    Returns:
        Total number of files.
    """
    if isinstance(node, FileNode):
        return 1
    return sum(_count_files(child) for child in node.children)


def _collect_zip_entries(
    names: Iterable[str], ignore_patterns: set[str]
) -> tuple[list[tuple[str, list[str]]], list[tuple[str, list[str]]]]:
    """Split zip namelist entries into files and directories.

    Args:
        names: Zip archive namelist.
        ignore_patterns: Patterns to ignore.

    Returns:
        Tuple of (files, directories) where each entry is (path, segments).
    """

    files: list[tuple[str, list[str]]] = []
    directories: list[tuple[str, list[str]]] = []

    for raw_name in names:
        normalized = raw_name.strip("/")
        if not normalized:
            continue

        segments = normalized.split("/")
        if _is_ignored(segments, ignore_patterns):
            continue

        if normalized.endswith("/"):
            directories.append((normalized[:-1], segments[:-1]))
            continue

        files.append((normalized, segments))

    return files, directories


def _is_doc_file(filename: str) -> bool:
    """Return True when *filename* looks like a documentation artifact."""

    doc_extensions = {".md", ".mdx", ".txt", ".pdf", ".docx", ".pptx"}
    lowered = filename.lower()
    return any(lowered.endswith(ext) for ext in doc_extensions)


def _is_media_file(filename: str) -> bool:
    """Return True when *filename* looks like a media artifact."""

    media_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".svg",
        ".mp4",
        ".mov",
        ".wav",
        ".mp3",
    }
    lowered = filename.lower()
    return any(lowered.endswith(ext) for ext in media_extensions)


def _discover_projects(names: list[str], ignore_patterns: set[str]) -> list[DetectedProject]:
    """Discover individual projects contained within the uploaded ZIP."""

    detection_ignore = {pattern for pattern in ignore_patterns if pattern != ".git"}
    files, directories = _collect_zip_entries(names, detection_ignore)

    top_level_dirs = {
        segments[0] for _, segments in files if len(segments) > 1 and segments[0] != ".git"
    }
    top_level_dirs.update(
        dir_path
        for dir_path, segments in directories
        if segments and len(segments) == 1 and segments[0] != ".git"
    )

    root_doc_files: list[str] = []
    root_media_files: list[str] = []

    for _, segments in files:
        if len(segments) != 1:
            continue
        if segments[0] == ".git":
            continue
        filename = segments[0]
        if _is_doc_file(filename):
            root_doc_files.append(filename)
        elif _is_media_file(filename):
            root_media_files.append(filename)

    git_project_paths: set[str] = set()

    for _, segments in directories:
        if segments and segments[-1] == ".git":
            candidate = "/".join(segments[:-1])
            if candidate:
                git_project_paths.add(candidate)

    for _, segments in files:
        if ".git" in segments:
            idx = segments.index(".git")
            candidate = "/".join(segments[:idx])
            if candidate:
                git_project_paths.add(candidate)

    project_paths = {path for path in top_level_dirs if path}
    project_paths.update(git_project_paths)

    discovered: list[DetectedProject] = []

    for project_path in sorted(project_paths):
        project_segments = project_path.split("/")
        project_files: list[list[str]] = []

        for _, segments in files:
            if len(segments) <= len(project_segments):
                continue
            if segments[: len(project_segments)] != project_segments:
                continue
            rel_segments = segments[len(project_segments) :]
            if ".git" in rel_segments:
                continue
            project_files.append(rel_segments)

        file_count = len(project_files)
        if file_count == 0:
            continue

        has_git = project_path in git_project_paths

        project_name = project_segments[-1]
        discovered.append(
            DetectedProject(
                name=project_name,
                rel_path=project_path,
                has_git_repo=has_git,
                file_count=file_count,
            )
        )

    if root_doc_files:
        discovered.append(
            DetectedProject(
                name="docs",
                rel_path="",
                has_git_repo=False,
                file_count=len(root_doc_files),
            )
        )

    if root_media_files:
        discovered.append(
            DetectedProject(
                name="media",
                rel_path="",
                has_git_repo=False,
                file_count=len(root_media_files),
            )
        )

    return discovered


def inspect_zip(zip_path: Path | str) -> tuple[ZipUploadResult, dict[str, bool]]:
    """Inspect a zip file and return its structured metadata.

    Args:
        zip_path: Path to the zip file.

    Returns:
        Tuple of:
            - ZipUploadResult containing metadata and tree structure.
            - Dict mapping project rel_path -> is_collaborative.

    Raises:
        InvalidZipError: If the file is not a valid zip archive.
    """
    path = Path(zip_path)
    _ensure_zip_file(path)

    ignore_patterns = _get_ignore_patterns()

    with ZipFile(path) as archive:
        names = archive.namelist()

    tree = _build_tree(names, ignore_patterns)
    file_count = _count_files(tree)
    projects = _discover_projects(names, ignore_patterns)

    # Determine collaboration flags using the extracted archive contents.
    collab_flags: dict[str, bool] = {}
    with TemporaryDirectory() as temp_dir_str:
        extract_root = Path(temp_dir_str)
        with ZipFile(path) as archive:
            archive.extractall(extract_root)

        for project in projects:
            if not project.rel_path:
                # Pseudo-projects like "docs" and "media" are treated as individual.
                collab_flags[project.rel_path] = False
                continue

            project_root = extract_root.joinpath(*project.rel_path.split("/"))
            if project_root.is_dir():
                try:
                    collab_flags[project.rel_path] = CollabDetector.is_collaborative(project_root)
                except Exception:
                    collab_flags[project.rel_path] = False
            else:
                collab_flags[project.rel_path] = False

    result = ZipUploadResult(
        filename=path.name,
        size_bytes=path.stat().st_size,
        file_count=file_count,
        tree=tree,
        projects=projects,
    )
    return result, collab_flags


def upload_zip(zip_path: Path | str) -> ZipUploadResult:
    """Process a zip file, extract its structure, and persist metadata.

    Args:
        zip_path: Path to the zip file.

    Returns:
        ZipUploadResult containing metadata and tree structure.

    Raises:
        InvalidZipError: If the file is not a valid zip archive.
    """
    from capstone_project_team_5.data.db import get_session
    from capstone_project_team_5.data.models import Project, UploadRecord

    result, collab_flags = inspect_zip(zip_path)

    with get_session() as session:
        upload_record = UploadRecord(
            filename=result.filename,
            size_bytes=result.size_bytes,
            file_count=result.file_count,
        )
        session.add(upload_record)
        session.flush()

        for project in result.projects:
            session.add(
                Project(
                    upload_id=upload_record.id,
                    name=project.name,
                    rel_path=project.rel_path,
                    has_git_repo=project.has_git_repo,
                    file_count=project.file_count,
                    is_collaborative=collab_flags.get(project.rel_path, False),
                )
            )

    return result
