from __future__ import annotations

from pathlib import Path

import pytest

from capstone_project_team_5.services.ai_bullets import generate_ai_bullets_for_project


def test_generate_ai_bullets_for_project_with_gemini(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Minimal project scaffolding
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("Hello world", encoding="utf-8")

    # Configure Gemini and mock SDK client
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "gemini-1.5-flash")

    class _FakeResp:
        def __init__(self, text: str) -> None:
            self.text = text

    class _FakeModels:
        def generate_content(
            self, *, model: str, contents: str, config: dict | None = None
        ) -> _FakeResp:  # type: ignore[override]
            return _FakeResp("- A\n- B\n- C")

    class _FakeClient:
        def __init__(self, api_key: str) -> None:  # noqa: D401 - simple stub
            self.models = _FakeModels()

    from google import genai

    monkeypatch.setattr(genai, "Client", _FakeClient, raising=True)

    bullets = generate_ai_bullets_for_project(tmp_path, max_bullets=3)
    assert bullets == ["A", "B", "C"]


def test_generate_ai_bullets_returns_empty_when_no_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "README.md").write_text("Hello", encoding="utf-8")
    # Clear any API key that might be set in the environment
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    # No GEMINI_API_KEY set; orchestrator should return [] because llm raises
    bullets = generate_ai_bullets_for_project(tmp_path)
    assert bullets == []
