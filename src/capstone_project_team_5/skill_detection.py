from __future__ import annotations

from pathlib import Path

from capstone_project_team_5.constants.skill_detection_constants import (
    PRACTICES_FILE_NAMES,
    PRACTICES_FILE_PATTERNS,
    PRACTICES_PATH_PATTERNS,
    SKIP_DIRS,
    TOOL_DIRECTORY_PATTERNS,
    TOOL_FILE_NAMES,
    TOOL_FILE_PATTERNS,
)


class SkillDetector:
    @staticmethod
    def _should_skip(path: Path) -> bool:
        """
        Check if a directory should be skipped during scanning.

        Case-insensitive check since directory names vary (Tests vs tests).
        """
        return path.name.lower() in SKIP_DIRS

    @staticmethod
    def _detect_tools(file_name: str, rel_path: str) -> set[str]:
        """
        Detect development tools based on file name and path.

        Args:
            file_name: Original file name (case-preserved)
            rel_path: Relative path (case-preserved, with forward slashes)

        Returns:
            Set of detected tool names
        """
        tools = set()

        file_name_lower = file_name.lower()
        rel_path_lower = rel_path.lower()

        # Check exact file names (CASE-SENSITIVE)
        for tool, file_names in TOOL_FILE_NAMES.items():
            if file_name in file_names:
                tools.add(tool)

        # Check file patterns (CASE-INSENSITIVE substring match)
        for tool, patterns in TOOL_FILE_PATTERNS.items():
            for pattern in patterns:
                if pattern in file_name_lower:
                    tools.add(tool)

        # Check directory patterns (CASE-INSENSITIVE)
        path_parts_lower = set(rel_path_lower.split("/"))
        for tool, dir_names in TOOL_DIRECTORY_PATTERNS.items():
            for dir_name in dir_names:
                if "/" in dir_name:
                    if rel_path_lower.startswith(dir_name):
                        tools.add(tool)
                        break
                else:
                    if dir_name in path_parts_lower:
                        tools.add(tool)
                        break

        return tools

    @staticmethod
    def _detect_practices(file_name: str, rel_path: str) -> set[str]:
        """
        Detect software development practices based on file name and path.

        Practices are detected case-insensitively to catch variations like
        README, Readme, readme, etc.

        Args:
            file_name: Original file name (case-preserved)
            rel_path: Relative path (case-preserved, with forward slashes)

        Returns:
            Set of detected practice names
        """
        practices = set()

        file_name_lower = file_name.lower()
        rel_path_lower = rel_path.lower()

        # Check exact file names (CASE-INSENSITIVE)
        for practice, file_names in PRACTICES_FILE_NAMES.items():
            if file_name_lower in file_names:
                practices.add(practice)

        # Check file patterns (CASE-INSENSITIVE substring match)
        for practice, patterns in PRACTICES_FILE_PATTERNS.items():
            for pattern in patterns:
                if pattern in file_name_lower:
                    practices.add(practice)

        # Check path patterns (CASE-INSENSITIVE)
        path_parts_lower = set(rel_path_lower.split("/"))
        for practice, patterns in PRACTICES_PATH_PATTERNS.items():
            for pattern in patterns:
                if "/" in pattern:
                    if rel_path_lower.startswith(pattern):
                        practices.add(practice)
                        break
                else:
                    if pattern in path_parts_lower:
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
                    # Skip excluded directories
                    if item.is_dir():
                        if SkillDetector._should_skip(item):
                            continue
                        scan_directory(item)
                    elif item.is_file():
                        # Preserve original case for file name
                        file_name = item.name
                        rel_path = str(item.relative_to(root)).replace("\\", "/")

                        # Detect tools and practices (case handling is internal)
                        tools.update(SkillDetector._detect_tools(file_name, rel_path))
                        practices.update(SkillDetector._detect_practices(file_name, rel_path))
            except PermissionError:
                # TODO: Add logging in later PR
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
