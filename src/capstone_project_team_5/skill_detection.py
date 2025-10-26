from __future__ import annotations

from pathlib import Path

from capstone_project_team_5.constants.skill_detection_constants import (
    PRACTICES_FILE_NAMES,
    PRACTICES_FILE_PATTERNS,
    PRACTICES_PATH_PATTERNS,
    SKIP_DIRS,
    TOOL_FILE_NAMES,
    TOOL_FILE_PATTERNS,
)


class SkillDetector:
    @staticmethod
    def _should_skip(path: Path) -> bool:
        """Check if a directory should be skipped during scanning."""
        return path.name.lower() in SKIP_DIRS

    @staticmethod
    def _detect_tools(file_name: str) -> set[str]:
        """
        Detect development tools based on file name.

        Args:
            file_name: Lowercase file name to check

        Returns:
            Set of detected tool names
        """
        tools = set()

        # Check exact file names
        for tool, file_names in TOOL_FILE_NAMES.items():
            if file_name in file_names:
                tools.add(tool)

        # Check file patterns (substring match)
        for tool, patterns in TOOL_FILE_PATTERNS.items():
            for pattern in patterns:
                if pattern in file_name:
                    tools.add(tool)

        return tools

    @staticmethod
    def _detect_practices(file_name: str, rel_path: str) -> set[str]:
        """
        Detect software development practices based on file name and path.

        Args:
            file_name: Lowercase file name to check
            rel_path: Lowercase relative path (with forward slashes)

        Returns:
            Set of detected practice names
        """
        practices = set()

        # Check exact file names
        for practice, file_names in PRACTICES_FILE_NAMES.items():
            if file_name in file_names:
                practices.add(practice)

        # Check file patterns (substring match)
        for practice, patterns in PRACTICES_FILE_PATTERNS.items():
            for pattern in patterns:
                if pattern in file_name:
                    practices.add(practice)

        # Check path patterns
        rel_path_parts = set(rel_path.split("/"))
        for practice, patterns in PRACTICES_PATH_PATTERNS.items():
            for pattern in patterns:
                if "/" in pattern:
                    if rel_path.startswith(pattern):
                        practices.add(practice)
                        break
                else:
                    if pattern in rel_path_parts:
                        practices.add(practice)
                        break

        return practices

    @staticmethod
    def _scan_project_files(root: Path) -> tuple[set[str], set[str]]:
        """
        Scan all files in the project to detect tools and practices.

        Args:
            root: Root directory of the project

        Returns:
            Tuple of (tools, practices) sets
        """
        tools = set()
        practices = set()

        def scan_directory(directory: Path) -> None:
            """Recursively scan directory, skipping excluded dirs."""
            try:
                for item in directory.iterdir():
                    if item.is_dir():
                        if SkillDetector._should_skip(item):
                            continue
                        scan_directory(item)
                    elif item.is_file():
                        file_name = item.name.lower()
                        # Use forward slashes for consistent path matching
                        rel_path = str(item.relative_to(root)).lower().replace("\\", "/")

                        tools.update(SkillDetector._detect_tools(file_name))
                        practices.update(SkillDetector._detect_practices(file_name, rel_path))
            except PermissionError:
                pass

        scan_directory(root)
        return tools, practices


def extract_project_skills(project_root: Path | str) -> dict[str, set[str]]:
    """
    Extracts project skills: tools and practices from the given project root directory.

    Args:
        project_root: Path to the project root directory

    Returns:
        Dictionary with 'tools' and 'practices' keys containing sets of detected items
    """
    root = Path(project_root)
    skills = {
        "tools": set(),
        "practices": set(),
    }

    if not root.exists() or not root.is_dir():
        return skills

    # Scan project files for tools and practices
    tools, practices = SkillDetector._scan_project_files(root)
    skills["tools"].update(tools)
    skills["practices"].update(practices)

    return skills
