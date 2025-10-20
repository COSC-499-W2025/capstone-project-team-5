from __future__ import annotations

from pathlib import Path

from capstone_project_team_5.constants.skill_detection_constants import (
    PRACTICES_FILE_NAMES,
    PRACTICES_FILE_PATTERNS,
    PRACTICES_PATH_PATTERNS,
    TOOL_FILE_NAMES,
    TOOL_FILE_PATTERNS,
)


class SkillDetector:
    @staticmethod
    def _read_text(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""

    @staticmethod
    def _detect_tools(name: str, root: Path) -> set[str]:
        """
        Detect development tools based on file name and content.

        TODO: Unused parameters will be utilized when function logic is extended
        """
        tools = set()

        # Check exact file names
        for tool, file_names in TOOL_FILE_NAMES.items():
            if name in file_names:
                tools.add(tool)

        # Check file patterns
        for tool, patterns in TOOL_FILE_PATTERNS.items():
            for pattern in patterns:
                if pattern in name or name.endswith(pattern):
                    tools.add(tool)

        return tools

    @staticmethod
    def _detect_practices(file_path: Path, name: str, rel: str) -> set[str]:
        """
        Detect software development practices based on file structure and content.

        TODO: Unused parameters will be utilized when function logic is extended
        """
        practices = set()

        # Check exact file names
        for practice, file_names in PRACTICES_FILE_NAMES.items():
            if name in file_names:
                practices.add(practice)

        # Check file patterns
        for practice, patterns in PRACTICES_FILE_PATTERNS.items():
            for pattern in patterns:
                if pattern in name or name.startswith(pattern):
                    practices.add(practice)

        # Check path patterns
        for practice, patterns in PRACTICES_PATH_PATTERNS.items():
            for pattern in patterns:
                if pattern in rel or rel.startswith(pattern):
                    practices.add(practice)

        return practices

    @staticmethod
    def _scan_project_files(root: Path) -> tuple[set[str], set[str]]:
        """
        Scan all files in the project to detect tools and practices.
        """
        tools = set()
        practices = set()

        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue

            name = file_path.name.lower()
            rel = str(file_path.relative_to(root)).lower()

            tools.update(SkillDetector._detect_tools(file_path, name, root))
            practices.update(SkillDetector._detect_practices(file_path, name, rel))

        return tools, practices


def extract_project_skills(project_root: Path | str) -> dict[str, set[str]]:
    """
    Extracts project skills: tools and practices from the given project root directory.
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
