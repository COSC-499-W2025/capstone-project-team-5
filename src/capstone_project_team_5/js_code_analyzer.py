import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import esprima

from capstone_project_team_5.constants.js_ts_analysis_constants import (
    FEATURE_PATTERNS,
    INTEGRATION_MAP,
)
from capstone_project_team_5.constants.skill_detection_constants import SKIP_DIRS


@dataclass
class JSProjectSummary:
    """Summary of JS/TS project analysis."""

    total_files: int = 0
    total_lines_of_code: int = 0
    total_functions: int = 0
    total_classes: int = 0

    tech_stack: dict = field(default_factory=dict)
    features: list[str] = field(default_factory=list)
    integrations: dict = field(default_factory=dict)
    skills_demonstrated: list[str] = field(default_factory=list)

    uses_typescript: bool = False
    uses_react: bool = False
    uses_vue: bool = False
    uses_angular: bool = False
    uses_nodejs: bool = False

    design_patterns: set[str] = field(default_factory=set)
    data_structures: set[str] = field(default_factory=set)
    algorithms_used: set[str] = field(default_factory=set)

    total_imports: int = 0
    total_exports: int = 0
    avg_function_complexity: float = 0.0
    max_function_complexity: int = 0
    uses_async_await: bool = False
    uses_promises: bool = False
    custom_hooks_count: int = 0
    oop_features: set[str] = field(default_factory=set)


@dataclass
class ASTMetrics:
    """Metrics extracted from AST analysis."""

    function_count: int = 0
    class_count: int = 0
    import_count: int = 0
    export_count: int = 0
    async_function_count: int = 0
    arrow_function_count: int = 0
    complexity_scores: list[int] = field(default_factory=list)
    custom_hooks: set[str] = field(default_factory=set)
    design_patterns: set[str] = field(default_factory=set)
    uses_promises: bool = False


class ASTAnalyzer:
    """Handles AST-based code analysis for JavaScript/TypeScript."""

    def __init__(self):
        self.metrics = ASTMetrics()

    def analyze_file(self, code: str, file_path: str) -> None:
        """
        Analyze a single file's AST.

        Args:
            code: Source code content
            file_path: Path to the file (for context)
        """

        if file_path.endswith((".ts", ".tsx")):
            code = self._strip_typescript_syntax(code)

        try:
            ast = esprima.parseModule(code, {"jsx": True, "tolerant": True})
            ast_dict = ast.toDict()
            self._traverse(ast_dict)

        except Exception:
            # Fallback to script mode if module fails
            try:
                ast = esprima.parseScript(code, {"jsx": True, "tolerant": True})
                ast_dict = ast.toDict()
                self._traverse(ast_dict)

            except Exception:
                # If parsing fails completely, skip this file
                pass

    def _strip_typescript_syntax(self, code: str) -> str:
        """
        Basic TypeScript syntax stripping for parsing.

        Note: This is a best-effort approach. Complex TypeScript may still fail to parse.
        """

        # Remove import type statements
        code = re.sub(r'import\s+type\s+.*?from\s+[\'"][^\'"]+[\'"];?', "", code)

        # Remove type-only imports
        code = re.sub(r'import\s*\{\s*type\s+[^}]+\}\s*from\s+[\'"][^\'"]+[\'"];?', "", code)

        # Remove interface declarations
        code = re.sub(r"interface\s+\w+\s*\{[^}]*\}", "", code, flags=re.DOTALL)

        # Remove type aliases
        code = re.sub(r"type\s+\w+\s*=\s*[^;]+;", "", code)

        # Remove generic type parameters from function/class declarations
        code = re.sub(r"<[A-Z]\w*(?:\s*,\s*[A-Z]\w*)*>(?=\s*\()", "", code)

        # Remove return type annotations: ): Type {
        code = re.sub(r"\):\s*\w+(?:\[\])?(?:\s*\|\s*\w+)*\s*\{", ") {", code)

        # Remove parameter type annotations: (param: Type)
        code = re.sub(r":\s*\w+(?:\[\])?(?:\s*\|\s*\w+)*(?=\s*[,\)])", "", code)

        # Remove variable type annotations: const x: Type =
        code = re.sub(r":\s*\w+(?:\[\])?(?:\s*\|\s*\w+)*(?=\s*=)", "", code)

        # Remove type assertions: as Type
        code = re.sub(r"\s+as\s+\w+", "", code)

        # Remove angle bracket type assertions: <Type>
        code = re.sub(r"<\w+>", "", code)

        # Remove readonly, public, private, protected modifiers
        code = re.sub(r"\b(readonly|public|private|protected)\s+", "", code)

        # Remove implements clause
        code = re.sub(r"\s+implements\s+\w+(?:\s*,\s*\w+)*", "", code)

        return code

    def _traverse(self, node: Any, parent: Any = None) -> None:
        """Recursively traverse AST nodes."""

        if not isinstance(node, dict) or "type" not in node:
            return

        node_type = node["type"]

        # Count functions
        if node_type in ("FunctionDeclaration", "FunctionExpression"):
            self.metrics.function_count += 1
            complexity = self._calculate_complexity(node)
            self.metrics.complexity_scores.append(complexity)

            if node.get("async"):
                self.metrics.async_function_count += 1

            # Detect custom React hooks
            func_name = node.get("id", {}).get("name", "")
            if func_name.startswith("use") and len(func_name) > 3 and func_name[3].isupper():
                self.metrics.custom_hooks.add(func_name)

        elif node_type == "ArrowFunctionExpression":
            self.metrics.arrow_function_count += 1
            self.metrics.function_count += 1
            complexity = self._calculate_complexity(node)
            self.metrics.complexity_scores.append(complexity)

            if node.get("async"):
                self.metrics.async_function_count += 1

        elif node_type == "ClassDeclaration":
            self.metrics.class_count += 1
            self._detect_class_patterns(node)

        elif node_type in ("ImportDeclaration", "ImportExpression"):
            self.metrics.import_count += 1

        elif node_type in (
            "ExportNamedDeclaration",
            "ExportDefaultDeclaration",
            "ExportAllDeclaration",
        ):
            self.metrics.export_count += 1

        elif node_type == "CallExpression":
            self._detect_call_patterns(node)
            self._detect_promise_usage(node)

        # Traverse children
        for _key, value in node.items():
            if isinstance(value, dict):
                self._traverse(value, node)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        self._traverse(item, node)

    def _calculate_complexity(self, func_node: dict) -> int:
        """Calculate cyclomatic complexity of a function."""

        complexity = 1

        def count_complexity(node):
            nonlocal complexity

            if not isinstance(node, dict):
                return

            node_type = node.get("type")

            if (
                node_type
                in (
                    "IfStatement",
                    "ConditionalExpression",
                    "WhileStatement",
                    "ForStatement",
                    "ForInStatement",
                    "ForOfStatement",
                    "CatchClause",
                    "SwitchCase",
                )
                or node_type == "LogicalExpression"
                and node.get("operator") in ("&&", "||")
            ):
                complexity += 1

            for value in node.values():
                if isinstance(value, dict):
                    count_complexity(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            count_complexity(item)

        count_complexity(func_node)
        return complexity

    def _detect_class_patterns(self, class_node: dict) -> None:
        """Detect design patterns in class structure."""

        body = class_node.get("body", {})
        class_body = body.get("body", [])

        method_names = set()
        has_get_instance = False

        for item in class_body:
            if item.get("type") == "MethodDefinition":
                key = item.get("key", {})
                name = key.get("name", "")
                method_names.add(name)

                if name in ("getInstance", "instance"):
                    has_get_instance = True

        if has_get_instance:
            self.metrics.design_patterns.add("Singleton Pattern")

        if any(name.startswith("create") for name in method_names):
            self.metrics.design_patterns.add("Factory Pattern")

    def _detect_call_patterns(self, call_node: dict) -> None:
        """Detect patterns in function calls."""

        callee = call_node.get("callee", {})

        if callee.get("type") == "MemberExpression":
            prop = callee.get("property", {})
            method_name = prop.get("name", "")

            if method_name in ("addEventListener", "on", "subscribe", "observe"):
                self.metrics.design_patterns.add("Observer Pattern")
            elif method_name in ("map", "filter", "reduce"):
                self.metrics.design_patterns.add("Functional Programming Pattern")

    def _detect_promise_usage(self, call_node: dict) -> None:
        """Detect Promise usage patterns."""

        callee = call_node.get("callee", {})

        # new Promise()
        if callee.get("name") == "Promise":
            self.metrics.uses_promises = True

        # .then(), .catch(), .finally()
        if callee.get("type") == "MemberExpression":
            prop = callee.get("property", {})
            method_name = prop.get("name", "")
            if method_name in ("then", "catch", "finally"):
                self.metrics.uses_promises = True


def analyze_js_project(
    project_path: Path, language: str, framework: str | None
) -> JSProjectSummary:
    """
    Analyze a JS/TS project and return unified summary.

    This is the main entry point that maintains backward compatibility
    with existing code while providing enhanced AST-based analysis.

    Args:
        project_path: Path to the project directory
        language: Detected language (JavaScript/TypeScript)
        framework: Detected framework (React/Vue/etc.)

    Returns:
        JSProjectSummary with all analysis data
    """

    existing_content = {"language": language, "framework": framework}

    analyzer = JSTSAnalyzer(str(project_path), existing_content)
    results = analyzer.analyze()

    summary = JSProjectSummary()

    # Basic metrics
    summary.total_files = _count_js_files(project_path)
    summary.total_lines_of_code = _count_lines_of_code(analyzer.all_code_content)

    # AST-based metrics
    summary.total_functions = results.get("function_count", 0)
    summary.total_classes = results.get("class_count", 0)
    summary.total_imports = results.get("import_count", 0)
    summary.total_exports = results.get("export_count", 0)
    summary.custom_hooks_count = results.get("custom_hooks_count", 0)
    summary.uses_async_await = results.get("uses_async_await", False)
    summary.uses_promises = results.get("uses_promises", False)

    # Complexity metrics
    complexity_scores = results.get("complexity_scores", [])
    if complexity_scores:
        summary.avg_function_complexity = sum(complexity_scores) / len(complexity_scores)
        summary.max_function_complexity = max(complexity_scores)

    # Tech stack and features
    summary.tech_stack = results.get("tech_stack", {})
    summary.features = results.get("features", [])
    summary.integrations = results.get("integrations", {})
    summary.skills_demonstrated = results.get("skills_demonstrated", [])

    summary.uses_typescript = language == "TypeScript"

    frontend = summary.tech_stack.get("frontend", [])
    backend = summary.tech_stack.get("backend", [])

    summary.uses_react = any("React" in item for item in frontend)
    summary.uses_vue = any("Vue" in item for item in frontend)
    summary.uses_angular = any("Angular" in item for item in frontend)
    summary.uses_nodejs = any("Node.js" in item for item in backend)

    # Design patterns
    summary.design_patterns = results.get("design_patterns", set())

    # Map features to design patterns
    feature_to_pattern = {
        "State Management": "State Management Pattern",
        "User Authentication": "Authentication Pattern",
        "CRUD Operations": "Repository Pattern",
        "Client-side Routing": "Router Pattern",
        "Form Validation": "Validation Pattern",
    }

    for feature in summary.features:
        if feature in feature_to_pattern:
            summary.design_patterns.add(feature_to_pattern[feature])

    # Detect OOP features
    if summary.total_classes > 0:
        summary.oop_features.add("Classes")
        summary.oop_features.add("Encapsulation")

        if re.search(r"extends\s+\w+", analyzer.all_code_content):
            summary.oop_features.add("Inheritance")

        if summary.uses_typescript and re.search(r"implements\s+\w+", analyzer.all_code_content):
            summary.oop_features.add("Interfaces")

    # Detect data structures
    data_structure_patterns = {
        r"\bMap\s*\(": "Map",
        r"\bSet\s*\(": "Set",
        r"\bWeakMap\s*\(": "WeakMap",
        r"\bWeakSet\s*\(": "WeakSet",
        r"\.push\s*\(|\.pop\s*\(": "Array/Stack",
        r"\.shift\s*\(|\.unshift\s*\(": "Queue",
    }

    for pattern, structure in data_structure_patterns.items():
        if re.search(pattern, analyzer.all_code_content):
            summary.data_structures.add(structure)

    # Detect algorithms
    algorithm_patterns = {
        r"\.sort\s*\(": "Sorting",
        r"\.filter\s*\(": "Filtering",
        r"\.reduce\s*\(": "Reduction/Aggregation",
        r"\.map\s*\(": "Mapping/Transformation",
        r"recursiv|factorial": "Recursion",
        r"memoize|cache": "Memoization",
        r"debounce|throttle": "Debouncing/Throttling",
    }

    for pattern, algorithm in algorithm_patterns.items():
        if re.search(pattern, analyzer.all_code_content, re.IGNORECASE):
            summary.algorithms_used.add(algorithm)

    return summary


def _count_js_files(project_path: Path) -> int:
    """Count JS/TS files in project."""

    extensions = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
    count = 0

    for _root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        count += sum(1 for f in files if Path(f).suffix in extensions)

    return count


def _count_lines_of_code(code_content: str) -> int:
    """Count non-empty lines of code."""

    if not code_content:
        return 0
    return sum(1 for line in code_content.split("\n") if line.strip())


class JSTSAnalyzer:
    """
    Analyzes JS/TS projects for resume-relevant skills and features.
    Uses both AST analysis and pattern matching for comprehensive results.
    """

    def __init__(self, project_path: str, existing_content: dict):
        """
        Initialize analyzer with project path and existing detection results.

        Args:
            project_path: Root directory of the JS/TS project.
            existing_content: Dict containing language, framework from detection.
        """

        self.project_path = Path(project_path)
        self.context = existing_content
        self.package_jsons = []
        self.merged_dependencies = {}
        self.all_code_content = ""
        self.ast_analyzer = ASTAnalyzer()

    def analyze(self) -> dict:
        """
        Main analysis method - extracts all resume-relevant information.

        Returns:
            dict: Metrics, tech stack, features, integrations, and patterns.
        """

        self._load_package_json()
        self._load_and_analyze_code()

        tech_stack = self._extract_tech_stack()
        features = self._detect_features()
        integrations = self._detect_integrations()

        result = {
            "tech_stack": tech_stack,
            "features": features,
            "integrations": integrations,
            "skills_demonstrated": self._generate_skills_list(tech_stack, features, integrations),
            "design_patterns": set(),
        }

        if self.ast_analyzer:
            metrics = self.ast_analyzer.metrics
            result.update(
                {
                    "function_count": metrics.function_count,
                    "class_count": metrics.class_count,
                    "import_count": metrics.import_count,
                    "export_count": metrics.export_count,
                    "uses_async_await": metrics.async_function_count > 0,
                    "uses_promises": metrics.uses_promises,
                    "custom_hooks_count": len(metrics.custom_hooks),
                    "complexity_scores": metrics.complexity_scores,
                    "design_patterns": metrics.design_patterns,
                }
            )

        return result

    def _load_package_json(self):
        """Load and parse all package.json files in the project."""

        package_files = list(self.project_path.rglob("package.json"))
        package_files = [f for f in package_files if "node_modules" not in f.parts]

        if not package_files:
            return

        all_deps = {}
        all_dev_deps = {}

        for package_path in package_files:
            try:
                with open(package_path, encoding="utf-8") as f:
                    pkg_data = json.load(f)
                    deps = pkg_data.get("dependencies", {})
                    dev_deps = pkg_data.get("devDependencies", {})

                    all_deps.update(deps)
                    all_dev_deps.update(dev_deps)

                    self.package_jsons.append(
                        {"path": str(package_path.relative_to(self.project_path)), "data": pkg_data}
                    )
            except (OSError, json.JSONDecodeError):
                continue

        self.merged_dependencies = {"dependencies": all_deps, "devDependencies": all_dev_deps}

    def _load_and_analyze_code(self):
        """Load all JS/TS code and perform AST analysis."""

        code_extensions = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
        code_files = []

        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

            for file in files:
                if Path(file).suffix in code_extensions:
                    file_path = Path(root) / file
                    try:
                        with open(file_path, encoding="utf-8", errors="ignore") as f:
                            code_content = f.read()
                            code_files.append(code_content)

                            # Perform AST analysis on each file
                            if self.ast_analyzer:
                                self.ast_analyzer.analyze_file(code_content, str(file_path))
                    except Exception:
                        continue

        self.all_code_content = "\n".join(code_files)

    def _extract_tech_stack(self) -> dict:
        """Extract technology stack from package.json."""

        deps = self.merged_dependencies.get("dependencies", {})
        dev_deps = self.merged_dependencies.get("devDependencies", {})

        if not deps and not dev_deps:
            return {}

        all_deps = {**deps, **dev_deps}

        tech_stack = {
            "frontend": self._detect_frontend_stack(all_deps),
            "backend": self._detect_backend_stack(all_deps),
            "database": self._detect_database_stack(all_deps),
            "testing": self._detect_testing_stack(all_deps),
            "tooling": self._detect_tooling(all_deps),
        }

        return {k: v for k, v in tech_stack.items() if v}

    def _detect_frontend_stack(self, all_deps: dict) -> list[str]:
        """Detect frontend technologies."""

        stack = []
        language = self.context.get("language", "")

        if language == "TypeScript":
            stack.append("TypeScript")
        elif language == "JavaScript":
            stack.append("JavaScript")

        framework = self.context.get("framework", "")
        if framework and framework in ["React", "Vue", "Angular", "Svelte", "Next.js"]:
            stack.append(framework)

        if "react" in all_deps and "React" not in " ".join(stack):
            version = all_deps["react"].replace("^", "").replace("~", "")
            stack.append(f"React {version.split('.')[0]}")
        elif "vue" in all_deps and "Vue" not in " ".join(stack):
            stack.append("Vue")
        elif "@angular/core" in all_deps and "Angular" not in " ".join(stack):
            stack.append("Angular")
        elif "svelte" in all_deps and "Svelte" not in " ".join(stack):
            stack.append("Svelte")

        # UI Libraries
        ui_libs = {
            "@mui/material": "Material-UI",
            "@material-ui/core": "Material-UI",
            "antd": "Ant Design",
            "tailwindcss": "Tailwind CSS",
            "bootstrap": "Bootstrap",
            "react-bootstrap": "Bootstrap",
            "@chakra-ui/react": "Chakra UI",
        }

        for pkg, name in ui_libs.items():
            if pkg in all_deps and name not in stack:
                stack.append(name)

        # State Management
        state_mgmt = {
            "redux": "Redux",
            "@reduxjs/toolkit": "Redux",
            "mobx": "MobX",
            "zustand": "Zustand",
            "recoil": "Recoil",
        }

        for pkg, name in state_mgmt.items():
            if pkg in all_deps and name not in stack:
                stack.append(name)

        return stack

    def _detect_backend_stack(self, all_deps: dict) -> list[str]:
        """Detect backend technologies."""

        stack = []
        backend_frameworks = {
            "express": "Express",
            "fastify": "Fastify",
            "koa": "Koa",
            "@nestjs/core": "NestJS",
            "hapi": "Hapi",
        }

        nodejs_detected = False
        for pkg_name, display_name in backend_frameworks.items():
            if pkg_name in all_deps:
                stack.append(display_name)
                nodejs_detected = True

        if nodejs_detected:
            stack.insert(0, "Node.js")

        if "next" in all_deps and "Node.js" not in stack:
            stack.insert(0, "Node.js")
            stack.append("Next.js API Routes")

        if "graphql" in all_deps or "apollo-server" in all_deps:
            stack.append("GraphQL")

        return stack

    def _detect_database_stack(self, all_deps: dict) -> list[str]:
        """Detect database and ORM technologies."""

        stack = []

        db_tools = {
            "@prisma/client": "Prisma",
            "prisma": "Prisma",
            "mongoose": "MongoDB (Mongoose)",
            "typeorm": "TypeORM",
            "sequelize": "Sequelize",
            "knex": "Knex.js",
            "pg": "PostgreSQL",
            "mysql": "MySQL",
            "mysql2": "MySQL",
            "mongodb": "MongoDB",
            "redis": "Redis",
        }

        for pkg, name in db_tools.items():
            if pkg in all_deps and name not in stack:
                stack.append(name)

        return stack

    def _detect_testing_stack(self, all_deps: dict) -> list[str]:
        """Detect testing frameworks and tools."""

        stack = []

        testing_tools = {
            "jest": "Jest",
            "mocha": "Mocha",
            "vitest": "Vitest",
            "cypress": "Cypress",
            "@playwright/test": "Playwright",
            "playwright": "Playwright",
            "@testing-library/react": "React Testing Library",
        }

        for pkg, name in testing_tools.items():
            if pkg in all_deps and name not in stack:
                stack.append(name)

        return stack

    def _detect_tooling(self, all_deps: dict) -> list[str]:
        """Detect build and development tools."""

        tools = []

        build_tools = {
            "vite": "Vite",
            "webpack": "Webpack",
            "rollup": "Rollup",
            "parcel": "Parcel",
            "eslint": "ESLint",
            "prettier": "Prettier",
            "typescript": "TypeScript Compiler",
        }

        for pkg, name in build_tools.items():
            if pkg in all_deps and name not in tools:
                tools.append(name)

        return tools

    def _detect_features(self) -> list[str]:
        """Detect implemented features by scanning code patterns."""

        detected_features = []

        for feature_name, patterns in FEATURE_PATTERNS.items():
            if self._check_patterns(patterns):
                detected_features.append(self._format_feature_name(feature_name))

        return detected_features

    def _check_patterns(self, patterns: list[str]) -> bool:
        """Check if any pattern matches in the code content."""

        return any(re.search(pattern, self.all_code_content, re.IGNORECASE) for pattern in patterns)

    def _format_feature_name(self, feature_key: str) -> str:
        """Convert feature key to display name."""

        mapping = {
            "authentication": "User Authentication",
            "payment_processing": "Payment Processing",
            "file_uploads": "File Upload Handling",
            "real_time_updates": "Real-time Updates",
            "api_integration": "External API Integration",
            "state_management": "State Management",
            "form_validation": "Form Validation",
            "responsive_design": "Responsive Design",
            "internationalization": "Internationalization (i18n)",
            "crud_operations": "CRUD Operations",
            "routing": "Client-side Routing",
            "data_visualization": "Data Visualization",
        }

        return mapping.get(feature_key, feature_key.replace("_", " ").title())

    def _detect_integrations(self) -> dict[str, list[str]]:
        """Detect third-party service integrations."""

        if not self.merged_dependencies:
            return {}

        deps = self.merged_dependencies.get("dependencies", {})
        dev_deps = self.merged_dependencies.get("devDependencies", {})
        all_deps = {**deps, **dev_deps}

        integrations = defaultdict(list)

        for package_name, (category, display_name) in INTEGRATION_MAP.items():
            if package_name in all_deps and display_name not in integrations[category]:
                integrations[category].append(display_name)

        return dict(integrations)

    def _generate_skills_list(
        self, tech_stack: dict, features: list[str], integrations: dict
    ) -> list[str]:
        """Generate comprehensive skills list for resume."""

        skills = set()

        for _category, items in tech_stack.items():
            skills.update(items)

        # Map integration categories to skills
        integration_skills_map = {
            "payment": "Payment Integration",
            "auth": "Authentication & Authorization",
            "cloud": "Cloud Services",
            "realtime": "Real-time Communication",
            "visualization": "Data Visualization",
            "database": "Database Management",
        }

        for category in integrations:
            if category in integration_skills_map:
                skills.add(integration_skills_map[category])

        # Map features to skills
        feature_skills_map = {
            "User Authentication": "Authentication & Authorization",
            "Payment Processing": "Payment Integration",
            "Real-time Updates": "Real-time Communication",
            "External API Integration": "REST API Integration",
            "CRUD Operations": "RESTful API Development",
            "Responsive Design": "Responsive Web Design",
        }

        for feature in features:
            if feature in feature_skills_map:
                skills.add(feature_skills_map[feature])

        return sorted(list(skills))
