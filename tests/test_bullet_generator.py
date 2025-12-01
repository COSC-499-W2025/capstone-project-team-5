from __future__ import annotations

from pathlib import Path

import capstone_project_team_5.services.bullet_generator as bullet_generator
from capstone_project_team_5.services.project_analysis import ProjectAnalysis


def _analysis_with_tests(tmp_path: Path) -> ProjectAnalysis:
    analysis = ProjectAnalysis(project_path=tmp_path, language="Python")
    analysis.test_case_count = 4
    analysis.unit_test_count = 3
    analysis.integration_test_count = 1
    analysis.test_frameworks = {"PyTest"}
    analysis.tests_by_language = {"Python": 4}
    return analysis


def test_generate_resume_bullets_appends_testing_bullet(monkeypatch, tmp_path):
    analysis = _analysis_with_tests(tmp_path)

    monkeypatch.setattr(
        bullet_generator,
        "_try_ai_generation",
        lambda _analysis, _max: ["AI bullet"],
    )

    bullets, source = bullet_generator.generate_resume_bullets(
        tmp_path,
        use_ai=True,
        ai_available=True,
        analysis=analysis,
    )

    assert source == "AI"
    assert len(bullets) == 2
    assert bullets[-1].startswith("Implemented 3 unit and 1 integration tests")


def test_generate_resume_bullets_falls_back_to_local_and_appends(monkeypatch, tmp_path):
    analysis = _analysis_with_tests(tmp_path)

    monkeypatch.setattr(
        bullet_generator,
        "_try_ai_generation",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        bullet_generator,
        "_generate_local_bullets",
        lambda *_args, **_kwargs: [],
    )

    bullets, source = bullet_generator.generate_resume_bullets(
        tmp_path,
        use_ai=True,
        ai_available=True,
        analysis=analysis,
    )

    assert source == "Local"
    assert len(bullets) == 1
    assert bullets[0].startswith("Implemented 3 unit and 1 integration tests")
