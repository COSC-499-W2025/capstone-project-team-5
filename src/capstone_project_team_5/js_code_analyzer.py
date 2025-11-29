import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from capstone_project_team_5.constants.js_ts_analysis_constants import (
    FEATURE_PATTERNS,
    INTEGRATION_MAP,
)
from capstone_project_team_5.constants.skill_detection_constants import SKIP_DIRS


@dataclass
class JSProjectSummary:
    """Summary of JS/TS project analysis - preserves rich analyzer output."""

    # Basic metrics
    total_files: int = 0
    total_lines_of_code: int = 0
    total_functions: int = 0
    total_classes: int = 0

    # Rich analysis from JSTSAnalyzer (this is your actual value!)
    tech_stack: dict = field(
        default_factory=dict
    )  # {frontend: [], backend: [], database: [], testing: [], tooling: []}
    features: list[str] = field(
        default_factory=list
    )  # ["User Authentication", "Payment Processing", ...]
    integrations: dict = field(default_factory=dict)  # {payment: [], auth: [], cloud: [], ...}
    skills_demonstrated: list[str] = field(default_factory=list)  # ["React", "Node.js", ...]

    # Feature flags (for compatibility with unified system)
    uses_typescript: bool = False
    uses_react: bool = False
    uses_vue: bool = False
    uses_angular: bool = False
    uses_nodejs: bool = False

    # These are less relevant for JS/TS but kept for compatibility
    design_patterns: set[str] = field(default_factory=set)
    data_structures: set[str] = field(default_factory=set)
    algorithms_used: set[str] = field(default_factory=set)


def analyze_js_project(
    project_path: Path, language: str, framework: str | None
) -> JSProjectSummary:
    """
    Analyze a JS/TS project and return unified summary.

    This wraps the JSTSAnalyzer and preserves all its rich output
    while providing compatibility with the unified analysis system.

    Args:
        project_path: Path to the project directory

    Returns:
        JSProjectSummary with all analysis data
    """

    existing_content = {"language": language, "framework": framework}

    analyzer = JSTSAnalyzer(str(project_path), existing_content)
    results = analyzer.analyze()

    summary = JSProjectSummary()
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

    # Count metrics
    summary.total_files = _count_js_files(project_path)
    summary.total_lines_of_code = _count_lines_of_code(analyzer.all_code_content)

    return summary


def _count_js_files(project_path: Path) -> int:
    """Count JS/TS files in project."""
    from capstone_project_team_5.constants.skill_detection_constants import SKIP_DIRS

    extensions = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
    count = 0

    for _root, dirs, files in project_path.walk():
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
    Can be called after detecting a project as JS/TS project.
    """

    def __init__(self, project_path: str, existing_content: dict):
        """
        Initialize analyzer with project path and existing detection results
        for language and framework.

        Args:
            project_path: Root directory of the JS/TS project.
            existing_content: Dict containing language, framework from detection.
        """

        self.project_path = Path(project_path)
        self.context = existing_content
        self.package_jsons = []  # List of found package.json files to account for multiple
        self.merged_dependencies = {}  # Combined dependencies from all package.json
        self.all_code_content = ""

    def analyze(self) -> dict:
        """
        Main analysis method - extracts all resume-relevant information.

        Returns:
            dict: Tech stack, features, integrations and skills.
        """

        self._load_package_json()
        self._load_code_content()

        tech_stack = self._extract_tech_stack()
        features = self._detect_features()
        integrations = self._detect_integrations()

        skills = self._generate_skills_list(
            tech_stack=tech_stack, features=features, integrations=integrations
        )

        return {
            "tech_stack": tech_stack,
            "features": features,
            "integrations": integrations,
            "skills_demonstrated": skills,
        }

    def _load_package_json(self):
        """
        Load and parse all package.json files in the project.
        Handles monorepos and multi-package projects.
        """

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

    def _load_code_content(self):
        """Loads all JS/TS code content for pattern matching."""

        code_extensions = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
        code_files = []

        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

            for file in files:
                if Path(file).suffix in code_extensions:
                    file_path = Path(root) / file
                    try:
                        with open(file_path, encoding="utf-8", errors="ignore") as f:
                            code_files.append(f.read())
                    except Exception:
                        # Ignore error and continue to process
                        continue

        self.all_code_content = "\n".join(code_files)

    def _extract_tech_stack(self) -> dict:
        """
        Extracts technology stack from package.json and project structure.

        Returns:
            dict: Containing frontend, backend, database, testing and tools.
        """

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

        if framework:
            if framework in ["React", "Vue", "Angular", "Svelte", "Next.js"]:
                stack.append(framework)
        else:
            # Fallback detection from deps
            if "react" in all_deps:
                version = all_deps["react"].replace("^", "").replace("~", "")
                stack.append(f"React {version.split('.')[0]}")
            elif "vue" in all_deps:
                stack.append("Vue")
            elif "@angular/core" in all_deps:
                stack.append("Angular")
            elif "svelte" in all_deps:
                stack.append("Svelte")

        # UI Libraries
        if "@mui/material" in all_deps or "@material-ui/core" in all_deps:
            stack.append("Material-UI")
        if "antd" in all_deps:
            stack.append("Ant Design")
        if "tailwindcss" in all_deps:
            stack.append("Tailwind CSS")
        if "bootstrap" in all_deps or "react-bootstrap" in all_deps:
            stack.append("Bootstrap")
        if "@chakra-ui/react" in all_deps:
            stack.append("Chakra UI")

        # State Management
        if "redux" in all_deps or "@reduxjs/toolkit" in all_deps:
            stack.append("Redux")
        if "mobx" in all_deps:
            stack.append("MobX")
        if "zustand" in all_deps:
            stack.append("Zustand")
        if "recoil" in all_deps:
            stack.append("Recoil")

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

        # Add Node.js runtime if backend framework detected
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

        # ORMs/Query Builders
        if "@prisma/client" in all_deps or "prisma" in all_deps:
            stack.append("Prisma")
        if "mongoose" in all_deps:
            stack.append("MongoDB (Mongoose)")
        if "typeorm" in all_deps:
            stack.append("TypeORM")
        if "sequelize" in all_deps:
            stack.append("Sequelize")
        if "knex" in all_deps:
            stack.append("Knex.js")

        # Database drivers
        if "pg" in all_deps:
            stack.append("PostgreSQL")
        if "mysql" in all_deps or "mysql2" in all_deps:
            stack.append("MySQL")
        if "mongodb" in all_deps:
            stack.append("MongoDB")
        if "redis" in all_deps:
            stack.append("Redis")

        return stack

    def _detect_testing_stack(self, all_deps: dict) -> list[str]:
        """Detect testing framework and tools."""

        stack = []

        if "jest" in all_deps:
            stack.append("Jest")
        if "mocha" in all_deps:
            stack.append("Mocha")
        if "vitest" in all_deps:
            stack.append("Vitest")
        if "cypress" in all_deps:
            stack.append("Cypress")
        if "@playwright/test" in all_deps or "playwright" in all_deps:
            stack.append("Playwright")
        if "@testing-library/react" in all_deps:
            stack.append("React Testing Library")

        return stack

    def _detect_tooling(self, all_deps: dict) -> list[str]:
        """Detect build and development tools."""

        tools = []

        if "vite" in all_deps:
            tools.append("Vite")
        if "webpack" in all_deps:
            tools.append("Webpack")
        if "rollup" in all_deps:
            tools.append("Rollup")
        if "parcel" in all_deps:
            tools.append("Parcel")
        if "eslint" in all_deps:
            tools.append("ESLint")
        if "prettier" in all_deps:
            tools.append("Prettier")
        if "typescript" in all_deps:
            tools.append("TypeScript Compiler")

        return tools

    def _detect_features(self) -> list[str]:
        """
        Detect implemented features by scanning code patterns.

        Returns:
            List of feature names that were detected
        """

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
        """Detect third party service integrations."""

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
        """
        Generate comprehensive skills list for resume.

        Combines tech stack, features, and integrations into a single
        list of demonstrable skills.
        """

        skills = set()

        for _category, items in tech_stack.items():
            skills.update(items)

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
