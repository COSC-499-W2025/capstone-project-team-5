"""File walker for extracted zip directories.

This module provides utilities to walk extracted zip directories and
collect files with ignore pattern support.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FileInfo:
    """Represents a file with its metadata.

    Attributes:
        path: Relative path from the root directory.
        absolute_path: Absolute path to the file.
        name: Name of the file.
        size_bytes: Size of the file in bytes.
    """

    path: str
    absolute_path: Path
    name: str
    size_bytes: int


@dataclass
class WalkResult:
    """Result of walking a directory tree.

    Attributes:
        root: Root directory that was walked.
        files: List of all files found.
        total_size_bytes: Total size of all files in bytes.
        ignore_patterns: Patterns that were used to filter files.
    """

    root: Path
    files: list[FileInfo] = field(default_factory=list)
    total_size_bytes: int = 0
    ignore_patterns: set[str] = field(default_factory=set)


class DirectoryWalker:
    """Walk extracted zip directories and collect file information."""

    @staticmethod
    def _get_default_ignore_patterns() -> set[str]:
        """Get default ignore patterns from capstone_project_team_5.utils.ignore_patterns.

        Returns:
            A set of default ignore pattern strings.
        """

        from capstone_project_team_5.utils.ignore_patterns import get_default_ignore_patterns

        return set(get_default_ignore_patterns())

    @staticmethod
    def _is_ignored(path: Path, root: Path, ignore_patterns: set[str]) -> bool:
        """Check if a path should be ignored based on patterns.

        Args:
            path: Path to check.
            root: Root directory for calculating relative path.
            ignore_patterns: Set of patterns to ignore.

        Returns:
            True if the path should be ignored.
        """
        try:
            rel_path = path.relative_to(root)
            parts = rel_path.parts
            return any(pattern in parts for pattern in ignore_patterns)
        except ValueError:
            return False

    @staticmethod
    def walk(
        directory: Path | str,
        ignore_patterns: set[str] | None = None,
    ) -> WalkResult:
        """Walk a directory and collect all files.

        Args:
            directory: Path to the directory to walk.
            ignore_patterns: Optional set of patterns to ignore. If None, uses defaults.

        Returns:
            WalkResult containing all files and statistics.

        Raises:
            ValueError: If directory doesn't exist or is not a directory.
        """
        root = Path(directory)
        if not root.exists() or not root.is_dir():
            raise ValueError(f"Invalid directory: {directory}")

        if ignore_patterns is None:
            ignore_patterns = DirectoryWalker._get_default_ignore_patterns()

        result = WalkResult(root=root, ignore_patterns=ignore_patterns)

        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue

            # Check if file should be ignored
            if DirectoryWalker._is_ignored(file_path, root, ignore_patterns):
                continue

            # Get file info
            try:
                size_bytes = file_path.stat().st_size
            except OSError:
                # Skip files we can't stat
                continue

            rel_path = file_path.relative_to(root)

            file_info = FileInfo(
                path=str(rel_path),
                absolute_path=file_path,
                name=file_path.name,
                size_bytes=size_bytes,
            )

            result.files.append(file_info)
            result.total_size_bytes += size_bytes

        return result

    @staticmethod
    def get_summary(result: WalkResult) -> dict[str, int]:
        """Get a summary dictionary from walk result.

        Args:
            result: WalkResult to summarize.

        Returns:
            Dictionary with total counts and sizes.
        """
        return {
            "total_files": len(result.files),
            "total_size_bytes": result.total_size_bytes,
        }
