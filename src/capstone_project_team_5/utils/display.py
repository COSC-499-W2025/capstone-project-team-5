"""Display and formatting utilities"""

from __future__ import annotations

from pathlib import Path

import easygui as eg

from capstone_project_team_5.models.upload import DirectoryNode, FileNode, ZipUploadResult


def prompt_for_zip_file() -> Path | None:
    """Display file picker dialog for zip file selection.

    Returns:
        Path to selected zip file, or None if cancelled.
    """
    zip_path_str = eg.fileopenbox(
        msg="Select a .zip file containing your project",
        title="Select Project Archive",
        default="*.zip",
        filetypes=["*.zip"],
    )
    return Path(zip_path_str) if zip_path_str else None


def print_tree(node: DirectoryNode | FileNode, indent: int = 0) -> None:
    """Recursively print the directory tree structure.

    Args:
        node: Tree node to print (directory or file).
        indent: Current indentation level.
    """
    prefix = "  " * indent
    if isinstance(node, FileNode):
        print(f"{prefix}📄 {node.name}")
        return

    if node.name:
        print(f"{prefix}📁 {node.name}/")

    for child in node.children:
        print_tree(child, indent + 1 if node.name else indent)


def display_upload_result(result: ZipUploadResult) -> None:
    """Display the upload result with formatted output.

    Args:
        result: Upload result containing file metadata and tree structure.
    """
    print("\n✅ Successfully processed zip archive:")
    print(f"   • Filename: {result.filename}")
    print(f"   • Size: {result.size_bytes:,} bytes")
    print(f"   • Files found: {result.file_count}")
    print(f"   • Projects discovered: {len(result.projects)}")

    if result.projects:
        print("\n📁 Discovered Projects:")
        print("-" * 60)
        print(f"{'Name':<24} {'Path':<24} {'Git':<5} {'Files':<5}")
        print("-" * 60)
        for project in result.projects:
            git_flag = "✓" if project.has_git_repo else "-"
            rel_path = project.rel_path or "(root)"
            print(f"{project.name:<24} {rel_path:<24} {git_flag:<5} {project.file_count:<5}")

    print("\n📂 Directory Structure:")
    print("-" * 60)
    print_tree(result.tree)
    print("\n" + "=" * 60)
    print("✨ Processing complete!")
    print("=" * 60)
