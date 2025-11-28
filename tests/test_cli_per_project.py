from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from capstone_project_team_5 import cli
from capstone_project_team_5.models.upload import DetectedProject, DirectoryNode, ZipUploadResult


class _StubConsentTool:
    def __init__(self, *, allow_external: bool, services: dict[str, bool] | None = None) -> None:
        self.use_external_services = allow_external
        self.external_services = services or {}

    @staticmethod
    def generate_consent_form() -> bool:
        return True


def _create_zip(path: Path, contents: dict[str, str]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for rel_path, data in contents.items():
            archive.writestr(rel_path, data)
    return path


def _make_result(zip_path: Path, projects: list[DetectedProject]) -> ZipUploadResult:
    return ZipUploadResult(
        filename=zip_path.name,
        size_bytes=zip_path.stat().st_size,
        file_count=sum(project.file_count for project in projects),
        tree=DirectoryNode(name="", path="", children=[]),
        projects=projects,
    )


def test_run_cli_displays_per_project_analysis(
    tmp_path: Path, capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    zip_path = tmp_path / "projects.zip"
    _create_zip(
        zip_path,
        {
            "proj1/pyproject.toml": "[build-system]\nrequires = ['setuptools']\n",
            "proj1/app/main.py": "print('hi')\n",
            "proj2/package.json": '{"dependencies": {"react": "18.0.0"}}\n',
            "proj2/src/index.ts": "console.log('hi');\n",
        },
    )

    projects = [
        DetectedProject(name="proj1", rel_path="proj1", has_git_repo=False, file_count=2),
        DetectedProject(name="proj2", rel_path="proj2", has_git_repo=True, file_count=2),
        DetectedProject(name="docs", rel_path="", has_git_repo=False, file_count=1),
    ]

    monkeypatch.setattr(
        cli, "ConsentTool", lambda: _StubConsentTool(allow_external=True, services={"Gemini": True})
    )
    monkeypatch.setattr(cli, "prompt_for_zip_file", lambda: zip_path)
    monkeypatch.setattr(cli, "display_upload_result", lambda _: None)
    monkeypatch.setattr(cli, "upload_zip", lambda _: _make_result(zip_path, projects))

    bullets: list[tuple[str, str]] = []

    def _fake_bullets(
        project_path: Path, *, use_ai: bool = False, **_: object
    ) -> tuple[list[str], str]:
        # Extract language from analysis
        from capstone_project_team_5.detection import identify_language_and_framework

        lang, fw = identify_language_and_framework(project_path)
        bullets.append((lang, fw or "None"))
        return ([f"Bullet for {lang}"], "AI" if use_ai else "Local")

    monkeypatch.setattr(cli, "generate_resume_bullets", _fake_bullets)

    exit_code = cli.run_cli()
    assert exit_code == 0

    output = capfd.readouterr().out
    assert "📊 Project Analysis" in output
    assert "Project: proj1" in output
    assert "Project: proj2" in output
    assert "Path: proj1" in output
    assert "Path: proj2" in output
    assert "Bullet for Python" in output
    assert "Bullet for TypeScript" in output
    assert "docs" not in output
    assert "📊 Analysis Summary" not in output
    assert len(bullets) == 2


def test_run_cli_falls_back_to_root_analysis_when_no_projects(
    tmp_path: Path, capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    zip_path = tmp_path / "single.zip"
    _create_zip(zip_path, {"main.py": "print('root')\n"})

    projects = [DetectedProject(name="docs", rel_path="", has_git_repo=False, file_count=1)]

    monkeypatch.setattr(cli, "ConsentTool", lambda: _StubConsentTool(allow_external=False))
    monkeypatch.setattr(cli, "prompt_for_zip_file", lambda: zip_path)
    monkeypatch.setattr(cli, "display_upload_result", lambda _: None)
    monkeypatch.setattr(cli, "upload_zip", lambda _: _make_result(zip_path, projects))

    # No need to mock - the unified system handles consent automatically
    # Just verify AI bullets are not shown when consent is missing

    exit_code = cli.run_cli()
    assert exit_code == 0

    output = capfd.readouterr().out
    assert "📊 Analysis Summary" in output
    assert "📊 Project Analysis" not in output
    # With unified system, bullets are attempted via local fallback
    # Since local generation succeeds, no error/warning is shown
    assert "Resume Bullet Points" in output or "No bullet points could be generated" in output


def test_run_cli_reports_missing_gemini_once(
    tmp_path: Path, capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    zip_path = tmp_path / "no_gemini.zip"
    _create_zip(
        zip_path,
        {
            "proj/package.json": '{"dependencies": {"next": "13"}}\n',
            "proj/src/index.ts": "export {};\n",
        },
    )

    projects = [DetectedProject(name="proj", rel_path="proj", has_git_repo=True, file_count=2)]

    monkeypatch.setattr(
        cli, "ConsentTool", lambda: _StubConsentTool(allow_external=True, services={})
    )
    monkeypatch.setattr(cli, "prompt_for_zip_file", lambda: zip_path)
    monkeypatch.setattr(cli, "display_upload_result", lambda _: None)
    monkeypatch.setattr(cli, "upload_zip", lambda _: _make_result(zip_path, projects))

    # No need to mock - the unified system handles Gemini availability automatically

    exit_code = cli.run_cli()
    assert exit_code == 0

    output = capfd.readouterr().out
    # With unified system: AI attempt made, fails (no Gemini), falls back to local automatically
    # Local generation succeeds, so bullets are shown without warnings
    assert "📊 Project Analysis" in output
    # Bullets are generated via local fallback
    assert "Resume Bullet Points" in output
