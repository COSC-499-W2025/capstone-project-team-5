"""
File diff checker based on file name and size.

A standalone module for creating snapshots of project files and comparing them
to detect added, removed, and modified files. No external dependencies required.

"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

# Directories to skip during scanning
SKIP_DIRS = {
    "node_modules",
    "vendor",
    "packages",
    "bower_components",
    "venv",
    ".venv",
    "env",
    ".env",
    "virtualenv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    ".git",
    ".svn",
    ".hg",
    ".idea",
    ".vscode",
    ".vs",
    "build",
    "dist",
    "out",
    "target",
    ".next",
    ".nuxt",
    ".gradle",
    ".cache",
    "coverage",
    ".nyc_output",
}


class DiffResult(TypedDict):
    """Result of comparing two snapshots."""

    added: list[str]
    removed: list[str]
    modified: list[str]
    unchanged: list[str]


@dataclass
class FileSnapshot:
    """A snapshot of files in a project directory (path -> size mapping)."""

    root: str
    files: dict[str, int] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, object]:
        """Convert snapshot to a dictionary for serialization."""
        return {
            "root": self.root,
            "files": self.files,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> FileSnapshot:
        """Create a snapshot from a dictionary."""
        return cls(
            root=str(data.get("root", "")),
            files=dict(data.get("files", {})),  # type: ignore[arg-type]
            created_at=str(data.get("created_at", "")),
        )

    def save(self, path: Path) -> None:
        """Save snapshot to a JSON file.

        Args:
            path: Path to save the snapshot file.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> FileSnapshot:
        """Load a snapshot from a JSON file.

        Args:
            path: Path to the snapshot file.

        Returns:
            FileSnapshot loaded from the file.

        Raises:
            FileNotFoundError: If the snapshot file doesn't exist.
            json.JSONDecodeError: If the file is not valid JSON.
        """
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)


class FileDiffChecker:
    """Creates and compares file snapshots for a project."""

    def __init__(self, skip_dirs: set[str] | None = None) -> None:
        """Initialize the diff checker.

        Args:
            skip_dirs: Set of directory names to skip during scanning.
                       Uses default SKIP_DIRS if not provided.
        """
        self.skip_dirs = skip_dirs if skip_dirs is not None else SKIP_DIRS

    def _should_skip(self, path: Path) -> bool:
        """Check if a directory should be skipped."""
        return path.name.lower() in {d.lower() for d in self.skip_dirs}

    def create_snapshot(self, root: Path) -> FileSnapshot:
        """Scan a directory and create a snapshot of all files.

        Args:
            root: Root directory to scan.

        Returns:
            FileSnapshot containing all file paths and their sizes.
        """
        snapshot = FileSnapshot(root=str(root.resolve()))

        def _scan(directory: Path) -> None:
            """Recursively scan directory for files."""
            try:
                for item in directory.iterdir():
                    if item.is_dir():
                        if not self._should_skip(item):
                            _scan(item)
                    elif item.is_file():
                        try:
                            rel_path = str(item.relative_to(root)).replace("\\", "/")
                            snapshot.files[rel_path] = item.stat().st_size
                        except (OSError, ValueError):
                            pass
            except (PermissionError, OSError):
                pass

        _scan(root)
        return snapshot

    def compare(self, old_snapshot: FileSnapshot, new_snapshot: FileSnapshot) -> DiffResult:
        """Compare two snapshots to find differences.

        Args:
            old_snapshot: The older/baseline snapshot.
            new_snapshot: The newer snapshot to compare against.

        Returns:
            DiffResult with added, removed, modified, and unchanged files.
        """
        old_files = set(old_snapshot.files.keys())
        new_files = set(new_snapshot.files.keys())

        added = sorted(new_files - old_files)
        removed = sorted(old_files - new_files)

        # Check for modified files (same name, different size)
        common_files = old_files & new_files
        modified = []
        unchanged = []

        for file_path in sorted(common_files):
            if old_snapshot.files[file_path] != new_snapshot.files[file_path]:
                modified.append(file_path)
            else:
                unchanged.append(file_path)

        return DiffResult(
            added=added,
            removed=removed,
            modified=modified,
            unchanged=unchanged,
        )

    def get_diff_summary(self, diff: DiffResult) -> str:
        """Generate a human-readable summary of the diff.

        Args:
            diff: The diff result to summarize.

        Returns:
            A formatted string summarizing the changes.
        """
        lines = []

        if diff["added"]:
            lines.append(f"Added ({len(diff['added'])} files):")
            for f in diff["added"][:10]:  # Show first 10
                lines.append(f"  + {f}")
            if len(diff["added"]) > 10:
                lines.append(f"  ... and {len(diff['added']) - 10} more")

        if diff["removed"]:
            lines.append(f"Removed ({len(diff['removed'])} files):")
            for f in diff["removed"][:10]:
                lines.append(f"  - {f}")
            if len(diff["removed"]) > 10:
                lines.append(f"  ... and {len(diff['removed']) - 10} more")

        if diff["modified"]:
            lines.append(f"Modified ({len(diff['modified'])} files):")
            for f in diff["modified"][:10]:
                lines.append(f"  ~ {f}")
            if len(diff["modified"]) > 10:
                lines.append(f"  ... and {len(diff['modified']) - 10} more")

        if not lines:
            lines.append("No changes detected.")
        else:
            unchanged_count = len(diff["unchanged"])
            lines.append(f"\nUnchanged: {unchanged_count} files")

        return "\n".join(lines)

    def has_changes(self, diff: DiffResult) -> bool:
        """Check if the diff contains any changes.

        Args:
            diff: The diff result to check.

        Returns:
            True if there are added, removed, or modified files.
        """
        return bool(diff["added"] or diff["removed"] or diff["modified"])


# Convenience functions
def create_snapshot(project_root: Path) -> FileSnapshot:
    """Create a snapshot of a project directory.

    Args:
        project_root: Path to the project root directory.

    Returns:
        FileSnapshot of the project.
    """
    checker = FileDiffChecker()
    return checker.create_snapshot(project_root)


def compare_snapshots(old: FileSnapshot, new: FileSnapshot) -> DiffResult:
    """Compare two snapshots to find differences.

    Args:
        old: The baseline snapshot.
        new: The new snapshot to compare.

    Returns:
        DiffResult with the differences.
    """
    checker = FileDiffChecker()
    return checker.compare(old, new)
