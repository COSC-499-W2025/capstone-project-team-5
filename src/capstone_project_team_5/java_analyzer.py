"""Analyzing Java Code."""

from __future__ import annotations

import os
from pathlib import Path

import tree_sitter_java as tsjava
from tree_sitter import Language, Node, Parser, Tree

from capstone_project_team_5.constants.java_analyzer_constants import (
    CODING_PATTERNS,
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
            "uses_recursion": False,
            "uses_bfs": False,
            "uses_dfs": False,
            "coding_patterns": set(),
            "imports": [],
        }
        self.current_method_stack: list[str] = []  # Track method names for recursion
        self.current_method_bodies: list[
            tuple[Node, bytes]
        ] = []  # Store method bodies for analysis

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

            # Get method name and body for analysis
            name_node = node.child_by_field_name("name")
            if name_node:
                method_name = self._get_node_text(name_node, source_code)
                self.current_method_stack.append(method_name)

                # Store method body for later analysis
                body_node = node.child_by_field_name("body")
                if body_node:
                    self.current_method_bodies.append((body_node, source_code))

                # Detect coding patterns from method name
                self._detect_coding_patterns_by_name(method_name)

                # Analyze children then pop method name
                for child in node.children:
                    self._single_pass_analysis(child, source_code)

                self.current_method_stack.pop()
                return  # Don't recurse again

        elif node_type == "method_invocation":
            # Check for recursion
            name_node = node.child_by_field_name("name")
            if name_node:
                invoked_method = self._get_node_text(name_node, source_code)
                # Check if calling current method (recursion)
                if invoked_method in self.current_method_stack:
                    # Check if it's a recursive call (not on another object)
                    object_node = node.child_by_field_name("object")
                    if object_node:
                        object_text = self._get_node_text(object_node, source_code)
                        # Only 'this' qualifier indicates recursion on same instance
                        if object_text == "this":
                            self.result["uses_recursion"] = True
                    else:
                        # No object qualifier means direct call - this is recursion
                        self.result["uses_recursion"] = True

        elif node_type == "import_declaration":
            # Track imports
            for child in node.children:
                if child.type in ("scoped_identifier", "identifier"):
                    import_text = self._get_node_text(child, source_code)
                    # Extract base package
                    base_package = import_text.split(".")[0] if "." in import_text else import_text
                    self.result["imports"].append(base_package)

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

            # Check field names for coding patterns
            for child in node.children:
                if child.type == "variable_declarator":
                    name_node = child.child_by_field_name("name")
                    if name_node:
                        field_name = self._get_node_text(name_node, source_code)
                        self._detect_coding_patterns_by_name(field_name)

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

    def _detect_coding_patterns_by_name(self, name: str) -> None:
        """Detect coding patterns based on naming conventions.

        Args:
            name: Class, method, or field name
        """
        name_lower = name.lower()

        # Check for coding patterns
        for pattern_name, indicators in CODING_PATTERNS.items():
            if any(indicator.lower() in name_lower for indicator in indicators):
                self.result["coding_patterns"].add(pattern_name)

    def _extract_base_type(self, type_node: Node, source_code: bytes) -> str:
        """Extract base type identifier from type node, handling generics.

        Args:
            type_node: Type node from AST
            source_code: Source code bytes

        Returns:
            Base type identifier (e.g., "Queue" from "Queue<Node>")
        """
        # Look for type_identifier child node
        for child in type_node.children:
            if child.type == "type_identifier":
                return self._get_node_text(child, source_code)

        # If generic_type, get the first type_identifier
        if type_node.type == "generic_type":
            for child in type_node.children:
                if child.type == "type_identifier":
                    return self._get_node_text(child, source_code)

        # Fallback: get full text and extract first word
        full_text = self._get_node_text(type_node, source_code)
        # Handle "Queue<Node>" -> "Queue"
        if "<" in full_text:
            return full_text.split("<")[0].strip()
        return full_text.strip()

    def _detect_bfs_dfs_in_method(self, method_body: Node, source_code: bytes) -> None:
        """Analyze method body to detect BFS or DFS algorithm usage using AST patterns.

        Args:
            method_body: Method body AST node
            source_code: Source code bytes
        """
        # Analyze for Queue/Stack variable declarations and their usage patterns
        self._analyze_algorithm_patterns(method_body, source_code)

    def _analyze_algorithm_patterns(
        self, node: Node, source_code: bytes
    ) -> tuple[bool, bool, bool, bool]:
        """Recursively analyze AST for BFS/DFS patterns.

        Args:
            node: AST node to analyze
            source_code: Source code bytes

        Returns:
            Tuple of (has_queue_var, has_stack_var, queue_ops, stack_ops)
        """
        has_queue_var = False
        has_stack_var = False
        queue_operations = False
        stack_operations = False

        # Check for variable declarations
        if node.type == "local_variable_declaration":
            type_node = node.child_by_field_name("type")
            if type_node:
                # Extract type identifier, handling generics
                type_identifier = self._extract_base_type(type_node, source_code)
                # Exact match for Queue types (not substrings)
                if type_identifier in ("Queue", "LinkedList", "ArrayDeque", "PriorityQueue"):
                    has_queue_var = True
                # Exact match for Stack
                elif type_identifier == "Stack":
                    has_stack_var = True

        # Check for method invocations that indicate BFS/DFS operations
        elif node.type == "method_invocation":
            name_node = node.child_by_field_name("name")
            if name_node:
                method_name = self._get_node_text(name_node, source_code)
                # Queue operations: offer, poll, add, remove, peek
                if method_name in ("offer", "poll", "add", "remove", "peek"):
                    queue_operations = True
                # Stack operations: push, pop, peek
                elif method_name in ("push", "pop"):
                    stack_operations = True

        # Recurse through children
        for child in node.children:
            child_hq, child_hs, child_qo, child_so = self._analyze_algorithm_patterns(
                child, source_code
            )
            has_queue_var = has_queue_var or child_hq
            has_stack_var = has_stack_var or child_hs
            queue_operations = queue_operations or child_qo
            stack_operations = stack_operations or child_so

        # Update results based on patterns
        if has_queue_var and queue_operations:
            self.result["uses_bfs"] = True
        if has_stack_var and stack_operations:
            self.result["uses_dfs"] = True

        return has_queue_var, has_stack_var, queue_operations, stack_operations

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

        # After initial pass, analyze method bodies for BFS/DFS (only if not found yet)
        if not self.result["uses_bfs"] or not self.result["uses_dfs"]:
            for body_node, body_source in self.current_method_bodies:
                if not (self.result["uses_bfs"] and self.result["uses_dfs"]):
                    self._detect_bfs_dfs_in_method(body_node, body_source)
                else:
                    break  # Found both, no need to continue

        # Clear method bodies for this file to free memory
        self.current_method_bodies.clear()

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
        self.result["coding_patterns"] = sorted(self.result["coding_patterns"])

        # Count and get top imports
        from collections import Counter

        import_counts = Counter(self.result["imports"])
        self.result["top_imports"] = [
            {"package": pkg, "count": count} for pkg, count in import_counts.most_common(10)
        ]
        del self.result["imports"]  # Remove raw import list

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
            "uses_recursion": bool,        # Whether recursion is detected
            "uses_bfs": bool,              # Whether BFS algorithm is detected
            "uses_dfs": bool,              # Whether DFS algorithm is detected
            "coding_patterns": list[str],  # Detected coding patterns (6 patterns)
            "top_imports": list[dict],     # Top 10 imported packages with counts
        }
        Or on error: {"error": str}
    """
    return JavaAnalyzer(project_root).analyze()
