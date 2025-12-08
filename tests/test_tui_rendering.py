from __future__ import annotations

from capstone_project_team_5.tui_rendering import (
    render_detected_list,
    render_project_markdown,
)


def test_render_detected_list_empty() -> None:
    text = render_detected_list([])
    assert "# Detected Projects" in text
    assert "(No projects detected)" in text


def test_render_detected_list_single_entry() -> None:
    detected = [{"name": "MyProj", "rel_path": "src/myproj", "file_count": 42}]
    text = render_detected_list(detected)
    assert "MyProj" in text
    assert "`src/myproj`" in text
    assert "42 files" in text


def test_render_project_markdown_basic() -> None:
    upload = {"filename": "archive.zip"}
    proj = {
        "name": "MyProj",
        "rel_path": "src/myproj",
        "duration": "3 months",
        "language": "Python",
        "framework": "FastAPI",
        "file_summary": {"total_files": 10, "total_size": "123 KB"},
        "score": 7.5,
        "score_breakdown": {},
        "practices": ["TDD"],
        "tools": ["pytest"],
        "skill_timeline": [],
        "resume_bullets": [],
        "resume_bullet_source": "auto",
        "git": {"is_repo": False},
    }

    text = render_project_markdown(upload, proj, rank=1)

    assert "# archive.zip" in text
    assert "MyProj (Rank #1)" in text
    assert "`src/myproj`" in text
    assert "Duration: 3 months" in text
    assert "Language: Python" in text
    assert "Framework: FastAPI" in text
