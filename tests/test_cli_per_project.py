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
        file_count=len(projects),
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

    bullets: list[list[str]] = []

    def _fake_bullets(*, language: str, framework: str | None, **_: object) -> list[str]:
        bullets.append([language, framework or "None"])
        return [f"Bullet for {language}"]

    monkeypatch.setattr(cli, "generate_bullet_points_from_analysis", _fake_bullets)

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

    def _fail_generate(**_: object) -> list[str]:  # pragma: no cover - ensures branch not taken
        pytest.fail("AI bullet generator should not be invoked when consent is missing")

    monkeypatch.setattr(cli, "generate_bullet_points_from_analysis", _fail_generate)

    exit_code = cli.run_cli()
    assert exit_code == 0

    output = capfd.readouterr().out
    assert "📊 Analysis Summary" in output
    assert "📊 Project Analysis" not in output
    assert "⚠️  External services consent not given" in output
    assert "AI Bullet Points" not in output


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

    calls: list[dict[str, object]] = []

    def _record_calls(
        **kwargs: object,
    ) -> list[str]:  # pragma: no cover - branch should not execute
        calls.append(kwargs)
        return []

    monkeypatch.setattr(cli, "generate_bullet_points_from_analysis", _record_calls)

    exit_code = cli.run_cli()
    assert exit_code == 0

    output = capfd.readouterr().out
    message = "⚠️  Gemini not enabled in external services; skipping AI bullet generation."
    assert output.count(message) == 1
    assert "📊 Project Analysis" in output
    assert "AI Bullet Points" not in output
    assert calls == []
