"""Python code analyzer for extracting project metrics and features."""

from __future__ import annotations

import ast
import json
import os
import re
from collections import defaultdict
from pathlib import Path

from capstone_project_team_5.constants.skill_detection_constants import SKIP_DIRS


class PythonAnalyzer:
    """Analyzes Python source code for OOP features, tech stack, and metrics."""

    def __init__(self, project_path: str | Path) -> None:
        """Initialize the analyzer with a Python project root directory.

        Args:
            project_path: Path to the Python project root directory
        """
        self.project_path = Path(project_path)
        self.all_code_content = ""
        self.imports = set()
        self.ast_trees = []
        self.file_count = 0
        self.files_analyzed = 0

    def analyze(self) -> dict:
        """Run full analysis on the Python project.

        Returns:
            Dictionary with analysis results or error message.
            On success:
            {
                "oop": dict with OOP analysis,
                "tech_stack": dict with detected frameworks/tools,
                "features": list of detected features,
                "integrations": dict with external integrations,
                "skills_demonstrated": list of skills,
                "metrics": dict with code metrics,
                "data_structures": list of detected data structures,
                "algorithms": list of detected algorithms,
                "design_patterns": list of detected design patterns,
            }
            On error: {"error": str}
        """
        # Validate project path
        if not self.project_path.exists():
            return {"error": f"Project root does not exist: {self.project_path}"}

        if not self.project_path.is_dir():
            return {"error": f"Project root is not a directory: {self.project_path}"}

        try:
            self._load_code_and_ast()
            self._extract_imports()

            # Check if any Python files were found
            if self.file_count == 0:
                return {"error": "No Python files found in project"}

            oop = self._analyze_oop()
            metrics = self._count_metrics()
            tech_stack = self._detect_tech_stack()
            features = self._detect_features()
            integrations = self._detect_integrations()
            data_structures = self._detect_data_structures()
            algorithms = self._detect_algorithms()
            design_patterns = self._detect_design_patterns()
            skills = self._generate_skills_list(
                tech_stack=tech_stack, features=features, integrations=integrations, oop=oop
            )

            return {
                "oop": oop,
                "tech_stack": tech_stack,
                "features": features,
                "integrations": integrations,
                "skills_demonstrated": skills,
                "metrics": metrics,
                "data_structures": data_structures,
                "algorithms": algorithms,
                "design_patterns": design_patterns,
            }

        except Exception as e:
            return {"error": f"Analysis failed: {str(e)}"}

    # ---------------------------------------------------------
    # LOAD CODE
    # ---------------------------------------------------------

    def _load_code_and_ast(self) -> None:
        """Load Python source code and parse AST in a single filesystem walk."""
        code_files: list[str] = []
        trees: list[ast.AST] = []
        self.file_count = 0
        self.files_analyzed = 0

        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [directory for directory in dirs if directory not in SKIP_DIRS]

            for file_name in files:
                if not file_name.endswith(".py"):
                    continue

                self.file_count += 1
                file_path = Path(root) / file_name

                try:
                    code = file_path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue

                code_files.append(code)
                self.files_analyzed += 1

                try:
                    trees.append(ast.parse(code, filename=str(file_path)))
                except Exception:
                    continue

        self.all_code_content = "\n".join(code_files)
        self.ast_trees = trees

    def _load_code_content(self) -> None:
        """Load all Python source code from the project directory."""
        # Kept for backward compatibility.
        if not self.all_code_content or not self.ast_trees:
            self._load_code_and_ast()

    # ---------------------------------------------------------
    # IMPORT PARSING
    # ---------------------------------------------------------

    def _extract_imports(self) -> None:
        """Extract import statements using regex."""
        imports = set()

        for line in self.all_code_content.splitlines():
            m1 = re.match(r"^\s*import\s+([a-zA-Z0-9_\.]+)", line)
            m2 = re.match(r"^\s*from\s+([a-zA-Z0-9_\.]+)", line)

            if m1:
                imports.add(m1.group(1).split(".")[0])
            if m2:
                imports.add(m2.group(1).split(".")[0])

        self.imports = imports

    # ---------------------------------------------------------
    # AST PARSING
    # ---------------------------------------------------------

    def _parse_ast(self) -> None:
        """Ensure AST trees are available for all Python files.

        This method reuses the combined loader to avoid an extra filesystem walk.
        """
        if not self.ast_trees:
            self._load_code_and_ast()

    # ---------------------------------------------------------
    # METRICS COUNTING
    # ---------------------------------------------------------

    def _count_metrics(self) -> dict:
        """Count code metrics: files, LOC, classes, methods.

        Returns:
            Dictionary with total_files, files_analyzed, lines_of_code,
            classes_count, and methods_count.
        """
        lines_of_code = 0
        classes_count: int = 0
        methods_count: int = 0
        function_complexities: list[int] = []

        # Count LOC from all code content
        for line in self.all_code_content.splitlines():
            stripped = line.strip()
            # Skip empty lines and comments
            if stripped and not stripped.startswith("#"):
                lines_of_code += 1

        # Count classes and methods from AST
        for tree in self.ast_trees:
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes_count += 1
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods_count += 1
                    function_complexities.append(self._calculate_function_complexity(node))

        avg_function_complexity = 0.0
        max_function_complexity = 0
        if function_complexities:
            max_function_complexity = max(function_complexities)
            avg_function_complexity = sum(function_complexities) / len(function_complexities)

        return {
            "total_files": self.file_count,
            "files_analyzed": self.files_analyzed,
            "lines_of_code": lines_of_code,
            "classes_count": classes_count,
            "methods_count": methods_count,
            "avg_function_complexity": avg_function_complexity,
            "max_function_complexity": max_function_complexity,
        }

    # ---------------------------------------------------------
    # OOP ANALYSIS
    # ---------------------------------------------------------

    def _analyze_oop(self) -> dict:
        """Analyze OOP features including all 4 principles.

        Returns:
            Dictionary with OOP analysis including classes, inheritance,
            encapsulation, polymorphism, and abstraction detection.
        """
        classes = {}
        inheritance = False
        encapsulation = False
        polymorphism = False
        abstraction = False
        method_map = defaultdict(list)

        for tree in self.ast_trees:
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue

                cname = node.name

                # Inheritance detection
                bases = [base.id for base in node.bases if isinstance(base, ast.Name)]
                if bases:
                    inheritance = True

                # Encapsulation detection (private attributes)
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Assign):
                        for tgt in sub.targets:
                            # Only consider attribute assignments, e.g., self._x
                            if isinstance(tgt, ast.Attribute):
                                attr_name = tgt.attr

                                # Must start with _ but not __dunder__
                                if not attr_name.startswith("_"):
                                    continue
                                if attr_name.startswith("__") and attr_name.endswith("__"):
                                    continue

                                val = tgt.value
                                # self._x, cls._x, ClassName._x
                                if isinstance(val, ast.Name) and val.id in {"self", "cls", cname}:
                                    encapsulation = True

                # Abstraction detection (abstract methods)
                for sub in node.body:
                    if isinstance(sub, ast.FunctionDef):
                        # Check for @abstractmethod decorator
                        for dec in sub.decorator_list:
                            is_abstract = (
                                isinstance(dec, ast.Name)
                                and dec.id == "abstractmethod"
                                or isinstance(dec, ast.Attribute)
                                and dec.attr == "abstractmethod"
                            )
                            if is_abstract:
                                abstraction = True

                        # Check for raise NotImplementedError
                        for stmt in ast.walk(sub):
                            if isinstance(stmt, ast.Raise):
                                if isinstance(stmt.exc, ast.Name):
                                    if stmt.exc.id == "NotImplementedError":
                                        abstraction = True
                                elif (
                                    isinstance(stmt.exc, ast.Call)
                                    and isinstance(stmt.exc.func, ast.Name)
                                    and stmt.exc.func.id == "NotImplementedError"
                                ):
                                    abstraction = True

                        # Collect methods for polymorphism detection
                        method_map[cname].append(sub.name)

                classes[cname] = bases

        # Polymorphism: same method names in different classes
        cls_names = list(method_map.keys())
        for i in range(len(cls_names)):
            for j in range(i + 1, len(cls_names)):
                if set(method_map[cls_names[i]]) & set(method_map[cls_names[j]]):
                    polymorphism = True

        return {
            "classes": classes,
            "inheritance": inheritance,
            "encapsulation": encapsulation,
            "polymorphism": polymorphism,
            "abstraction": abstraction,
        }

    # ---------------------------------------------------------
    # COMPLEXITY ANALYSIS
    # ---------------------------------------------------------

    def _calculate_function_complexity(self, node: ast.AST) -> int:
        """Approximate cyclomatic complexity for a single function.

        This is a lightweight estimate based on common branching constructs.
        """
        complexity = 1
        for child in ast.walk(node):
            if isinstance(
                child,
                (
                    ast.If,
                    ast.For,
                    ast.AsyncFor,
                    ast.While,
                    ast.With,
                    ast.AsyncWith,
                    ast.Try,
                    ast.BoolOp,
                    ast.IfExp,
                    ast.comprehension,
                ),
            ):
                complexity += 1
        return complexity

    # ---------------------------------------------------------
    # DATA STRUCTURES DETECTION
    # ---------------------------------------------------------

    def _detect_data_structures(self) -> list[str]:
        """Detect Python data structures used in the codebase.

        Returns:
            Sorted list of detected data structures.
        """
        structures: set[str] = set()
        code = self.all_code_content

        # Check for collections module structures
        if "collections" in self.imports or "from collections" in code:
            if "deque" in code:
                structures.add("deque")
            if "Counter" in code:
                structures.add("Counter")
            if "defaultdict" in code:
                structures.add("defaultdict")
            if "OrderedDict" in code:
                structures.add("OrderedDict")
            if "namedtuple" in code:
                structures.add("namedtuple")

        # Use AST to detect built-in data structures to avoid string-based
        # false positives (for example, indexing versus literal lists).
        for tree in self.ast_trees:
            for node in ast.walk(tree):
                if isinstance(node, (ast.List, ast.ListComp)):
                    structures.add("list")
                elif isinstance(node, (ast.Dict, ast.DictComp)):
                    structures.add("dict")
                elif isinstance(node, (ast.Set, ast.SetComp)):
                    structures.add("set")
                elif isinstance(node, ast.Tuple):
                    structures.add("tuple")
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    function_name = node.func.id
                    if function_name == "list":
                        structures.add("list")
                    elif function_name == "dict":
                        structures.add("dict")
                    elif function_name == "set":
                        structures.add("set")
                    elif function_name == "tuple":
                        structures.add("tuple")

        # Check for heapq
        if "heapq" in self.imports:
            structures.add("heap")

        return sorted(list(structures))

    # ---------------------------------------------------------
    # ALGORITHMS DETECTION
    # ---------------------------------------------------------

    def _detect_algorithms(self) -> list[str]:
        """Detect algorithm patterns used in the codebase.

        Returns:
            Sorted list of detected algorithms.
        """
        algorithms = set()

        # Detect recursion
        for tree in self.ast_trees:
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_name = node.name
                    # Check if function calls itself
                    for sub in ast.walk(node):
                        if (
                            isinstance(sub, ast.Call)
                            and isinstance(sub.func, ast.Name)
                            and sub.func.id == func_name
                        ):
                            algorithms.add("Recursion")
                            break

        # Detect sorting
        if "sorted(" in self.all_code_content or ".sort(" in self.all_code_content:
            algorithms.add("Sorting")

        # Detect searching
        if ".find(" in self.all_code_content or ".index(" in self.all_code_content:
            algorithms.add("Searching")

        # Detect dynamic programming patterns
        if "memo" in self.all_code_content.lower() or "dp[" in self.all_code_content:
            algorithms.add("Dynamic Programming")

        return sorted(list(algorithms))

    # ---------------------------------------------------------
    # DESIGN PATTERNS DETECTION
    # ---------------------------------------------------------

    def _detect_design_patterns(self) -> list[str]:
        """Detect common design patterns in the codebase.

        Returns:
            Sorted list of detected design patterns.
        """
        patterns: set[str] = set()

        for tree in self.ast_trees:
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    if self._is_singleton_class(node):
                        patterns.add("Singleton")
                    if self._is_observer_class(node):
                        patterns.add("Observer")
                    if self._is_strategy_class(node):
                        patterns.add("Strategy")
                    if self._is_decorator_class(node):
                        patterns.add("Decorator")
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if self._is_factory_function(node):
                        patterns.add("Factory")
                    if self._is_builder_function(node):
                        patterns.add("Builder")

        return sorted(list(patterns))

    def _is_singleton_class(self, class_node: ast.ClassDef) -> bool:
        """Heuristic detection of a Singleton-style class."""
        has_instance_attribute = False
        has_classmethod_accessor = False

        for statement in class_node.body:
            if isinstance(statement, ast.Assign):
                for target in statement.targets:
                    if (
                        isinstance(target, ast.Name)
                        and "instance" in target.id.lower()
                        or isinstance(target, ast.Attribute)
                        and "instance" in target.attr.lower()
                    ):
                        has_instance_attribute = True

        for statement in class_node.body:
            if not isinstance(statement, ast.FunctionDef):
                continue

            decorator_names = {
                decorator.id
                for decorator in statement.decorator_list
                if isinstance(decorator, ast.Name)
            }
            if "classmethod" not in decorator_names:
                continue

            for inner in ast.walk(statement):
                if (
                    isinstance(inner, ast.Return)
                    and isinstance(inner.value, ast.Attribute)
                    and isinstance(inner.value.value, ast.Name)
                    and inner.value.attr.lower().endswith("instance")
                ):
                    has_classmethod_accessor = True
                    break

        return has_instance_attribute and has_classmethod_accessor

    def _is_factory_function(self, function_node: ast.AST) -> bool:
        """Heuristic detection of a factory function.

        Marks a function as a factory when it conditionally constructs
        different types (multiple constructor calls).
        """
        constructor_names: set[str] = set()
        for child in ast.walk(function_node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                constructor_names.add(child.func.id)
        return len(constructor_names) >= 2

    def _is_builder_function(self, function_node: ast.AST) -> bool:
        """Heuristic detection of a builder-style `build` function."""
        if not isinstance(function_node, ast.FunctionDef):
            return False

        if function_node.name != "build":
            return False

        returns_constructed_object = False
        fluent_calls = False

        for child in ast.walk(function_node):
            if isinstance(child, ast.Return) and isinstance(child.value, ast.Call):
                returns_constructed_object = True
            if (
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Attribute)
                and isinstance(child.func.value, ast.Name)
                and child.func.value.id == "self"
            ):
                fluent_calls = True

        return returns_constructed_object or fluent_calls

    def _is_observer_class(self, class_node: ast.ClassDef) -> bool:
        """Heuristic detection of an Observer-style class."""
        has_observers_attribute = False
        has_subscribe_method = False
        has_notify_method = False

        for statement in class_node.body:
            if isinstance(statement, ast.Assign):
                for target in statement.targets:
                    if (
                        isinstance(target, ast.Name)
                        and "observer" in target.id.lower()
                        or isinstance(target, ast.Attribute)
                        and "observer" in target.attr.lower()
                    ):
                        has_observers_attribute = True
            elif isinstance(statement, ast.FunctionDef):
                method_name = statement.name.lower()
                if method_name in {"subscribe", "attach", "register"}:
                    has_subscribe_method = True
                if method_name.startswith("notify"):
                    has_notify_method = True

        return has_observers_attribute and has_subscribe_method and has_notify_method

    def _is_strategy_class(self, class_node: ast.ClassDef) -> bool:
        """Heuristic detection of a Strategy-style class."""
        has_strategy_attribute = False
        uses_strategy_attribute = False

        for statement in class_node.body:
            if isinstance(statement, ast.Assign):
                for target in statement.targets:
                    if (
                        isinstance(target, ast.Name)
                        and "strategy" in target.id.lower()
                        or isinstance(target, ast.Attribute)
                        and "strategy" in target.attr.lower()
                    ):
                        has_strategy_attribute = True

        for statement in class_node.body:
            if not isinstance(statement, ast.FunctionDef):
                continue

            for child in ast.walk(statement):
                if (
                    isinstance(child, ast.Attribute)
                    and isinstance(child.value, ast.Name)
                    and child.value.id in {"self", class_node.name}
                    and "strategy" in child.attr.lower()
                ):
                    uses_strategy_attribute = True

        return has_strategy_attribute and uses_strategy_attribute

    def _is_decorator_class(self, class_node: ast.ClassDef) -> bool:
        """Heuristic detection of a Decorator-style class (GoF pattern)."""
        class_name_lower = class_node.name.lower()
        has_wrapper_name = "decorator" in class_name_lower or "wrapper" in class_name_lower
        has_call_method = any(
            isinstance(statement, ast.FunctionDef) and statement.name == "__call__"
            for statement in class_node.body
        )

        return has_wrapper_name and has_call_method

    # ---------------------------------------------------------
    # TECH STACK DETECTION
    # ---------------------------------------------------------

    def _detect_tech_stack(self) -> dict:
        imports = self.imports

        stack = {
            "frameworks": [],
            "database": [],
            "testing": [],
            "tooling": [],
        }

        if "flask" in imports:
            stack["frameworks"].append("Flask")
        if "django" in imports:
            stack["frameworks"].append("Django")
        if "fastapi" in imports:
            stack["frameworks"].append("FastAPI")

        if "sqlalchemy" in imports:
            stack["database"].append("SQLAlchemy ORM")
        if "pymongo" in imports:
            stack["database"].append("MongoDB")
        if "psycopg2" in imports:
            stack["database"].append("PostgreSQL")
        if "pymysql" in imports:
            stack["database"].append("MySQL")

        if "pytest" in imports:
            stack["testing"].append("PyTest")
        if "unittest" in imports:
            stack["testing"].append("unittest")

        if "pydantic" in imports:
            stack["tooling"].append("Pydantic")
        if "click" in imports:
            stack["tooling"].append("Click")
        if "typer" in imports:
            stack["tooling"].append("Typer")

        return {k: v for k, v in stack.items() if v}

    # ---------------------------------------------------------
    # FEATURE DETECTION
    # ---------------------------------------------------------

    def _detect_features(self) -> list[str]:
        code = self.all_code_content.lower()
        features = []

        if "def get_" in code or "def post_" in code:
            features.append("API Endpoints")
        if "async def" in code:
            features.append("Asynchronous Programming")
        if "class " in code and "__init__" in code:
            features.append("Object-Oriented Design")
        if "import threading" in code:
            features.append("Multithreading")
        if "import multiprocessing" in code:
            features.append("Multiprocessing")

        return features

    # ---------------------------------------------------------
    # INTEGRATION DETECTION
    # ---------------------------------------------------------

    def _detect_integrations(self) -> dict[str, list[str]]:
        imports = self.imports
        integrations = defaultdict(list)

        if "requests" in imports:
            integrations["http"].append("Requests")
        if "boto3" in imports:
            integrations["aws"].append("Boto3")
        if "redis" in imports:
            integrations["cache"].append("Redis")
        if "pandas" in imports:
            integrations["data"].append("Pandas")
        if "numpy" in imports:
            integrations["data"].append("NumPy")

        return dict(integrations)

    # ---------------------------------------------------------
    # SKILL LIST
    # ---------------------------------------------------------

    def _generate_skills_list(self, tech_stack, features, integrations, oop) -> list[str]:
        skills = set()

        for _, items in tech_stack.items():
            skills.update(items)

        skills.update(features)

        if "Object-Oriented Design" in features or oop.get("classes"):
            skills.add("Object-Oriented Design")

        if oop["inheritance"]:
            skills.add("Object-Oriented Programming (Inheritance)")
        if oop["encapsulation"]:
            skills.add("Encapsulation & Private Attributes")
        if oop["polymorphism"]:
            skills.add("Polymorphism")
        if oop.get("abstraction"):
            skills.add("Abstraction")

        if "http" in integrations:
            skills.add("HTTP API Integration")
        if "aws" in integrations:
            skills.add("AWS Integration")
        if "cache" in integrations:
            skills.add("Caching & Messaging")
        if "data" in integrations:
            skills.add("Data Processing")

        return sorted(list(skills))


def analyze_python_project(project_root: Path | str) -> dict:
    """Analyze a Python project and return comprehensive analysis results.

    This is the main entry point for Python project analysis, providing a
    consistent interface for integration with the unified project analysis system.

    Args:
        project_root: Path to the Python project root directory

    Returns:
        Dictionary with analysis results:
        {
            "total_files": int,              # Total .py files found
            "files_analyzed": int,           # Files successfully analyzed
            "lines_of_code": int,            # Total lines of code
            "classes_count": int,            # Total classes
            "methods_count": int,            # Total methods/functions
            "oop_principles": {              # OOP principles detected
                "Encapsulation": bool,
                "Inheritance": bool,
                "Polymorphism": bool,
                "Abstraction": bool,
            },
            "complexity_score": float,       # Approximate complexity score (0-10)
            "data_structures": list[str],    # Detected data structures
            "algorithms": list[str],         # Detected algorithms
            "design_patterns": list[str],    # Detected design patterns
            "tech_stack": dict,              # Frameworks and tools
            "features": list[str],           # Language features used
            "integrations": dict,            # External integrations
            "skills_demonstrated": list[str] # Aggregated skills
        }
        Or on error: {"error": str}

    Example:
        >>> result = analyze_python_project("/path/to/project")
        >>> if "error" not in result:
        ...     print(f"Found {result['classes_count']} classes")
    """
    try:
        analyzer = PythonAnalyzer(project_root)
        result = analyzer.analyze()

        # Check for error
        if "error" in result:
            return result

        # Transform to expected format
        oop = result.get("oop", {})
        metrics = result.get("metrics", {})
        avg_complexity = metrics.get("avg_function_complexity", 0.0)
        complexity_score = 0.0
        if isinstance(avg_complexity, (int, float)):
            complexity_score = min(10.0, float(avg_complexity))

        return {
            "total_files": metrics.get("total_files", 0),
            "files_analyzed": metrics.get("files_analyzed", 0),
            "lines_of_code": metrics.get("lines_of_code", 0),
            "classes_count": metrics.get("classes_count", 0),
            "methods_count": metrics.get("methods_count", 0),
            "oop_principles": {
                "Encapsulation": oop.get("encapsulation", False),
                "Inheritance": oop.get("inheritance", False),
                "Polymorphism": oop.get("polymorphism", False),
                "Abstraction": oop.get("abstraction", False),
            },
            "complexity_score": complexity_score,
            "data_structures": result.get("data_structures", []),
            "algorithms": result.get("algorithms", []),
            "design_patterns": result.get("design_patterns", []),
            "tech_stack": result.get("tech_stack", {}),
            "features": result.get("features", []),
            "integrations": result.get("integrations", {}),
            "skills_demonstrated": result.get("skills_demonstrated", []),
        }

    except Exception as e:
        return {"error": f"Failed to analyze Python project: {str(e)}"}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyze a Python codebase.")
    parser.add_argument("path", help="Path to the Python project directory")
    args = parser.parse_args()

    result = analyze_python_project(args.path)

    print(json.dumps(result, indent=2))
