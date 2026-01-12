"""Tests for the file diff checker (standalone, no DB dependencies)."""

from __future__ import annotations

from pathlib import Path

from capstone_project_team_5.file_diff import (
    DiffResult,
    FileDiffChecker,
    FileSnapshot,
)


def test_create_snapshot_with_files_and_subdirs(tmp_path: Path) -> None:
    """Test creating a snapshot with files and nested directories."""
    (tmp_path / "file.txt").write_text("hello")
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "main.py").write_text("# main")

    checker = FileDiffChecker()
    snapshot = checker.create_snapshot(tmp_path)

    assert snapshot.root == str(tmp_path.resolve())
    assert len(snapshot.files) == 2
    assert "file.txt" in snapshot.files
    assert "src/main.py" in snapshot.files
    assert snapshot.files["file.txt"] == 5  # len("hello")


def test_create_snapshot_skips_excluded_directories(tmp_path: Path) -> None:
    """Test that node_modules, .venv, etc. are skipped."""
    (tmp_path / "main.py").write_text("# main")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "pkg.json").write_text("{}")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "cfg").write_text("x")

    checker = FileDiffChecker()
    snapshot = checker.create_snapshot(tmp_path)

    assert len(snapshot.files) == 1
    assert "main.py" in snapshot.files


def test_compare_detects_all_change_types() -> None:
    """Test detecting added, removed, modified, and unchanged files."""
    old = FileSnapshot(
        root="/project",
        files={"keep.txt": 100, "modify.txt": 100, "remove.txt": 100},
    )
    new = FileSnapshot(
        root="/project",
        files={"keep.txt": 100, "modify.txt": 999, "add.txt": 200},
    )

    checker = FileDiffChecker()
    diff = checker.compare(old, new)

    assert diff["added"] == ["add.txt"]
    assert diff["removed"] == ["remove.txt"]
    assert diff["modified"] == ["modify.txt"]
    assert diff["unchanged"] == ["keep.txt"]


def test_compare_no_changes() -> None:
    """Test comparing identical snapshots returns no changes."""
    snapshot = FileSnapshot(root="/project", files={"a.txt": 100, "b.txt": 200})

    checker = FileDiffChecker()
    diff = checker.compare(snapshot, snapshot)

    assert diff["added"] == []
    assert diff["removed"] == []
    assert diff["modified"] == []
    assert len(diff["unchanged"]) == 2


def test_snapshot_save_and_load(tmp_path: Path) -> None:
    """Test saving and loading snapshots to/from JSON."""
    snapshot_file = tmp_path / "snapshot.json"
    original = FileSnapshot(
        root="/my/project",
        files={"main.py": 100, "utils.py": 200},
    )

    original.save(snapshot_file)
    loaded = FileSnapshot.load(snapshot_file)

    assert loaded.root == original.root
    assert loaded.files == original.files
    assert loaded.created_at == original.created_at


def test_snapshot_to_dict_and_from_dict() -> None:
    """Test dict serialization roundtrip."""
    original = FileSnapshot(root="/project", files={"main.py": 100})

    data = original.to_dict()
    restored = FileSnapshot.from_dict(data)

    assert restored.root == original.root
    assert restored.files == original.files


def test_get_diff_summary() -> None:
    """Test human-readable summary generation."""
    checker = FileDiffChecker()

    # With changes
    diff: DiffResult = {
        "added": ["new.txt"],
        "removed": ["old.txt"],
        "modified": ["changed.txt"],
        "unchanged": ["keep.txt"],
    }
    summary = checker.get_diff_summary(diff)
    assert "+ new.txt" in summary
    assert "- old.txt" in summary
    assert "~ changed.txt" in summary

    # No changes
    no_change_diff: DiffResult = {
        "added": [],
        "removed": [],
        "modified": [],
        "unchanged": ["file.txt"],
    }
    assert "No changes detected." in checker.get_diff_summary(no_change_diff)


def test_has_changes() -> None:
    """Test has_changes helper."""
    checker = FileDiffChecker()

    assert checker.has_changes({"added": ["f"], "removed": [], "modified": [], "unchanged": []})
    assert checker.has_changes({"added": [], "removed": ["f"], "modified": [], "unchanged": []})
    assert checker.has_changes({"added": [], "removed": [], "modified": ["f"], "unchanged": []})
    assert not checker.has_changes({"added": [], "removed": [], "modified": [], "unchanged": ["f"]})


def test_custom_skip_dirs(tmp_path: Path) -> None:
    """Test using custom skip directories."""
    (tmp_path / "main.py").write_text("# main")
    (tmp_path / "my_cache").mkdir()
    (tmp_path / "my_cache" / "file.py").write_text("# cached")

    # Default: my_cache is NOT skipped
    default_snapshot = FileDiffChecker().create_snapshot(tmp_path)
    assert "my_cache/file.py" in default_snapshot.files

    # Custom: my_cache IS skipped
    custom_snapshot = FileDiffChecker(skip_dirs={"my_cache"}).create_snapshot(tmp_path)
    assert "my_cache/file.py" not in custom_snapshot.files


def test_empty_directory(tmp_path: Path) -> None:
    """Test snapshot of empty directory."""
    snapshot = FileDiffChecker().create_snapshot(tmp_path)
    assert snapshot.files == {}
