"""Analyzing Java Code."""

from __future__ import annotations

from pathlib import Path

import tree_sitter_java as tsjava
from tree_sitter import Language, Node, Parser, Tree

from capstone_project_team_5.constants.java_analyzer_constants import (
    JAVA_COLLECTIONS,
)


class JavaAnalyzer:
    """Analyzes Java source code using Tree-sitter for structural patterns."""

    def __init__(self, file_path: Path | str) -> None:
        """Initialize the analyzer with a Java file path.

        Args:
            file_path: Path to the Java source file
        """
        self.file_path = Path(file_path)
        self.source_code: bytes | None = None
        self.parser: Parser | None = None
        self.tree: Tree | None = None
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

    def _read_file(self) -> bool:
        """Read the Java source file.

        Returns:
            True if successful, False otherwise
        """
        if not self.file_path.exists():
            return False

        try:
            self.source_code = self.file_path.read_bytes()
            return True
        except (OSError, PermissionError):
            # OSError: general I/O errors
            # PermissionError: insufficient file permissions
            return False

    def _parse_code(self) -> bool:
        """Parse the source code into an AST.

        Returns:
            True if successful, False otherwise
        """
        if self.parser is None or self.source_code is None:
            return False

        self.tree = self.parser.parse(self.source_code)
        return True

    def _get_node_text(self, node: Node) -> str:
        """Extract text content from a Tree-sitter node.

        Args:
            node: Tree-sitter node

        Returns:
            Decoded text content
        """
        if self.source_code is None:
            return ""
        return self.source_code[node.start_byte : node.end_byte].decode("utf-8")

    def _single_pass_analysis(self, node: Node) -> None:
        """Perform all analyses in a single tree traversal for optimal performance.

        Args:
            node: Current AST node
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
            text = self._get_node_text(node)
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
                if name_node and self._get_node_text(name_node) == "Override":
                    self.result["oop_principles"]["Polymorphism"] = True

        elif node_type == "modifiers":
            # Abstraction - abstract keyword
            if not self.result["oop_principles"]["Abstraction"] and any(
                child.type == "abstract" for child in node.children
            ):
                self.result["oop_principles"]["Abstraction"] = True

        # Recursively analyze children
        for child in node.children:
            self._single_pass_analysis(child)

    def analyze(self) -> dict[str, bool | int | list[str] | dict[str, bool] | str]:
        """Perform complete analysis of the Java file.

        Returns:
            Dictionary with analysis results or error message.
            On success: {
                "data_structures": list[str],
                "oop_principles": dict with Encapsulation/Inheritance/Polymorphism/Abstraction,
                "methods_count": int,
                "classes_count": int
            }
            On error: {"error": str}
        """
        # Initialize parser
        if not self._initialize_parser():
            return {"error": "Failed to initialize parser"}

        # Read file
        if not self._read_file():
            return {"error": f"Failed to read file: {self.file_path}"}

        # Parse code
        if not self._parse_code():
            return {"error": "Failed to parse code"}

        if self.tree is None:
            return {"error": "No parse tree available"}

        root = self.tree.root_node

        # Single-pass analysis - combines all checks in one traversal
        self._single_pass_analysis(root)

        # Convert data_structures set to sorted list
        self.result["data_structures"] = sorted(self.result["data_structures"])
        return self.result


def analyze_java_file(
    file_path: Path | str,
) -> dict[str, bool | int | list[str] | dict[str, bool] | str]:
    """Analyze a Java source file for complexity, data structures, and OOP principles.

    Args:
        file_path: Path to the Java source file

    Returns:
        Dictionary with analysis results (see JavaAnalyzer.analyze for structure)
    """
    return JavaAnalyzer(file_path).analyze()
