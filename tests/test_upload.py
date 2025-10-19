from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from capstone_project_team_5.upload import DirectoryNode, FileNode, InvalidZipError, upload_zip


def _collect_file_paths(node: DirectoryNode | FileNode) -> set[str]:
    collected: set[str] = set()

    def _walk(current: DirectoryNode | FileNode) -> None:
        if isinstance(current, FileNode):
            collected.add(current.path)
            return
        for child in current.children:
            _walk(child)

    _walk(node)
    return collected


def _create_zip(zip_path: Path, entries: Iterable[tuple[str, bytes]]) -> None:
    with ZipFile(zip_path, mode="w", compression=ZIP_DEFLATED) as archive:
        for relative_path, data in entries:
            archive.writestr(relative_path, data)


def test_upload_valid_zip_returns_tree_excluding_ignored(tmp_path: Path) -> None:
    zip_path = tmp_path / "sample.zip"
    _create_zip(
        zip_path,
        entries=[
            ("src/app.py", b"print('hello')\n"),
            ("src/utils/helpers.py", b"def add(a, b): return a + b\n"),
            ("docs/readme.md", b"# Sample\n"),
            (".git/config", b"[core]\n"),
            ("node_modules/pkg/index.js", b"module.exports = {}"),
            ("__pycache__/module.cpython-311.pyc", b"binary"),
        ],
    )

    result = upload_zip(zip_path)

    assert result.filename == "sample.zip"
    assert result.file_count == 3
    assert any(child.name == "src" for child in result.tree.children)
    collected_paths = _collect_file_paths(result.tree)
    assert collected_paths == {
        "src/app.py",
        "src/utils/helpers.py",
        "docs/readme.md",
    }


def test_upload_wrong_extension_raises(tmp_path: Path) -> None:
    bad_path = tmp_path / "not_a_zip.txt"
    bad_path.write_text("content", encoding="utf-8")

    with pytest.raises(InvalidZipError):
        upload_zip(bad_path)


def test_upload_corrupt_zip_raises(tmp_path: Path) -> None:
    corrupt_path = tmp_path / "broken.zip"
    corrupt_path.write_bytes(b"not a real zip")

    with pytest.raises(InvalidZipError):
        upload_zip(corrupt_path)
