"""Data models for zip upload functionality."""

from __future__ import annotations

from dataclasses import dataclass, field


class InvalidZipError(Exception):
    """Raised when the provided file cannot be processed as a valid ZIP archive."""


@dataclass(slots=True)
class FileNode:
    """Represents a file in the directory tree.

    Attributes:
        name: Name of the file.
        path: Full path from root of the archive.
    """

    name: str
    path: str


@dataclass(slots=True)
class DirectoryNode:
    """Represents a directory in the tree structure.

    Attributes:
        name: Name of the directory.
        path: Full path from root of the archive.
        children: List of child nodes (files and subdirectories).
    """

    name: str
    path: str
    children: list[FileNode | DirectoryNode] = field(default_factory=list)


@dataclass(slots=True)
class ZipUploadResult:
    """Result of a successful zip upload operation.

    Attributes:
        filename: Name of the uploaded zip file.
        size_bytes: Size of the zip file in bytes.
        file_count: Number of files extracted (excluding ignored patterns).
        tree: Root directory node representing the file structure.
    """

    filename: str
    size_bytes: int
    file_count: int
    tree: DirectoryNode
