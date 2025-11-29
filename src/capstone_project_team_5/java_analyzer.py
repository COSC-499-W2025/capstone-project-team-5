"""Analyzing Java Code."""

from __future__ import annotations

import os
from pathlib import Path

import tree_sitter_java as tsjava
from tree_sitter import Language, Node, Parser, Tree

from capstone_project_team_5.constants.java_analyzer_constants import (
    JAVA_COLLECTIONS,
    SKIP_DIRS,
)


class JavaAnalyzer:
    """Analyzes Java source code using Tree-sitter for structural patterns."""

    def __init__(self, project_root: Path | str) -> None:
        """Initialize the analyzer with a Java project root directory.

        Args:
            project_root: Path to the Java project root directory
        """
        self.project_root = Path(project_root)
        self.parser: Parser | None = None
        self.result = {
            "data_structures": set(),
            "oop_principles": {
                "Encapsulation": False,
                "Inheritance": False,
                "Polymorphism": False,
                "Abstraction": False,
            },
            "methods_count": 0,
            "classes_count": 0,
            "files_analyzed": 0,
        }

    def _initialize_parser(self) -> bool:
        """Initialize the Tree-sitter parser for Java.

        Returns:
            True if successful, False otherwise
        """
        try:
            java_language = Language(tsjava.language())
            self.parser = Parser(java_language)
            return True
        except (ImportError, AttributeError, OSError):
            # ImportError: tree-sitter modules not available
            # AttributeError: invalid language function call
            return False

    def _find_java_files(self) -> list[Path]:
        """Find all Java files in the project directory.

        Skips build outputs, IDE directories, and other non-source directories.

        Returns:
            List of paths to Java files
        """
        java_files = []
        for root, dirs, files in os.walk(self.project_root):
            # Filter out directories to skip (in-place modification)
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

            for file in files:
                if file.endswith(".java"):
                    java_files.append(Path(root) / file)
        return java_files

    def _parse_code(self, source_code: bytes) -> Tree | None:
        """Parse the source code into an AST.

        Args:
            source_code: Java source code as bytes

        Returns:
            Parsed tree or None if parsing failed
        """
        if self.parser is None:
            return None

        return self.parser.parse(source_code)

    def _get_node_text(self, node: Node, source_code: bytes) -> str:
        """Extract text content from a Tree-sitter node.

        Args:
            node: Tree-sitter node
            source_code: Source code bytes

        Returns:
            Decoded text content
        """
        return source_code[node.start_byte : node.end_byte].decode("utf-8")

    def _single_pass_analysis(self, node: Node, source_code: bytes) -> None:
        """Perform all analyses in a single tree traversal for optimal performance.

        Args:
            node: Current AST node
            source_code: Source code bytes
        """
        node_type = node.type

        # Count structures
        if node_type == "class_declaration":
            self.result["classes_count"] += 1

            # Check inheritance (extends keyword)
            if not self.result["oop_principles"]["Inheritance"]:
                superclass = node.child_by_field_name("superclass")
                if superclass:
                    self.result["oop_principles"]["Inheritance"] = True

            # Check polymorphism (interface implementation)
            if not self.result["oop_principles"]["Polymorphism"]:
                interfaces = node.child_by_field_name("interfaces")
                if interfaces:
                    self.result["oop_principles"]["Polymorphism"] = True

        elif node_type == "method_declaration":
            self.result["methods_count"] += 1

        elif node_type == "type_identifier":
            # Data structures analysis
            text = self._get_node_text(node, source_code)
            if text in JAVA_COLLECTIONS:
                self.result["data_structures"].add(text)

        elif node_type == "array_type":
            # Data structures - arrays
            self.result["data_structures"].add("Array")

        elif node_type == "field_declaration":
            # Encapsulation - check for private fields
            if not self.result["oop_principles"]["Encapsulation"]:
                for child in node.children:
                    if child.type == "modifiers" and any(
                        c.type == "private" for c in child.children
                    ):
                        self.result["oop_principles"]["Encapsulation"] = True
                        break

        elif node_type == "interface_declaration":
            # Abstraction - interface
            if not self.result["oop_principles"]["Abstraction"]:
                self.result["oop_principles"]["Abstraction"] = True

        elif node_type == "marker_annotation":
            # Polymorphism - @Override annotation
            if not self.result["oop_principles"]["Polymorphism"]:
                name_node = node.child_by_field_name("name")
                if name_node and self._get_node_text(name_node, source_code) == "Override":
                    self.result["oop_principles"]["Polymorphism"] = True

        elif node_type == "modifiers":
            # Abstraction - abstract keyword
            if not self.result["oop_principles"]["Abstraction"] and any(
                child.type == "abstract" for child in node.children
            ):
                self.result["oop_principles"]["Abstraction"] = True

        # Recursively analyze children
        for child in node.children:
            self._single_pass_analysis(child, source_code)

    def _analyze_file(self, file_path: Path) -> bool:
        """Analyze a single Java file and aggregate results.

        Args:
            file_path: Path to the Java file

        Returns:
            True if successful, False otherwise
        """
        try:
            source_code = file_path.read_bytes()
        except (OSError, PermissionError):
            return False

        tree = self._parse_code(source_code)
        if tree is None:
            return False

        root = tree.root_node
        self._single_pass_analysis(root, source_code)
        self.result["files_analyzed"] += 1
        return True

    def analyze(self) -> dict[str, bool | int | list[str] | dict[str, bool] | str]:
        """Perform complete analysis of all Java files in the project.

        Returns:
            Dictionary with analysis results or error message.
            On success: {
                "data_structures": list[str],
                "oop_principles": dict with Encapsulation/Inheritance/Polymorphism/Abstraction,
                "methods_count": int,
                "classes_count": int,
                "files_analyzed": int
            }
            On error: {"error": str}
        """
        # Check if project root exists
        if not self.project_root.exists():
            return {"error": f"Project root does not exist: {self.project_root}"}

        if not self.project_root.is_dir():
            return {"error": f"Project root is not a directory: {self.project_root}"}

        # Initialize parser
        if not self._initialize_parser():
            return {"error": "Failed to initialize parser"}

        # Find all Java files
        java_files = self._find_java_files()

        if not java_files:
            return {"error": "No Java files found in project"}

        # Analyze each file
        for file_path in java_files:
            self._analyze_file(file_path)

        # Convert data_structures set to sorted list
        self.result["data_structures"] = sorted(self.result["data_structures"])
        return self.result


def analyze_java_project(
    project_root: Path | str,
) -> dict[str, bool | int | list[str] | dict[str, bool] | str]:
    """Analyze all Java source files in a project directory.

    Analyzes all .java files in the project root and subdirectories,
    skipping build outputs, IDE directories, and generated code.

    Args:
        project_root: Path to the Java project root directory

    Returns:
        Dictionary with analysis results:
        {
            "data_structures": list[str],  # Sorted list of detected data structures
            "oop_principles": {             # OOP principles detected in project
                "Encapsulation": bool,
                "Inheritance": bool,
                "Polymorphism": bool,
                "Abstraction": bool,
            },
            "methods_count": int,          # Total methods across all files
            "classes_count": int,          # Total classes across all files
            "files_analyzed": int,         # Number of .java files analyzed
        }
        Or on error: {"error": str}
    """
    return JavaAnalyzer(project_root).analyze()
