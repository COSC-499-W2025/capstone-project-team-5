"""Tests for directory walking functionality."""

from __future__ import annotations

from pathlib import Path

import pytest

from capstone_project_team_5.file_walker import DirectoryWalker


class TestDirectoryWalker:
    """Test cases for DirectoryWalker."""

    def test_walk_simple_directory(self, tmp_path: Path) -> None:
        """Test walking a simple directory structure."""
        # Create test files
        (tmp_path / "main.py").write_text("print('hello')")
        (tmp_path / "README.md").write_text("# Project")
        (tmp_path / "logo.png").write_bytes(b"fake png")

        result = DirectoryWalker.walk(tmp_path)

        assert len(result.files) == 3
        assert result.total_size_bytes > 0

    def test_walk_nested_directory(self, tmp_path: Path) -> None:
        """Test walking a nested directory structure."""
        # Create nested structure
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "app.py").write_text("code")
        (src_dir / "utils.py").write_text("code")

        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "guide.md").write_text("docs")

        result = DirectoryWalker.walk(tmp_path)

        assert len(result.files) == 3

    def test_walk_respects_ignore_patterns(self, tmp_path: Path) -> None:
        """Test that ignore patterns are respected."""
        # Create files in ignored directories
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("git config")

        node_modules = tmp_path / "node_modules"
        node_modules.mkdir()
        (node_modules / "package.js").write_text("code")

        pycache = tmp_path / "__pycache__"
        pycache.mkdir()
        (pycache / "module.pyc").write_bytes(b"bytecode")

        # Create valid files
        (tmp_path / "main.py").write_text("code")

        result = DirectoryWalker.walk(tmp_path)

        # Only main.py should be included
        assert len(result.files) == 1
        assert result.files[0].name == "main.py"

    def test_walk_with_custom_ignore_patterns(self, tmp_path: Path) -> None:
        """Test walking with custom ignore patterns."""
        # Create directories
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        (build_dir / "output.js").write_text("code")

        (tmp_path / "source.py").write_text("code")

        # Walk with custom ignore pattern
        result = DirectoryWalker.walk(tmp_path, ignore_patterns={"build"})

        # Only source.py should be included
        assert len(result.files) == 1
        assert result.files[0].name == "source.py"

    def test_get_summary(self, tmp_path: Path) -> None:
        """Test getting summary statistics."""
        (tmp_path / "main.py").write_text("x" * 100)
        (tmp_path / "app.js").write_text("x" * 200)
        (tmp_path / "README.md").write_text("x" * 50)
        (tmp_path / "logo.png").write_bytes(b"x" * 150)

        result = DirectoryWalker.walk(tmp_path)
        summary = DirectoryWalker.get_summary(result)

        assert summary["total_files"] == 4
        assert summary["total_size_bytes"] == 500

    def test_walk_empty_directory(self, tmp_path: Path) -> None:
        """Test walking an empty directory."""
        result = DirectoryWalker.walk(tmp_path)

        assert len(result.files) == 0
        assert result.total_size_bytes == 0

    def test_walk_invalid_directory(self) -> None:
        """Test walking a non-existent directory raises error."""
        with pytest.raises(ValueError, match="Invalid directory"):
            DirectoryWalker.walk("/nonexistent/path")

    def test_walk_file_instead_of_directory(self, tmp_path: Path) -> None:
        """Test walking a file instead of directory raises error."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")

        with pytest.raises(ValueError, match="Invalid directory"):
            DirectoryWalker.walk(file_path)

    def test_file_info_attributes(self, tmp_path: Path) -> None:
        """Test that FileInfo has correct attributes."""
        (tmp_path / "test.py").write_text("code")

        result = DirectoryWalker.walk(tmp_path)

        assert len(result.files) == 1
        file = result.files[0]

        assert file.name == "test.py"
        assert file.path == "test.py"
        assert file.size_bytes == 4
        assert file.absolute_path == tmp_path / "test.py"

    def test_walk_deeply_nested_structure(self, tmp_path: Path) -> None:
        """Test walking a deeply nested directory structure."""
        deep_path = tmp_path / "a" / "b" / "c" / "d"
        deep_path.mkdir(parents=True)
        (deep_path / "deep.py").write_text("code")

        result = DirectoryWalker.walk(tmp_path)

        assert len(result.files) == 1
        # Check path separator (works on both Windows and Unix)
        assert "deep.py" in result.files[0].path

    def test_total_size_calculation(self, tmp_path: Path) -> None:
        """Test that total size is correctly calculated."""
        (tmp_path / "file1.py").write_text("x" * 100)
        (tmp_path / "file2.py").write_text("x" * 200)
        (tmp_path / "file3.md").write_text("x" * 300)

        result = DirectoryWalker.walk(tmp_path)

        assert result.total_size_bytes == 600
        assert sum(f.size_bytes for f in result.files) == 600

    def test_ignore_patterns_stored(self, tmp_path: Path) -> None:
        """Test that ignore patterns are stored in result."""
        custom_patterns = {"build", "dist"}
        result = DirectoryWalker.walk(tmp_path, ignore_patterns=custom_patterns)

        assert result.ignore_patterns == custom_patterns

    def test_walk_with_various_file_types(self, tmp_path: Path) -> None:
        """Test walking with various file types."""
        files = ["main.py", "app.js", "style.css", "README.md", "LICENSE", "logo.png", "data.bin"]

        for filename in files:
            (tmp_path / filename).write_text("content")

        result = DirectoryWalker.walk(tmp_path)

        assert len(result.files) == len(files)

        collected_names = {f.name for f in result.files}
        assert collected_names == set(files)
