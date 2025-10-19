from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from zipfile import BadZipFile, ZipFile


class InvalidZipError(Exception):
    """Raised when the provided file cannot be processed as a valid ZIP archive."""


@dataclass(slots=True)
class FileNode:
    name: str
    path: str


@dataclass(slots=True)
class DirectoryNode:
    name: str
    path: str
    children: list[FileNode | DirectoryNode] = field(default_factory=list)


@dataclass(slots=True)
class ZipUploadResult:
    filename: str
    size_bytes: int
    file_count: int
    tree: DirectoryNode


def _get_ignore_patterns() -> set[str]:
    from capstone_project_team_5.consent_tool import ConsentTool

    return set(ConsentTool()._get_default_ignore_patterns())


def _is_ignored(segments: list[str], ignore_patterns: set[str]) -> bool:
    return any(part in ignore_patterns for part in segments)


def _ensure_zip_file(path: Path) -> None:
    if path.suffix.lower() != ".zip" or not path.is_file():
        raise InvalidZipError("Expected a .zip file")
    try:
        with ZipFile(path):
            pass
    except (BadZipFile, OSError) as exc:
        raise InvalidZipError("Provided file is not a valid ZIP archive") from exc


def _build_tree(names: Iterable[str], ignore_patterns: set[str]) -> DirectoryNode:
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


def upload_zip(zip_path: Path | str) -> ZipUploadResult:
    path = Path(zip_path)
    _ensure_zip_file(path)

    ignore_patterns = _get_ignore_patterns()

    with ZipFile(path) as archive:
        names = archive.namelist()

    tree = _build_tree(names, ignore_patterns)

    file_count = 0

    def _count_files(node: DirectoryNode | FileNode) -> None:
        nonlocal file_count
        if isinstance(node, FileNode):
            file_count += 1
            return
        for child in node.children:
            _count_files(child)

    _count_files(tree)

    return ZipUploadResult(
        filename=path.name,
        size_bytes=path.stat().st_size,
        file_count=file_count,
        tree=tree,
    )
