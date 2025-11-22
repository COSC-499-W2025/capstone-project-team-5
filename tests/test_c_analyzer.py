"""Tests for C/C++ file analyzer."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from capstone_project_team_5.c_analyzer import (
    CFileAnalyzer,
    CFileStats,
    CProjectSummary,
    analyze_c_files,
    analyze_c_project,
)


@pytest.fixture
def temp_c_file(tmp_path: Path) -> Path:
    """Create a temporary C file with sample code."""
    c_file = tmp_path / "test.c"
    content = dedent(
        """
        #include <stdio.h>
        #include <stdlib.h>
        
        /* This is a block comment
         * spanning multiple lines
         */
        
        struct Point {
            int x;
            int y;
        };
        
        // Function to calculate sum
        int add(int a, int b) {
            return a + b;
        }
        
        int main(int argc, char *argv[]) {
            int *ptr = malloc(sizeof(int));
            if (ptr == NULL) {
                return 1;
            }
            
            for (int i = 0; i < 10; i++) {
                *ptr = i;
            }
            
            free(ptr);
            return 0;
        }
        """
    )
    c_file.write_text(content)
    return c_file


@pytest.fixture
def temp_cpp_file(tmp_path: Path) -> Path:
    """Create a temporary C++ file with sample code."""
    cpp_file = tmp_path / "test.cpp"
    content = dedent(
        """
        #include <iostream>
        #include <vector>
        #include <memory>
        
        class MyClass {
        private:
            int value;
        public:
            MyClass(int v) : value(v) {}
            int getValue() const { return value; }
        };
        
        void processData(std::vector<int>& data) {
            for (auto& item : data) {
                item *= 2;
            }
        }
        
        int main() {
            auto ptr = std::make_unique<MyClass>(42);
            std::vector<int> numbers = {1, 2, 3, 4, 5};
            
            try {
                processData(numbers);
            } catch (const std::exception& e) {
                std::cerr << "Error: " << e.what() << std::endl;
            }
            
            return 0;
        }
        """
    )
    cpp_file.write_text(content)
    return cpp_file


@pytest.fixture
def temp_header_file(tmp_path: Path) -> Path:
    """Create a temporary header file."""
    header = tmp_path / "mylib.h"
    content = dedent(
        """
        #ifndef MYLIB_H
        #define MYLIB_H
        
        struct Data {
            int id;
            char name[50];
        };
        
        int calculate(int x, int y);
        void process(struct Data* data);
        
        #endif
        """
    )
    header.write_text(content)
    return header


class TestCFileAnalyzer:
    """Test cases for CFileAnalyzer class."""

    def test_is_c_file(self) -> None:
        """Test C/C++ file detection."""
        assert CFileAnalyzer._is_c_file(Path("test.c"))
        assert CFileAnalyzer._is_c_file(Path("test.cpp"))
        assert CFileAnalyzer._is_c_file(Path("test.h"))
        assert CFileAnalyzer._is_c_file(Path("test.hpp"))
        assert not CFileAnalyzer._is_c_file(Path("test.py"))
        assert not CFileAnalyzer._is_c_file(Path("test.txt"))

    def test_is_header_file(self) -> None:
        """Test header file detection."""
        assert CFileAnalyzer._is_header_file(Path("test.h"))
        assert CFileAnalyzer._is_header_file(Path("test.hpp"))
        assert not CFileAnalyzer._is_header_file(Path("test.c"))
        assert not CFileAnalyzer._is_header_file(Path("test.cpp"))

    def test_remove_comments(self) -> None:
        """Test comment removal and counting."""
        content = dedent(
            """
            int x = 5; // line comment
            /* block comment */
            int y = 10;
            /* multi-line
               block comment */
            int z = 15;
            """
        )
        clean, count = CFileAnalyzer._remove_comments(content)
        assert "// line comment" not in clean
        assert "/* block comment */" not in clean
        assert "int x = 5;" in clean
        assert count >= 3  # At least 3 comment lines

    def test_count_functions(self) -> None:
        """Test function counting."""
        content = dedent(
            """
            int add(int a, int b) {
                return a + b;
            }
            
            void print_value(int x) {
                printf("%d", x);
            }
            
            double calculate(double x, double y) {
                return x * y;
            }
            """
        )
        count = CFileAnalyzer._count_functions(content)
        assert count == 3

    def test_count_structs(self) -> None:
        """Test struct counting."""
        content = dedent(
            """
            struct Point {
                int x, y;
            };
            
            struct Color {
                int r, g, b;
            };
            """
        )
        count = CFileAnalyzer._count_structs(content)
        assert count == 2

    def test_count_classes(self) -> None:
        """Test class counting (C++)."""
        content = dedent(
            """
            class Shape {
                virtual void draw() = 0;
            };
            
            class Circle : public Shape {
                void draw() override {}
            };
            """
        )
        count = CFileAnalyzer._count_classes(content)
        assert count == 2

    def test_extract_includes(self) -> None:
        """Test include extraction."""
        content = dedent(
            """
            #include <stdio.h>
            #include <stdlib.h>
            #include "myheader.h"
            """
        )
        includes = CFileAnalyzer._extract_includes(content)
        assert "stdio.h" in includes
        assert "stdlib.h" in includes
        assert "myheader.h" in includes
        assert len(includes) == 3

    def test_has_main_function(self) -> None:
        """Test main function detection."""
        content_with_main = "int main(int argc, char *argv[]) { return 0; }"
        content_without_main = "int add(int a, int b) { return a + b; }"

        assert CFileAnalyzer._has_main_function(content_with_main)
        assert not CFileAnalyzer._has_main_function(content_without_main)

    def test_calculate_complexity(self) -> None:
        """Test complexity score calculation."""
        simple_content = "int x = 5;"
        complex_content = dedent(
            """
            for (int i = 0; i < 10; i++) {
                if (i % 2 == 0) {
                    while (x > 0) {
                        x--;
                    }
                }
            }
            """
        )

        simple_score = CFileAnalyzer._calculate_complexity(simple_content)
        complex_score = CFileAnalyzer._calculate_complexity(complex_content)

        assert simple_score < complex_score
        assert complex_score > 0

    def test_detect_pointers(self) -> None:
        """Test pointer detection."""
        with_pointers = "int *ptr = malloc(sizeof(int)); ptr->value = 5;"
        without_pointers = "int x = 5; int y = 10;"

        assert CFileAnalyzer._detect_pointers(with_pointers)
        assert not CFileAnalyzer._detect_pointers(without_pointers)

    def test_detect_memory_management(self) -> None:
        """Test memory management detection."""
        with_malloc = "int *ptr = malloc(sizeof(int)); free(ptr);"
        with_new = "int *ptr = new int(5); delete ptr;"
        without_mm = "int x = 5;"

        assert CFileAnalyzer._detect_memory_management(with_malloc)
        assert CFileAnalyzer._detect_memory_management(with_new)
        assert not CFileAnalyzer._detect_memory_management(without_mm)

    def test_detect_concurrency(self) -> None:
        """Test concurrency detection."""
        with_threads = "pthread_create(&thread, NULL, func, NULL);"
        with_cpp_threads = "std::thread t(func);"
        without_threads = "int x = 5;"

        assert CFileAnalyzer._detect_concurrency(with_threads)
        assert CFileAnalyzer._detect_concurrency(with_cpp_threads)
        assert not CFileAnalyzer._detect_concurrency(without_threads)

    def test_detect_error_handling(self) -> None:
        """Test error handling detection."""
        with_try_catch = "try { func(); } catch (const std::exception& e) {}"
        with_errno = 'if (errno != 0) { perror("Error"); }'
        without_eh = "int x = 5;"

        assert CFileAnalyzer._detect_error_handling(with_try_catch)
        assert CFileAnalyzer._detect_error_handling(with_errno)
        assert not CFileAnalyzer._detect_error_handling(without_eh)

    def test_analyze_file_c(self, temp_c_file: Path) -> None:
        """Test analyzing a C file."""
        stats = CFileAnalyzer.analyze_file(temp_c_file)

        assert stats is not None
        assert isinstance(stats, CFileStats)
        assert not stats.is_header
        assert stats.lines_of_code > 0
        assert stats.function_count >= 2  # add and main
        assert stats.struct_count >= 1  # Point
        assert stats.has_main
        assert stats.uses_memory_management
        assert stats.uses_pointers
        assert "stdio.h" in stats.includes
        assert "stdlib.h" in stats.includes

    def test_analyze_file_cpp(self, temp_cpp_file: Path) -> None:
        """Test analyzing a C++ file."""
        stats = CFileAnalyzer.analyze_file(temp_cpp_file)

        assert stats is not None
        assert isinstance(stats, CFileStats)
        assert not stats.is_header
        assert stats.lines_of_code > 0
        assert stats.function_count >= 1
        assert stats.class_count >= 1  # MyClass
        assert stats.has_main
        assert stats.uses_error_handling
        assert "iostream" in stats.includes
        assert "vector" in stats.includes

    def test_analyze_file_header(self, temp_header_file: Path) -> None:
        """Test analyzing a header file."""
        stats = CFileAnalyzer.analyze_file(temp_header_file)

        assert stats is not None
        assert stats.is_header
        assert stats.struct_count >= 1
        # Function declarations in headers are not counted by our analyzer
        # (only definitions with { })
        assert not stats.has_main

    def test_analyze_file_invalid(self, tmp_path: Path) -> None:
        """Test that analyzer processes any file since caller pre-filters.

        Note: The analyzer now assumes the caller has already validated
        the file is C/C++, so it will attempt to analyze any file passed to it.
        """
        py_file = tmp_path / "test.py"
        py_file.write_text("print('hello')")

        # Analyzer will process it since we removed pre-validation
        # The caller (file walker) is responsible for filtering
        stats = CFileAnalyzer.analyze_file(py_file)
        assert stats is not None  # It processes the file
        assert stats.function_count == 0  # But won't find C functions

    def test_analyze_project(
        self, tmp_path: Path, temp_c_file: Path, temp_header_file: Path
    ) -> None:
        """Test analyzing entire project."""
        # Create a project structure
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        # Copy test files into project
        (src_dir / "main.c").write_text(temp_c_file.read_text())
        (src_dir / "lib.h").write_text(temp_header_file.read_text())

        # Analyze project
        summary = CFileAnalyzer.analyze_project(tmp_path)

        assert isinstance(summary, CProjectSummary)
        # Test finds files in tmp_path and src_dir, so at least 2 files
        assert summary.total_files >= 2
        assert summary.header_files >= 1
        assert summary.source_files >= 1
        assert summary.total_lines_of_code > 0
        assert summary.total_functions > 0
        assert summary.has_main

    def test_generate_summary_text(self, tmp_path: Path, temp_c_file: Path) -> None:
        """Test generating summary text."""
        (tmp_path / "test.c").write_text(temp_c_file.read_text())

        summary = CFileAnalyzer.analyze_project(tmp_path)
        text = CFileAnalyzer.generate_summary_text(summary)

        assert "C/C++ Project Analysis" in text
        assert "Files:" in text
        assert "Lines of Code:" in text
        assert isinstance(text, str)
        assert len(text) > 0

    def test_generate_summary_text_empty(self, tmp_path: Path) -> None:
        """Test generating summary text for empty project."""
        summary = CFileAnalyzer.analyze_project(tmp_path)
        text = CFileAnalyzer.generate_summary_text(summary)

        assert "No C/C++ files found" in text


class TestPublicFunctions:
    """Test public API functions."""

    def test_analyze_c_project(self, tmp_path: Path, temp_c_file: Path) -> None:
        """Test analyze_c_project function."""
        (tmp_path / "test.c").write_text(temp_c_file.read_text())

        summary = analyze_c_project(tmp_path)

        assert isinstance(summary, CProjectSummary)
        assert summary.total_files > 0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_nonexistent_directory(self) -> None:
        """Test analyzing nonexistent directory."""
        summary = analyze_c_project(Path("/nonexistent/path"))

        assert summary.total_files == 0
        assert summary.total_lines_of_code == 0

    def test_empty_file(self, tmp_path: Path) -> None:
        """Test analyzing empty file."""
        empty_file = tmp_path / "empty.c"
        empty_file.write_text("")

        stats = CFileAnalyzer.analyze_file(empty_file)

        assert stats is not None
        assert stats.lines_of_code == 0
        assert stats.function_count == 0

    def test_file_with_only_comments(self, tmp_path: Path) -> None:
        """Test analyzing file with only comments."""
        comment_file = tmp_path / "comments.c"
        comment_file.write_text(
            dedent(
                """
                /* This is a comment */
                // Another comment
                /* Multi-line
                   comment */
                """
            )
        )

        stats = CFileAnalyzer.analyze_file(comment_file)

        assert stats is not None
        assert stats.lines_of_code == 0
        assert stats.comment_lines > 0

    def test_complex_project_structure(self, tmp_path: Path) -> None:
        """Test analyzing complex project structure."""
        # Create nested directory structure
        (tmp_path / "src").mkdir()
        (tmp_path / "include").mkdir()
        (tmp_path / "tests").mkdir()

        # Create files in different directories
        (tmp_path / "src" / "main.c").write_text("int main() { return 0; }")
        (tmp_path / "src" / "utils.c").write_text("int add(int a, int b) { return a + b; }")
        (tmp_path / "include" / "utils.h").write_text("int add(int a, int b);")
        (tmp_path / "tests" / "test.c").write_text("int test() { return 0; }")

        summary = analyze_c_project(tmp_path)

        assert summary.total_files == 4
        assert summary.has_main
        assert summary.total_functions > 0


class TestPreFilteredFiles:
    """Test analyzing pre-filtered file lists."""

    def test_analyze_c_files_with_list(self, tmp_path: Path) -> None:
        """Test analyzing a pre-filtered list of C files."""
        # Create files
        file1 = tmp_path / "file1.c"
        file2 = tmp_path / "file2.c"
        file1.write_text("int add(int a, int b) { return a + b; }")
        file2.write_text("int multiply(int a, int b) { return a * b; }")

        # Analyze using file list (as if filtered by file walker)
        files = [file1, file2]
        summary = analyze_c_files(files, tmp_path)

        assert summary.total_files == 2
        assert summary.total_functions == 2
        assert summary.source_files == 2
        assert summary.header_files == 0

    def test_analyze_c_files_with_headers(self, tmp_path: Path) -> None:
        """Test analyzing mixed source and header files."""
        source = tmp_path / "code.c"
        header = tmp_path / "code.h"
        source.write_text("int func() { return 42; }")
        header.write_text("int func();")

        files = [source, header]
        summary = analyze_c_files(files, tmp_path)

        assert summary.total_files == 2
        assert summary.source_files == 1
        assert summary.header_files == 1

    def test_analyze_c_files_empty_list(self, tmp_path: Path) -> None:
        """Test analyzing empty file list."""
        summary = analyze_c_files([], tmp_path)

        assert summary.total_files == 0
        assert summary.total_lines_of_code == 0

    def test_analyze_c_files_with_unreadable(self, tmp_path: Path) -> None:
        """Test that unreadable files are skipped gracefully."""
        good_file = tmp_path / "good.c"
        good_file.write_text("int func() { return 1; }")

        # Create a path to non-existent file
        bad_file = tmp_path / "nonexistent.c"

        files = [good_file, bad_file]
        summary = analyze_c_files(files, tmp_path)

        # Should only count the readable file
        assert summary.total_files == 1
        assert summary.total_functions >= 1
