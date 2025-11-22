"""Tests for local bullet generation service."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from capstone_project_team_5.services.local_bullets import (
    generate_local_bullets,
    should_use_local_analysis,
)


@pytest.fixture
def temp_c_project(tmp_path: Path) -> Path:
    """Create a temporary C project."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    # Create main.c
    (src_dir / "main.c").write_text(
        dedent(
            """
            #include <stdio.h>
            #include <stdlib.h>
            
            int add(int a, int b) {
                return a + b;
            }
            
            int main(int argc, char *argv[]) {
                int *ptr = malloc(sizeof(int));
                free(ptr);
                return 0;
            }
            """
        )
    )

    # Create utils.h
    (src_dir / "utils.h").write_text(
        dedent(
            """
            #ifndef UTILS_H
            #define UTILS_H
            
            int add(int a, int b);
            
            #endif
            """
        )
    )

    return tmp_path


@pytest.fixture
def temp_python_project(tmp_path: Path) -> Path:
    """Create a temporary Python project."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    # Create main.py
    (src_dir / "main.py").write_text(
        dedent(
            """
            def add(a, b):
                return a + b
            
            if __name__ == '__main__':
                print(add(1, 2))
            """
        )
    )

    # Create test_main.py
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_main.py").write_text(
        dedent(
            """
            import pytest
            
            def test_add():
                assert add(1, 2) == 3
            """
        )
    )

    # Create README.md
    (tmp_path / "README.md").write_text("# Test Project\n\nThis is a test project.")

    # Create requirements.txt
    (tmp_path / "requirements.txt").write_text("pytest\nrequests\n")

    return tmp_path


class TestGenerateLocalBullets:
    """Test cases for generate_local_bullets function."""

    def test_generate_bullets_for_c_project(self, temp_c_project: Path) -> None:
        """Test generating bullets for C project."""
        bullets = generate_local_bullets(temp_c_project)

        assert isinstance(bullets, list)
        assert len(bullets) > 0
        assert all(isinstance(b, str) for b in bullets)
        # Should mention C/C++
        assert any("c" in b.lower() or "code" in b.lower() for b in bullets)

    def test_generate_bullets_for_python_project(self, temp_python_project: Path) -> None:
        """Test generating bullets for Python project."""
        bullets = generate_local_bullets(temp_python_project)

        assert isinstance(bullets, list)
        assert len(bullets) > 0
        assert all(isinstance(b, str) for b in bullets)
        # Should mention Python
        assert any("python" in b.lower() for b in bullets)

    def test_generate_bullets_with_max_bullets_limit(self, temp_c_project: Path) -> None:
        """Test that max_bullets parameter limits output."""
        bullets_3 = generate_local_bullets(temp_c_project, max_bullets=3)
        bullets_6 = generate_local_bullets(temp_c_project, max_bullets=6)

        assert len(bullets_3) <= 3
        assert len(bullets_6) <= 6

    def test_generate_bullets_empty_directory(self, tmp_path: Path) -> None:
        """Test generating bullets for empty directory."""
        bullets = generate_local_bullets(tmp_path)

        # Should return something even for empty projects
        assert isinstance(bullets, list)

    def test_generate_bullets_with_string_path(self, temp_c_project: Path) -> None:
        """Test that function accepts string paths."""
        bullets = generate_local_bullets(str(temp_c_project))

        assert isinstance(bullets, list)
        assert len(bullets) > 0

    def test_bullets_content_quality(self, temp_python_project: Path) -> None:
        """Test that bullets contain meaningful content."""
        bullets = generate_local_bullets(temp_python_project)

        # Check that bullets are not empty and have reasonable length
        assert all(len(b) > 20 for b in bullets), "Bullets should be descriptive"

        # Check that bullets start with capital letters or numbers
        assert all(b[0].isupper() or b[0].isdigit() for b in bullets if b)

    def test_c_project_specific_features(self, temp_c_project: Path) -> None:
        """Test that C projects get specific analysis."""
        bullets = generate_local_bullets(temp_c_project)

        # C projects should mention specific features
        all_text = " ".join(bullets).lower()
        # Should have some technical detail
        assert any(
            term in all_text
            for term in ["function", "memory", "code", "file", "implemented", "developed"]
        )


class TestShouldUseLocalAnalysis:
    """Test cases for should_use_local_analysis function."""

    def test_no_llm_available(self) -> None:
        """Test that local analysis is used when LLM not available."""
        assert should_use_local_analysis("Python", has_llm_consent=True, llm_available=False)

    def test_no_llm_consent(self) -> None:
        """Test that local analysis is used when no consent."""
        assert should_use_local_analysis("Python", has_llm_consent=False, llm_available=True)

    def test_c_language_prefers_local(self) -> None:
        """Test that C/C++ prefers local analysis."""
        assert should_use_local_analysis("C/C++", has_llm_consent=True, llm_available=True)

    def test_other_languages_with_llm(self) -> None:
        """Test that other languages can use LLM when available."""
        result = should_use_local_analysis("Python", has_llm_consent=True, llm_available=True)
        # Should return False for Python when LLM is available
        assert not result

    def test_java_with_llm(self) -> None:
        """Test Java with LLM available."""
        result = should_use_local_analysis("Java", has_llm_consent=True, llm_available=True)
        assert not result

    def test_unknown_language_no_llm(self) -> None:
        """Test unknown language without LLM."""
        assert should_use_local_analysis("Unknown", has_llm_consent=False, llm_available=False)


class TestGenericBullets:
    """Test generic bullet generation for non-C projects."""

    def test_python_project_mentions_tests(self, temp_python_project: Path) -> None:
        """Test that Python project bullets mention testing."""
        bullets = generate_local_bullets(temp_python_project)

        all_text = " ".join(bullets).lower()
        assert "test" in all_text

    def test_python_project_mentions_documentation(self, temp_python_project: Path) -> None:
        """Test that Python project bullets mention documentation."""
        bullets = generate_local_bullets(temp_python_project)

        all_text = " ".join(bullets).lower()
        assert "document" in all_text or "readme" in all_text or "md" in all_text

    def test_bullets_are_unique(self, temp_python_project: Path) -> None:
        """Test that generated bullets are unique."""
        bullets = generate_local_bullets(temp_python_project)

        # No duplicate bullets
        assert len(bullets) == len(set(bullets))


class TestIntegration:
    """Integration tests for local bullet generation."""

    def test_multiple_languages_in_project(self, tmp_path: Path) -> None:
        """Test project with multiple languages."""
        # Create mixed project
        (tmp_path / "main.c").write_text("int main() { return 0; }")
        (tmp_path / "script.py").write_text("print('hello')")

        bullets = generate_local_bullets(tmp_path)

        assert isinstance(bullets, list)
        assert len(bullets) > 0

    def test_large_project_structure(self, tmp_path: Path) -> None:
        """Test with larger project structure."""
        # Create multiple directories and files
        for i in range(3):
            dir_path = tmp_path / f"module{i}"
            dir_path.mkdir()
            for j in range(5):
                (dir_path / f"file{j}.c").write_text(f"void func{i}_{j}() {{ /* code */ }}")

        bullets = generate_local_bullets(tmp_path)

        assert len(bullets) > 0
        # Should mention the significant amount of code
        all_text = " ".join(bullets).lower()
        assert any(word in all_text for word in ["file", "function", "code"])

    def test_project_with_cmake(self, tmp_path: Path) -> None:
        """Test project with CMake build system."""
        (tmp_path / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.0)")
        (tmp_path / "main.c").write_text("int main() { return 0; }")

        bullets = generate_local_bullets(tmp_path)

        assert len(bullets) > 0
        # Should detect as C/C++ project
        all_text = " ".join(bullets).lower()
        assert "c" in all_text or "code" in all_text
