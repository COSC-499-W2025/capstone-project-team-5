"""Demo script to showcase the file walker functionality.

This script creates a sample project structure and demonstrates
how the file walker analyzes it.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from zipfile import ZipFile

from capstone_project_team_5.file_walker import DirectoryWalker


def create_sample_project(root: Path) -> None:
    """Create a sample project structure for demonstration."""
    # Source code
    src = root / "src"
    src.mkdir()
    (src / "main.py").write_text("print('Hello World')\n" * 10)
    (src / "utils.py").write_text("def helper():\n    pass\n" * 5)
    (src / "config.json").write_text('{"key": "value"}\n' * 3)

    # Tests
    tests = root / "tests"
    tests.mkdir()
    (tests / "test_main.py").write_text("def test_example():\n    assert True\n" * 8)

    # Documentation
    (root / "README.md").write_text("# Sample Project\n\n" + "Description text. " * 20)
    (root / "LICENSE").write_text("MIT License\n" + "License text. " * 10)

    docs = root / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text("# User Guide\n\n" + "Guide content. " * 30)

    # Assets
    assets = root / "assets"
    assets.mkdir()
    (assets / "logo.png").write_bytes(b"FAKE_PNG_DATA" * 50)
    (assets / "banner.jpg").write_bytes(b"FAKE_JPG_DATA" * 100)

    # Build artifacts (should be ignored)
    node_modules = root / "node_modules"
    node_modules.mkdir()
    (node_modules / "package.json").write_text('{"name": "ignored"}')

    pycache = root / "__pycache__"
    pycache.mkdir()
    (pycache / "main.cpython-313.pyc").write_bytes(b"BYTECODE" * 20)


def format_size(size_bytes: int) -> str:
    """Format bytes to human-readable size."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def demo_basic_walk() -> None:
    """Demo 1: Basic directory walking."""
    print("=" * 70)
    print("DEMO 1: Basic Directory Walking")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        create_sample_project(root)

        print(f"\n📂 Walking directory: {root}")
        print("\nProject structure created with:")
        print("  - Source code (src/)")
        print("  - Tests (tests/)")
        print("  - Documentation (README.md, docs/)")
        print("  - Assets (assets/)")
        print("  - Build artifacts (node_modules/, __pycache__/) [ignored]")

        result = DirectoryWalker.walk(root)

        print("\n📊 Walk Results:")
        print(f"  Total files found: {len(result.files)}")
        print(f"  Total size: {format_size(result.total_size_bytes)}")
        print(f"  Ignored patterns: {', '.join(sorted(result.ignore_patterns))}")

        print("\n📝 Files discovered:")
        for file in sorted(result.files, key=lambda f: f.path):
            print(f"  {file.path:30s} ({format_size(file.size_bytes):>10s})")


def demo_custom_ignore() -> None:
    """Demo 2: Custom ignore patterns."""
    print("\n\n" + "=" * 70)
    print("DEMO 2: Custom Ignore Patterns")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create structure with build directories
        (root / "src").mkdir()
        (root / "src" / "main.py").write_text("code")

        (root / "build").mkdir()
        (root / "build" / "output.js").write_text("compiled")

        (root / "dist").mkdir()
        (root / "dist" / "bundle.js").write_text("bundled")

        print("\nProject has: src/, build/, dist/")

        # Walk with default patterns
        result_default = DirectoryWalker.walk(root)
        print("\n📊 With default ignore patterns:")
        print(f"  Files found: {len(result_default.files)}")
        print(f"  Files: {[f.name for f in result_default.files]}")

        # Walk with custom patterns
        result_custom = DirectoryWalker.walk(root, ignore_patterns={"build", "dist"})
        print("\n📊 With custom ignore patterns (build, dist):")
        print(f"  Files found: {len(result_custom.files)}")
        print(f"  Files: {[f.name for f in result_custom.files]}")


def demo_summary() -> None:
    """Demo 3: Summary statistics."""
    print("\n\n" + "=" * 70)
    print("DEMO 3: Summary Statistics")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        create_sample_project(root)

        result = DirectoryWalker.walk(root)
        summary = DirectoryWalker.get_summary(result)

        print("\n📊 Project Summary:")
        print(f"  Total files: {summary['total_files']}")
        print(f"  Total size: {format_size(summary['total_size_bytes'])}")

        print("\n📁 File breakdown:")
        file_types = {}
        for file in result.files:
            ext = Path(file.name).suffix or "no extension"
            file_types[ext] = file_types.get(ext, 0) + 1

        for ext, count in sorted(file_types.items(), key=lambda x: -x[1]):
            print(f"  {ext:15s}: {count} files")


def demo_with_zip() -> None:
    """Demo 4: Real workflow with zip extraction."""
    print("\n\n" + "=" * 70)
    print("DEMO 4: Real Workflow (Zip → Extract → Walk)")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Create a sample project
        project_dir = tmp_path / "sample_project"
        project_dir.mkdir()
        create_sample_project(project_dir)

        # Zip it up
        zip_path = tmp_path / "project.zip"
        with ZipFile(zip_path, "w") as zf:
            for file in project_dir.rglob("*"):
                if file.is_file():
                    zf.write(file, file.relative_to(project_dir))

        print(f"\n📦 Created zip file: {zip_path.name}")
        print(f"   Size: {format_size(zip_path.stat().st_size)}")

        # Extract
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()
        with ZipFile(zip_path) as zf:
            zf.extractall(extract_dir)

        print(f"\n📂 Extracted to: {extract_dir}")

        # Walk
        result = DirectoryWalker.walk(extract_dir)
        summary = DirectoryWalker.get_summary(result)

        print("\n📊 Analysis Results:")
        print(f"  Files analyzed: {summary['total_files']}")
        print(f"  Total size: {format_size(summary['total_size_bytes'])}")
        total_files_in_project = len([f for f in project_dir.rglob("*") if f.is_file()])
        ignored_count = total_files_in_project - summary["total_files"]
        print(f"  Ignored files: {ignored_count}")

        print("\n✅ This is what happens in the CLI when you upload a zip!")


def main() -> None:
    """Run all demos."""
    print("\n🎬 File Walker Demonstration")
    print("This shows how the file walker analyzes project directories\n")

    demo_basic_walk()
    demo_custom_ignore()
    demo_summary()
    demo_with_zip()

    print("\n\n" + "=" * 70)
    print("✨ Demo Complete!")
    print("=" * 70)
    print("\nThe file walker:")
    print("  ✅ Walks directories recursively")
    print("  ✅ Respects ignore patterns (.git, node_modules, __pycache__)")
    print("  ✅ Collects file metadata (path, name, size)")
    print("  ✅ Provides summary statistics")
    print("  ✅ Integrates with the zip upload workflow")
    print("\n")


if __name__ == "__main__":
    main()
