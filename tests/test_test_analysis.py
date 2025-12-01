from __future__ import annotations

from capstone_project_team_5.services.bullet_generator import build_testing_bullet
from capstone_project_team_5.services.project_analysis import ProjectAnalysis
from capstone_project_team_5.services.test_analysis import analyze_tests


def test_analyze_tests_counts_python(tmp_path):
    project_dir = tmp_path / "sample"
    test_dir = project_dir / "tests"
    test_dir.mkdir(parents=True)

    test_file = test_dir / "test_example.py"
    test_file.write_text(
        """
import pytest


def helper():
    return True


def test_first():
    assert helper()


class TestSuite:
    def test_second(self):
        assert 1 == 1
"""
    )

    result = analyze_tests(project_dir)

    assert result.test_file_count == 1
    assert result.test_case_count == 2
    assert result.unit_test_count == 2
    assert result.tests_by_language["Python"] == 2
    assert "PyTest" in result.frameworks


def test_build_testing_bullet_formats_counts(tmp_path):
    analysis = ProjectAnalysis(project_path=tmp_path, language="Python")
    analysis.test_case_count = 10
    analysis.unit_test_count = 7
    analysis.integration_test_count = 3
    analysis.test_frameworks = {"PyTest", "Jest"}
    analysis.tests_by_language = {"Python": 7, "TypeScript": 3}

    bullet = build_testing_bullet(analysis)

    assert bullet is not None
    assert "7 unit and 3 integration tests" in bullet
    assert "Python and TypeScript" in bullet
    assert "PyTest" not in bullet and "Jest" not in bullet


def test_framework_detection_avoids_substring_matches(tmp_path):
    project_dir = tmp_path / "sample"
    (project_dir / "tests").mkdir(parents=True)
    test_file = project_dir / "tests" / "test_misc.py"
    test_file.write_text(
        """
def test_available_flag():
    assert True
"""
    )

    result = analyze_tests(project_dir)
    assert result.frameworks == set()
