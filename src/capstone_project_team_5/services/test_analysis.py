from __future__ import annotations

import ast
import os
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from capstone_project_team_5.constants.contribution_metrics_constants import (
    SKIP_DIRS as CONTRIBUTION_SKIP_DIRS,
)
from capstone_project_team_5.constants.contribution_metrics_constants import (
    TEST_FILE_PATTERNS,
)
from capstone_project_team_5.constants.skill_detection_constants import (
    SKIP_DIRS as SKILL_SKIP_DIRS,
)


@dataclass
class TestFileSummary:
    """Per-test-file metrics used for aggregation."""

    path: Path
    language: str
    test_count: int
    category: str  # "unit" or "integration"
    frameworks: set[str] = field(default_factory=set)


@dataclass
class TestAnalysisResult:
    """Aggregated test metrics for a project."""

    test_file_count: int = 0
    test_case_count: int = 0
    unit_test_count: int = 0
    integration_test_count: int = 0
    frameworks: set[str] = field(default_factory=set)
    tests_by_language: dict[str, int] = field(default_factory=dict)
    tests_by_framework: dict[str, int] = field(default_factory=dict)
    files: list[TestFileSummary] = field(default_factory=list)

    def register_file(self, summary: TestFileSummary) -> None:
        """Accumulate a TestFileSummary into the aggregate result."""

        self.files.append(summary)
        self.test_file_count += 1
        self.test_case_count += summary.test_count

        if summary.category == "integration":
            self.integration_test_count += summary.test_count
        else:
            self.unit_test_count += summary.test_count

        if summary.language:
            self.tests_by_language[summary.language] = (
                self.tests_by_language.get(summary.language, 0) + summary.test_count
            )

        if summary.frameworks:
            for framework in summary.frameworks:
                self.frameworks.add(framework)
                self.tests_by_framework[framework] = (
                    self.tests_by_framework.get(framework, 0) + summary.test_count
                )


# Normalized skip directories used when walking the tree
_SKIP_DIRS = {name.lower() for name in (SKILL_SKIP_DIRS | CONTRIBUTION_SKIP_DIRS)}

# Fixture/helper file hints to avoid double-counting supporting files
_FIXTURE_FILE_HINTS = {
    "conftest.py",
    "fixture",
    "fixtures",
    "helper",
    "helpers",
    "factory",
    "factories",
    "snapshot",
    "snapshots",
    "testdata",
    "data_builder",
}

# Regexes derived from existing contribution constants plus extra heuristics
_TEST_PATH_REGEXES = [re.compile(pattern, re.IGNORECASE) for pattern in TEST_FILE_PATTERNS] + [
    re.compile(r"\bSpec\.", re.IGNORECASE),
    re.compile(r"/__specs__/", re.IGNORECASE),
    re.compile(r"/integration[/\\]", re.IGNORECASE),
    re.compile(r"/e2e[/\\]", re.IGNORECASE),
]

_INTEGRATION_HINTS = {"integration", "e2e", "acceptance", "functional", "system"}
_UNIT_HINTS = {"unit", "unittest", "component"}

_FRAMEWORK_KEYWORDS: dict[str, str] = {
    "pytest": "PyTest",
    "unittest": "unittest",
    "nose": "Nose",
    "jest": "Jest",
    "vitest": "Vitest",
    "mocha": "Mocha",
    "cypress": "Cypress",
    "playwright": "Playwright",
    "ava": "AVA",
    "rspec": "RSpec",
    "minitest": "Minitest",
    "junit": "JUnit",
    "testng": "TestNG",
    "gtest": "GoogleTest",
    "googletest": "GoogleTest",
    "catch2": "Catch2",
    "xctest": "XCTest",
    "espresso": "Espresso",
    "selenium": "Selenium",
    "karma": "Karma",
    "enzyme": "Enzyme",
    "testing-library": "Testing Library",
    "expect": "Expect",
}


def _compile_framework_pattern(keyword: str) -> re.Pattern[str]:
    """Build a regex that matches the keyword with sensible boundaries."""

    start = keyword[0].isalnum()
    end = keyword[-1].isalnum()
    escaped = re.escape(keyword)

    pattern = escaped
    if start:
        pattern = r"\b" + pattern
    if end:
        pattern = pattern + r"\b"

    return re.compile(pattern, re.IGNORECASE)


_FRAMEWORK_REGEXES: dict[str, re.Pattern[str]] = {
    keyword: _compile_framework_pattern(keyword) for keyword in _FRAMEWORK_KEYWORDS
}

_ASSERT_PATTERNS = [
    re.compile(r"\bassert\b"),
    re.compile(r"\bAssert\."),
    re.compile(r"\bEXPECT_[A-Z]+\s*\("),
    re.compile(r"\bASSERT_[A-Z]+\s*\("),
    re.compile(r"\brequire\.\w+\s*\("),
    re.compile(r"\bshould\b"),
]

_JAVA_TEST_ANNOTATION = re.compile(
    r"@\s*(?:org\.junit\.)?(?:Test|ParameterizedTest|RepeatedTest|TestFactory|TestTemplate)",
    re.IGNORECASE,
)

_JS_TEST_CALL = re.compile(r"\b(it|test)\s*\(", re.IGNORECASE)

_GTEST_MACROS = re.compile(r"\bTEST(?:_[FP])?\s*\(|\bTEST_[A-Z]+\s*\(", re.IGNORECASE)

_GO_TEST_FUNC = re.compile(r"\bfunc\s+(?:\([^)]+\)\s*)?Test\w+\s*\(", re.IGNORECASE)


def analyze_tests(project_root: Path | str) -> TestAnalysisResult:
    """Analyze tests across any language within the provided project root."""

    root = Path(project_root)
    result = TestAnalysisResult()

    if not root.exists() or not root.is_dir():
        return result

    for file_path in _iter_candidate_test_files(root):
        if _is_fixture_like(file_path):
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue

        language = _detect_language(file_path)
        test_count = _count_tests(language, content)

        if test_count == 0:
            continue

        category = _infer_test_category(file_path)
        frameworks = _detect_frameworks(content)

        summary = TestFileSummary(
            path=file_path,
            language=language,
            test_count=test_count,
            category=category,
            frameworks=frameworks,
        )
        result.register_file(summary)

    return result


def _iter_candidate_test_files(root: Path) -> Iterator[Path]:
    """Yield files that are likely to contain tests based on path heuristics."""

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name.lower() not in _SKIP_DIRS]

        for filename in filenames:
            file_path = Path(dirpath) / filename
            if _looks_like_test_path(file_path):
                yield file_path


def _looks_like_test_path(path: Path) -> bool:
    """Determine if the path likely represents a test file."""

    normalized = str(path).replace("\\", "/")
    filename = path.name.lower()

    if filename.endswith((".snap", ".snapshot")):
        return False

    if filename in {"package-lock.json", "pnpm-lock.yaml", "yarn.lock"}:
        return False

    for regex in _TEST_PATH_REGEXES:
        if regex.search(normalized):
            return True

    return filename.startswith("test") or filename.endswith("_test.py")


def _is_fixture_like(path: Path) -> bool:
    """Filter out fixture/helper/support files inside test directories."""

    name_lower = path.name.lower()

    if name_lower in _FIXTURE_FILE_HINTS:
        return True

    if any(hint in name_lower for hint in ("fixture", "snapshot")):
        return True

    normalized = str(path).replace("\\", "/").lower()
    return any(
        segment in normalized for segment in ("/fixtures/", "/__snapshots__/", "/snapshots/")
    )


def _detect_language(path: Path) -> str:
    """Best-effort language detection from file extension."""

    suffix = path.suffix.lower()
    language_map = {
        ".py": "Python",
        ".java": "Java",
        ".kt": "Kotlin",
        ".kts": "Kotlin",
        ".js": "JavaScript",
        ".jsx": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".c": "C/C++",
        ".cc": "C/C++",
        ".cxx": "C/C++",
        ".cpp": "C/C++",
        ".hpp": "C/C++",
        ".hh": "C/C++",
        ".hxx": "C/C++",
        ".m": "Objective-C",
        ".mm": "Objective-C++",
        ".swift": "Swift",
        ".go": "Go",
        ".rb": "Ruby",
        ".php": "PHP",
        ".cs": "C#",
        ".rs": "Rust",
        ".mjs": "JavaScript",
        ".cjs": "JavaScript",
    }
    return language_map.get(suffix, "Unknown")


def _infer_test_category(path: Path) -> str:
    """Infer unit vs integration tests based on directory/file naming."""

    normalized = str(path).replace("\\", "/").lower()

    if any(keyword in normalized for keyword in _INTEGRATION_HINTS):
        return "integration"

    if any(keyword in normalized for keyword in _UNIT_HINTS):
        return "unit"

    return "unit"


def _detect_frameworks(content: str) -> set[str]:
    """Return a set of frameworks inferred from the file content."""

    detected: set[str] = set()

    for keyword, pattern in _FRAMEWORK_REGEXES.items():
        if pattern.search(content):
            detected.add(_FRAMEWORK_KEYWORDS[keyword])

    return detected


def _count_tests(language: str, content: str) -> int:
    """Dispatch to language-specific counters with fallbacks."""

    if language == "Python":
        return _count_python_tests(content)
    if language == "Java":
        return _count_java_tests(content)
    if language in {"JavaScript", "TypeScript"}:
        return _count_js_tests(content)
    if language == "C/C++":
        return _count_cpp_tests(content)
    if language == "Go":
        return _count_go_tests(content)

    return _count_asserts(content)


def _count_python_tests(content: str) -> int:
    """Count pytest/unittest test cases via AST analysis."""

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return _count_asserts(content)

    count = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
            "test"
        ):
            count += 1

    return count or _count_asserts(content)


def _count_java_tests(content: str) -> int:
    """Count Java/Kotlin tests by detecting JUnit/TestNG annotations."""

    matches = _JAVA_TEST_ANNOTATION.findall(content)
    return len(matches) or _count_asserts(content)


def _count_js_tests(content: str) -> int:
    """Count JS/TS tests by tallying `it()` / `test()` usage."""

    matches = _JS_TEST_CALL.findall(content)
    return len(matches) or _count_asserts(content)


def _count_cpp_tests(content: str) -> int:
    """Count C/C++ tests via GoogleTest-style macros."""

    matches = _GTEST_MACROS.findall(content)
    return len(matches) or _count_asserts(content)


def _count_go_tests(content: str) -> int:
    """Count Go tests (func TestX)."""

    matches = _GO_TEST_FUNC.findall(content)
    return len(matches) or _count_asserts(content)


def _count_asserts(content: str) -> int:
    """Generic fallback: count assertion-like statements."""

    count = 0
    for pattern in _ASSERT_PATTERNS:
        count += len(pattern.findall(content))
    return count
