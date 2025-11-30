from __future__ import annotations

from capstone_project_team_5.services.code_analysis_persistence import (
    _prepare_generic_data,
)
from capstone_project_team_5.services.project_analysis import ProjectAnalysis


def test_prepare_generic_data_includes_testing_metrics(tmp_path):
    analysis = ProjectAnalysis(project_path=tmp_path, language="Python")
    analysis.test_file_count = 3
    analysis.test_case_count = 12
    analysis.unit_test_count = 9
    analysis.integration_test_count = 3
    analysis.test_frameworks = {"PyTest", "Jest"}
    analysis.tests_by_language = {"Python": 9, "TypeScript": 3}
    analysis.tests_by_framework = {"PyTest": 9, "Jest": 3}

    metrics, summary = _prepare_generic_data(analysis)

    assert metrics["test_file_count"] == 3
    assert metrics["test_case_count"] == 12
    assert metrics["unit_test_count"] == 9
    assert metrics["integration_test_count"] == 3
    assert metrics["tests_by_language"]["Python"] == 9
    assert "PyTest" in metrics["test_frameworks"]
    assert summary.startswith("Python project")
