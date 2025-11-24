import ast
import json
import os
import re
from collections import defaultdict
from pathlib import Path

from capstone_project_team_5.constants.skill_detection_constants import SKIP_DIRS


class PythonAnalyzer:
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.all_code_content = ""
        self.imports = set()
        self.ast_trees = []

    def analyze(self) -> dict:
        """Run full analysis."""
        self._load_code_content()
        self._extract_imports()
        self._parse_ast()

        oop = self._analyze_oop()
        tech_stack = self._detect_tech_stack()
        features = self._detect_features()
        integrations = self._detect_integrations()
        skills = self._generate_skills_list(
            tech_stack=tech_stack, features=features, integrations=integrations, oop=oop
        )

        return {
            "oop": oop,
            "tech_stack": tech_stack,
            "features": features,
            "integrations": integrations,
            "skills_demonstrated": skills,
        }

    # ---------------------------------------------------------
    # LOAD CODE
    # ---------------------------------------------------------

    def _load_code_content(self):
        code_files = []

        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

            for file in files:
                if file.endswith(".py"):
                    file_path = Path(root) / file
                    try:
                        code = file_path.read_text(encoding="utf-8", errors="ignore")
                        code_files.append(code)
                    except Exception:
                        continue

        self.all_code_content = "\n".join(code_files)

    # ---------------------------------------------------------
    # IMPORT PARSING
    # ---------------------------------------------------------

    def _extract_imports(self):
        """Pull import statements using regex."""
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

    def _parse_ast(self):
        """Parse AST for OOP analysis."""
        trees = []

        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

            for file in files:
                if file.endswith(".py"):
                    p = Path(root) / file
                    try:
                        trees.append(ast.parse(p.read_text(encoding="utf-8", errors="ignore")))
                    except Exception:
                        continue

        self.ast_trees = trees

    # ---------------------------------------------------------
    # OOP ANALYSIS
    # ---------------------------------------------------------

    def _analyze_oop(self) -> dict:
        classes = {}
        inheritance = False
        encapsulation = False
        polymorphism = False
        method_map = defaultdict(list)

        for tree in self.ast_trees:
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue

                cname = node.name

                # inheritance detection
                bases = [base.id for base in node.bases if isinstance(base, ast.Name)]
                if bases:
                    inheritance = True

                # -------------------------------------------------
                # FIXED ENCAPSULATION DETECTION (instance/class private attrs only)
                # -------------------------------------------------
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

                # collect methods
                for sub in node.body:
                    if isinstance(sub, ast.FunctionDef):
                        method_map[cname].append(sub.name)

                classes[cname] = bases

        # polymorphism: same method names in different classes
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
        }

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

        if "http" in integrations:
            skills.add("HTTP API Integration")
        if "aws" in integrations:
            skills.add("AWS Integration")
        if "cache" in integrations:
            skills.add("Caching & Messaging")
        if "data" in integrations:
            skills.add("Data Processing")

        return sorted(list(skills))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyze a Python codebase.")
    parser.add_argument("path", help="Path to the Python project directory")
    args = parser.parse_args()

    analyzer = PythonAnalyzer(args.path)
    result = analyzer.analyze()

    print(json.dumps(result, indent=2))
