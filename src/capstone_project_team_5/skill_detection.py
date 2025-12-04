from __future__ import annotations

from pathlib import Path

from capstone_project_team_5.consent_tool import ConsentTool
from capstone_project_team_5.constants.skill_detection_constants import (
    PRACTICES_FILE_NAMES,
    PRACTICES_FILE_PATTERNS,
    PRACTICES_PATH_PATTERNS,
    SKIP_DIRS,
    TOOL_DIRECTORY_PATTERNS,
    TOOL_FILE_NAME_PATTERNS,
    TOOL_FILE_NAMES,
    TOOL_FILE_PATH_PATTERNS,
)
from capstone_project_team_5.services.llm_providers import LLMError
from capstone_project_team_5.services.llm_service import LLMService


class SkillDetector:
    @staticmethod
    def _should_skip(path: Path) -> bool:
        """
        Check if a directory should be skipped during scanning.

        Args:
            path: Path to check
        """
        return path.name.lower() in SKIP_DIRS

    @staticmethod
    def _detect_tools_locally(file_name: str, rel_path: str) -> set[str]:
        """
        Detect development tools based on file name and path.

        Args:
            file_name: Original file name
            rel_path: Relative path

        Returns:
            Set of detected tool names
        """
        tools = set()

        file_name_lower = file_name.lower()
        rel_path_lower = rel_path.lower()

        # Check exact file names
        for tool, file_names in TOOL_FILE_NAMES.items():
            if file_name in file_names:
                tools.add(tool)

        # Check file name patterns
        for tool, patterns in TOOL_FILE_NAME_PATTERNS.items():
            for pattern in patterns:
                if pattern in file_name_lower:
                    tools.add(tool)

        # Check file path patterns
        for tool, patterns in TOOL_FILE_PATH_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in rel_path_lower:
                    tools.add(tool)

        # Check directory patterns
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
    def _detect_practices_locally(file_name: str, rel_path: str) -> set[str]:
        """
        Detect software development practices based on file name and path.

        Args:
            file_name: Original file name
            rel_path: Relative path

        Returns:
            Set of detected practice names
        """
        practices = set()

        file_name_lower = file_name.lower()
        rel_path_lower = rel_path.lower()

        # Check exact file names
        for practice, file_names in PRACTICES_FILE_NAMES.items():
            if file_name_lower in file_names:
                practices.add(practice)

        # Check file patterns
        for practice, patterns in PRACTICES_FILE_PATTERNS.items():
            for pattern in patterns:
                if pattern in file_name_lower:
                    practices.add(practice)

        # Check path patterns
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
    def _detect_tools_practices_locally(root: Path) -> tuple[set[str], set[str]]:
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
                        file_name = item.name
                        rel_path = str(item.relative_to(root)).replace("\\", "/")

                        # Detect tools and practices
                        tools.update(SkillDetector._detect_tools_locally(file_name, rel_path))
                        practices.update(
                            SkillDetector._detect_practices_locally(file_name, rel_path)
                        )
            except (PermissionError, OSError, FileNotFoundError):
                # Skip directories we can't access due to permissions or I/O errors
                pass

        scan_directory(root)
        return tools, practices

    @staticmethod
    def _generate_directory_tree(
        root: Path, prefix: str = "", max_depth: int = 5, current_depth: int = 0
    ) -> str:
        """
        Generate a directory tree structure string for the project.

        Args:
            root: Root directory of the project
            prefix: Prefix for indentation
            max_depth: Maximum depth to traverse
            current_depth: Current depth in the tree

        Returns:
            String representation of the directory tree
        """
        if current_depth >= max_depth:
            return ""

        tree_lines = []

        try:
            # Get all items in the directory
            items = sorted(root.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))

            for item in items:
                # Skip excluded directories
                if item.is_dir() and SkillDetector._should_skip(item):
                    continue

                # Add item to tree
                if item.is_dir():
                    tree_lines.append(f"{prefix}{item.name}/")
                    # Recursively add subdirectory contents
                    subtree = SkillDetector._generate_directory_tree(
                        item, prefix + "  ", max_depth, current_depth + 1
                    )
                    if subtree:
                        tree_lines.append(subtree)
                else:
                    tree_lines.append(f"{prefix}{item.name}")

        except (PermissionError, OSError, FileNotFoundError):
            # Skip directories we can't access due to permissions or I/O errors
            pass

        return "\n".join(tree_lines)

    @staticmethod
    def _generate_llm_call_config(directory_tree: str) -> tuple[str, str, float, int]:
        """
        Create system instructions and user content for LLM call.

        Args:
            directory_tree: String representation of the directory tree
        Returns:
            Tuple of (system_instructions, user_content, temperature, max_tokens)
        """
        temperature = 0.3
        max_tokens = 3000

        # Create example lists from constants
        tool_examples = [
            "Docker",
            "Webpack",
            "Jest",
            "Terraform",
            "Prisma",
            "GitHub Actions",
            "PyTest",
            "Gradle",
            "Maven",
            "Jenkins",
            "Cypress",
        ]
        practice_examples = [
            "Test-Driven Development (TDD)",
            "CI/CD",
            "Documentation Discipline",
            "Infrastructure as Code",
            "Code Quality Enforcement",
            "Environment Management",
            "API Design",
            "Automated Testing",
        ]

        # Build system instructions
        system_instructions = (
            "You are an expert software development analyst. "
            "Your task is to identify development TOOLS and software development PRACTICES "
            "used in a project based on its directory structure.\n\n"
            "IMPORTANT CONSTRAINTS:\n"
            "- Do NOT identify programming languages "
            "(e.g., Python, JavaScript, TypeScript, Java, Go)\n"
            "- Do NOT identify frameworks "
            "(e.g., React, Django, Flask, Spring, Angular, Vue)\n"
            "- ONLY identify development tools and practices\n\n"
            "TOOLS are development utilities, build tools, testing frameworks, "
            "CI/CD systems, package managers, containerization tools, etc.\n"
            f"Examples: {', '.join(tool_examples)}\n\n"
            "PRACTICES are software development methodologies, patterns, and disciplines.\n"
            f"Examples: {', '.join(practice_examples)}\n\n"
            "Analyze the directory structure and return ONLY a JSON response "
            "with this exact structure:\n"
            '{"tools": ["tool1", "tool2"], "practices": ["practice1", "practice2"]}\n\n'
            "Return an empty array if you don't find any tools or practices. "
            "Be conservative and only include items you are confident about."
        )

        # Build user content with directory tree
        user_content = (
            "Here is the project directory structure:\n\n"
            f"{directory_tree}\n\n"
            "Based on this directory structure, identify the development tools "
            "and software practices used in this project. "
            "Return your response as JSON only."
        )
        return system_instructions, user_content, temperature, max_tokens

    @staticmethod
    def _detect_tools_practices_llm(
        root: Path,
        existing_tools: set[str],
        existing_practices: set[str],
        consent_tool: ConsentTool | None = None,
    ) -> tuple[set[str], set[str]]:
        """
        Use LLM to identify additional tools and practices from the directory structure.

        Args:
            root: Root directory of the project
            existing_tools: Tools already detected by pattern matching
            existing_practices: Practices already detected by pattern matching
            consent_tool: Optional ConsentTool for getting model preferences.

        Returns:
            Tuple of (tools, practices) sets identified by LLM
        """
        try:
            tree = SkillDetector._generate_directory_tree(root)

            # Skip LLM call if directory tree is empty
            if not tree or not tree.strip():
                return set(), set()

            # Create LLM call content
            system_instructions, user_content, temperature, max_tokens = (
                SkillDetector._generate_llm_call_config(tree)
            )

            # Create LLM service with user's model preferences if available
            model_preferences = consent_tool.get_llm_model_preferences() if consent_tool else []
            llm_service = LLMService.from_model_preferences(model_preferences)
            response = llm_service.generate_llm_response(
                system_instructions=system_instructions,
                user_content=user_content,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Extract and parse JSON from response
            result = LLMService.extract_json_from_response(response)

            llm_tools = set(result.get("tools", []))
            llm_practices = set(result.get("practices", []))

            # Filter out items that are already detected (case-insensitive comparison)
            existing_tools_lower = {t.lower() for t in existing_tools}
            existing_practices_lower = {p.lower() for p in existing_practices}

            tools = {t for t in llm_tools if t.lower() not in existing_tools_lower}
            practices = {p for p in llm_practices if p.lower() not in existing_practices_lower}

            return tools, practices

        except LLMError:
            # In case of LLM failure, return empty sets
            return set(), set()

    @staticmethod
    def detect_skills(root: Path, consent_tool: ConsentTool | None = None) -> dict[str, set[str]]:
        """
        Detect development tools and practices in the project.

        Args:
            root: Root directory of the project
            consent_tool: Optional ConsentTool instance for checking LLM permissions.

        Returns:
            Dictionary with 'tools' and 'practices' keys containing sets of detected items
        """
        skills: dict[str, set[str]] = {
            "tools": set(),
            "practices": set(),
        }

        if not root.exists() or not root.is_dir():
            return skills

        # Detect tools and practices locally
        local_tools, local_practices = SkillDetector._detect_tools_practices_locally(root)
        skills["tools"].update(local_tools)
        skills["practices"].update(local_practices)

        if consent_tool is not None and consent_tool.is_llm_allowed():
            # use LLM to identify any additional tools/practices
            llm_tools, llm_practices = SkillDetector._detect_tools_practices_llm(
                root, skills["tools"], skills["practices"], consent_tool
            )
            skills["tools"].update(llm_tools)
            skills["practices"].update(llm_practices)

        return skills


def extract_project_tools_practices(
    project_root: Path, consent_tool: ConsentTool | None = None
) -> dict[str, set[str]]:
    """
    Extracts project skills: tools and practices from the given project root directory.

    Args:
        project_root: Path to the project root directory
        consent_tool: Optional ConsentTool instance for checking LLM permissions.

    Returns:
        Dictionary with skills: 'tools' and 'practices' keys containing sets of detected items
    """
    return SkillDetector.detect_skills(Path(project_root), consent_tool)
