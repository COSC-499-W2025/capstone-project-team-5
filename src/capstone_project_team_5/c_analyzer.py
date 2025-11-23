"""
C/C++ file analyzer for extracting code statistics and generating summaries.

This module provides local (non-LLM) analysis of C/C++ source code to extract
meaningful statistics that can be used for resume bullet generation or project
summaries without requiring AI/LLM services.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from capstone_project_team_5.constants.c_analysis_constants import (
    ALL_C_EXTENSIONS,
    COMMON_C_LIBRARIES,
    COMMON_CPP_LIBRARIES,
    COMPLEXITY_KEYWORDS,
    CONCURRENCY_PATTERNS,
    ERROR_HANDLING_PATTERNS,
    HEADER_EXTENSIONS,
    MEMORY_FUNCTIONS,
)


@dataclass
class CFileStats:
    """Statistics extracted from a C/C++ file.

    Attributes:
        file_path: Relative path to the file.
        is_header: Whether this is a header file.
        lines_of_code: Total non-empty, non-comment lines.
        total_lines: Total lines including comments and empty lines.
        comment_lines: Number of comment lines.
        function_count: Number of function definitions.
        struct_count: Number of struct definitions.
        class_count: Number of class definitions (C++ only).
        include_count: Number of include directives.
        includes: List of included headers.
        has_main: Whether the file contains a main function.
        complexity_score: Rough estimate of code complexity.
        uses_pointers: Whether pointer operations are present.
        uses_memory_management: Whether manual memory management is used.
        uses_concurrency: Whether concurrency primitives are used.
        uses_error_handling: Whether error handling is present.
        library_usage: Set of detected library names.
    """

    file_path: str
    is_header: bool = False
    lines_of_code: int = 0
    total_lines: int = 0
    comment_lines: int = 0
    function_count: int = 0
    struct_count: int = 0
    class_count: int = 0
    include_count: int = 0
    includes: list[str] = field(default_factory=list)
    has_main: bool = False
    complexity_score: int = 0
    uses_pointers: bool = False
    uses_memory_management: bool = False
    uses_concurrency: bool = False
    uses_error_handling: bool = False
    library_usage: set[str] = field(default_factory=set)


@dataclass
class CProjectSummary:
    """Summary statistics for a C/C++ project.

    Attributes:
        total_files: Total number of C/C++ files analyzed.
        header_files: Number of header files.
        source_files: Number of source files.
        total_lines_of_code: Total LOC across all files.
        total_functions: Total function count.
        total_structs: Total struct count.
        total_classes: Total class count.
        has_main: Whether project has main function.
        libraries_used: Set of detected libraries.
        common_includes: Most common included headers.
        avg_complexity: Average complexity score.
        uses_pointers: Whether project uses pointers.
        uses_memory_management: Whether project uses manual memory management.
        uses_concurrency: Whether project uses concurrency.
        uses_error_handling: Whether project has error handling.
        file_stats: List of individual file statistics.
    """

    total_files: int = 0
    header_files: int = 0
    source_files: int = 0
    total_lines_of_code: int = 0
    total_functions: int = 0
    total_structs: int = 0
    total_classes: int = 0
    has_main: bool = False
    libraries_used: set[str] = field(default_factory=set)
    common_includes: list[tuple[str, int]] = field(default_factory=list)
    avg_complexity: float = 0.0
    uses_pointers: bool = False
    uses_memory_management: bool = False
    uses_concurrency: bool = False
    uses_error_handling: bool = False
    file_stats: list[CFileStats] = field(default_factory=list)


class CFileAnalyzer:
    """Analyzer for C/C++ source code files."""

    @staticmethod
    def _is_c_file(file_path: Path) -> bool:
        """Check if a file is a C/C++ source or header file.

        Args:
            file_path: Path to check.

        Returns:
            True if file has C/C++ extension.
        """
        return file_path.suffix.lower() in ALL_C_EXTENSIONS

    @staticmethod
    def _is_header_file(file_path: Path) -> bool:
        """Check if a file is a header file.

        Args:
            file_path: Path to check.

        Returns:
            True if file is a header.
        """
        return file_path.suffix.lower() in HEADER_EXTENSIONS

    @staticmethod
    def _remove_comments(content: str) -> tuple[str, int]:
        """Remove comments from C/C++ code and count comment lines.

        Args:
            content: Source code content.

        Returns:
            Tuple of (code without comments, number of comment lines).
        """
        comment_lines = 0

        # Count block comments
        block_comments = re.findall(r"/\*.*?\*/", content, re.DOTALL)
        for comment in block_comments:
            comment_lines += comment.count("\n") + 1

        # Remove block comments
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)

        # Count line comments
        line_comments = re.findall(r"//.*$", content, re.MULTILINE)
        comment_lines += len(line_comments)

        # Remove line comments
        content = re.sub(r"//.*$", "", content, flags=re.MULTILINE)

        return content, comment_lines

    @staticmethod
    def _count_functions(content: str) -> int:
        """Count function definitions in code.

        Args:
            content: Source code content (without comments).

        Returns:
            Number of function definitions.
        """
        # Pattern matches: return_type function_name(params) {
        # This is a simplified pattern that works for most cases
        pattern = r"\b\w+\s+\w+\s*\([^)]*\)\s*\{"
        matches = re.findall(pattern, content)
        return len(matches)

    @staticmethod
    def _count_structs(content: str) -> int:
        """Count struct definitions in code.

        Args:
            content: Source code content (without comments).

        Returns:
            Number of struct definitions.
        """
        pattern = r"\bstruct\s+\w+\s*\{"
        matches = re.findall(pattern, content)
        return len(matches)

    @staticmethod
    def _count_classes(content: str) -> int:
        """Count class definitions in code (C++ only).

        Args:
            content: Source code content (without comments).

        Returns:
            Number of class definitions.
        """
        pattern = r"\bclass\s+\w+\s*[:{]"
        matches = re.findall(pattern, content)
        return len(matches)

    @staticmethod
    def _extract_includes(content: str) -> list[str]:
        """Extract include directives from code.

        Args:
            content: Source code content.

        Returns:
            List of included headers.
        """
        pattern = r'#include\s+[<"]([^>"]+)[>"]'
        matches = re.findall(pattern, content)
        return matches

    @staticmethod
    def _has_main_function(content: str) -> bool:
        """Check if code contains a main function.

        Args:
            content: Source code content (without comments).

        Returns:
            True if main function is present.
        """
        pattern = r"\bint\s+main\s*\([^)]*\)\s*\{"
        return bool(re.search(pattern, content))

    @staticmethod
    def _calculate_complexity(content: str) -> int:
        """Calculate a rough complexity score based on control flow keywords.

        Args:
            content: Source code content (without comments).

        Returns:
            Complexity score (higher = more complex).
        """
        score = 0
        for keyword in COMPLEXITY_KEYWORDS:
            pattern = rf"\b{keyword}\b"
            score += len(re.findall(pattern, content))
        return score

    @staticmethod
    def _detect_pointers(content: str) -> bool:
        """Detect pointer usage in code.

        Args:
            content: Source code content (without comments).

        Returns:
            True if pointers are used.
        """
        # Look for pointer declaration patterns: type *var or type*var
        pattern = r"\w+\s*\*\s*\w+|->|\*\w+"
        return bool(re.search(pattern, content))

    @staticmethod
    def _detect_memory_management(content: str) -> bool:
        """Detect manual memory management.

        Args:
            content: Source code content (without comments).

        Returns:
            True if memory management functions are used.
        """
        return any(re.search(rf"\b{func}\b", content) for func in MEMORY_FUNCTIONS)

    @staticmethod
    def _detect_concurrency(content: str) -> bool:
        """Detect concurrency primitives.

        Args:
            content: Source code content (without comments).

        Returns:
            True if concurrency patterns are detected.
        """
        return any(pattern in content for pattern in CONCURRENCY_PATTERNS)

    @staticmethod
    def _detect_error_handling(content: str) -> bool:
        """Detect error handling patterns.

        Args:
            content: Source code content (without comments).

        Returns:
            True if error handling is present.
        """
        return any(re.search(rf"\b{pattern}\b", content) for pattern in ERROR_HANDLING_PATTERNS)

    @staticmethod
    def _detect_libraries(includes: list[str]) -> set[str]:
        """Detect common libraries from include statements.

        Args:
            includes: List of included headers.

        Returns:
            Set of detected library names.
        """
        libraries = set()

        for include in includes:
            include_lower = include.lower()

            # Check C libraries
            for lib_pattern, lib_name in COMMON_C_LIBRARIES.items():
                if lib_pattern in include_lower:
                    libraries.add(lib_name)

            # Check C++ libraries
            for lib_pattern, lib_name in COMMON_CPP_LIBRARIES.items():
                if lib_pattern in include_lower:
                    libraries.add(lib_name)

        return libraries

    @staticmethod
    def analyze_file(file_path: Path, root: Path | None = None) -> CFileStats | None:
        """Analyze a single C/C++ file.

        Assumes the caller has already validated that this is a C/C++ file.

        Args:
            file_path: Path to the C/C++ file (pre-validated).
            root: Optional root directory for relative path calculation.

        Returns:
            CFileStats object with analysis results, or None if file cannot be read.
        """
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            return None

        # Calculate relative path
        if root:
            try:
                rel_path = str(file_path.relative_to(root))
            except ValueError:
                rel_path = file_path.name
        else:
            rel_path = file_path.name

        # Remove comments and count them
        clean_content, comment_lines = CFileAnalyzer._remove_comments(content)

        # Extract includes
        includes = CFileAnalyzer._extract_includes(content)

        # Count lines of code (non-empty, non-comment lines)
        lines = [line for line in clean_content.split("\n") if line.strip()]
        lines_of_code = len(lines)
        total_lines = len(content.split("\n"))

        # Analyze code
        stats = CFileStats(
            file_path=rel_path,
            is_header=CFileAnalyzer._is_header_file(file_path),
            lines_of_code=lines_of_code,
            total_lines=total_lines,
            comment_lines=comment_lines,
            function_count=CFileAnalyzer._count_functions(clean_content),
            struct_count=CFileAnalyzer._count_structs(clean_content),
            class_count=CFileAnalyzer._count_classes(clean_content),
            include_count=len(includes),
            includes=includes,
            has_main=CFileAnalyzer._has_main_function(clean_content),
            complexity_score=CFileAnalyzer._calculate_complexity(clean_content),
            uses_pointers=CFileAnalyzer._detect_pointers(clean_content),
            uses_memory_management=CFileAnalyzer._detect_memory_management(clean_content),
            uses_concurrency=CFileAnalyzer._detect_concurrency(clean_content),
            uses_error_handling=CFileAnalyzer._detect_error_handling(clean_content),
            library_usage=CFileAnalyzer._detect_libraries(includes),
        )

        return stats

    @staticmethod
    def analyze_project(project_root: Path | str) -> CProjectSummary:
        """Analyze all C/C++ files in a project directory.

        Args:
            project_root: Path to the project root directory.

        Returns:
            CProjectSummary with aggregated statistics.
        """
        root = Path(project_root)
        summary = CProjectSummary()

        if not root.exists() or not root.is_dir():
            return summary

        # Find all C/C++ files (by extension)
        c_files = [f for f in root.rglob("*") if f.is_file() and f.suffix in ALL_C_EXTENSIONS]

        # Analyze each file
        all_includes: Counter[str] = Counter()

        for file_path in c_files:
            stats = CFileAnalyzer.analyze_file(file_path, root)
            if stats is None:
                continue

            summary.file_stats.append(stats)
            summary.total_files += 1

            if stats.is_header:
                summary.header_files += 1
            else:
                summary.source_files += 1

            summary.total_lines_of_code += stats.lines_of_code
            summary.total_functions += stats.function_count
            summary.total_structs += stats.struct_count
            summary.total_classes += stats.class_count

            if stats.has_main:
                summary.has_main = True

            summary.uses_pointers = summary.uses_pointers or stats.uses_pointers
            summary.uses_memory_management = (
                summary.uses_memory_management or stats.uses_memory_management
            )
            summary.uses_concurrency = summary.uses_concurrency or stats.uses_concurrency
            summary.uses_error_handling = summary.uses_error_handling or stats.uses_error_handling

            summary.libraries_used.update(stats.library_usage)

            # Track include usage
            for include in stats.includes:
                all_includes[include] += 1

        # Calculate averages
        if summary.total_files > 0:
            total_complexity = sum(stat.complexity_score for stat in summary.file_stats)
            summary.avg_complexity = total_complexity / summary.total_files

        # Get most common includes
        summary.common_includes = all_includes.most_common(10)

        return summary

    @staticmethod
    def generate_summary_text(summary: CProjectSummary) -> str:
        """Generate a human-readable text summary of the analysis.

        Args:
            summary: CProjectSummary to format.

        Returns:
            Formatted text summary.
        """
        if summary.total_files == 0:
            return "No C/C++ files found in project."

        lines = []
        lines.append("=== C/C++ Project Analysis ===\n")

        # File counts
        lines.append(f"📁 Total Files: {summary.total_files}")
        lines.append(f"   Headers: {summary.header_files}, Source: {summary.source_files}")

        # Code metrics
        lines.append("\n📊 Code Metrics:")
        lines.append(f"   Lines of Code: {summary.total_lines_of_code:,}")
        lines.append(f"   Functions: {summary.total_functions}")
        lines.append(f"   Structs: {summary.total_structs}")
        if summary.total_classes > 0:
            lines.append(f"   Classes: {summary.total_classes}")
        lines.append(f"   Avg Complexity: {summary.avg_complexity:.1f}")

        # Technical features
        features = []
        if summary.uses_pointers:
            features.append("Pointers")
        if summary.uses_memory_management:
            features.append("Manual Memory Management")
        if summary.uses_concurrency:
            features.append("Concurrency")
        if summary.uses_error_handling:
            features.append("Error Handling")

        if features:
            lines.append(f"\n⚙️  Technical Features: {', '.join(features)}")

        # Libraries
        if summary.libraries_used:
            lines.append("\n📚 Libraries Used:")
            for lib in sorted(summary.libraries_used):
                lines.append(f"   • {lib}")

        # Common includes
        if summary.common_includes:
            lines.append("\n#️⃣  Most Common Includes:")
            for include, count in summary.common_includes[:5]:
                lines.append(f"   • {include} ({count} files)")

        return "\n".join(lines)


def analyze_c_project(project_root: Path | str) -> CProjectSummary:
    """Analyze a C/C++ project and return summary statistics.

    Args:
        project_root: Path to the project root directory.

    Returns:
        CProjectSummary with analysis results.
    """
    return CFileAnalyzer.analyze_project(project_root)


def analyze_c_files(files: list[Path], root: Path | None = None) -> CProjectSummary:
    """Analyze a pre-filtered list of C/C++ files.

    Use this function when you've already filtered files through
    your file walker or other logic. Assumes all files are valid C/C++ files.

    Args:
        files: List of C/C++ file paths (pre-validated).
        root: Optional root directory for relative path calculation.

    Returns:
        CProjectSummary with aggregated statistics.
    """
    summary = CProjectSummary()
    all_includes: Counter[str] = Counter()

    for file_path in files:
        stats = CFileAnalyzer.analyze_file(file_path, root)
        if stats is None:
            continue

        summary.file_stats.append(stats)
        summary.total_files += 1

        if stats.is_header:
            summary.header_files += 1
        else:
            summary.source_files += 1

        summary.total_lines_of_code += stats.lines_of_code
        summary.total_functions += stats.function_count
        summary.total_structs += stats.struct_count
        summary.total_classes += stats.class_count

        if stats.has_main:
            summary.has_main = True

        summary.uses_pointers = summary.uses_pointers or stats.uses_pointers
        summary.uses_memory_management = (
            summary.uses_memory_management or stats.uses_memory_management
        )
        summary.uses_concurrency = summary.uses_concurrency or stats.uses_concurrency
        summary.uses_error_handling = summary.uses_error_handling or stats.uses_error_handling

        summary.libraries_used.update(stats.library_usage)

        # Track include usage
        for include in stats.includes:
            all_includes[include] += 1

    # Calculate averages
    if summary.total_files > 0:
        total_complexity = sum(stat.complexity_score for stat in summary.file_stats)
        summary.avg_complexity = total_complexity / summary.total_files

    # Get most common includes
    summary.common_includes = all_includes.most_common(10)

    return summary
