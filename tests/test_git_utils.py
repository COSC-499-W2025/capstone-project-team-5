from __future__ import annotations

import os
import shutil
import subprocess
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from capstone_project_team_5.utils.git import (
    NumstatEntry,
    get_author_contributions,
    get_commit_type_counts,
    get_weekly_activity_window,
    parse_numstat,
    render_weekly_activity_chart,
    run_git,
    summarize_conventional_contributions,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _git_available() -> bool:
    return shutil.which("git") is not None


def _run(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    subprocess.run(cmd, cwd=str(cwd), check=True, capture_output=True, text=True, env=env)


def _init_repo(tmp: Path) -> Path:
    _run(["git", "init", "-q", "--initial-branch=main"], cwd=tmp)
    _run(["git", "config", "user.name", "Tester"], cwd=tmp)
    _run(["git", "config", "user.email", "tester@example.com"], cwd=tmp)
    return tmp


def _commit(
    repo: Path,
    *,
    filename: str,
    content: str,
    message: str,
    author: str,
    email: str,
    when: datetime,
) -> None:
    (repo / filename).write_text(content, encoding="utf-8")
    _run(["git", "add", filename], cwd=repo)
    env = os.environ.copy()
    stamp = str(int(when.timestamp()))
    env.update(
        {
            "GIT_AUTHOR_NAME": author,
            "GIT_AUTHOR_EMAIL": email,
            "GIT_COMMITTER_NAME": author,
            "GIT_COMMITTER_EMAIL": email,
            "GIT_AUTHOR_DATE": stamp,
            "GIT_COMMITTER_DATE": stamp,
        }
    )
    _run(["git", "commit", "-q", "-m", message], cwd=repo, env=env)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_parse_numstat_filters_binary() -> None:
    raw = "10\t2\tsrc/app.py\n-\t-\tassets/logo.png\n3\t0\tsrc/util/helpers.py\n"
    entries = parse_numstat(raw)
    assert [e.path for e in entries] == ["src/app.py", "src/util/helpers.py"]
    assert entries[0] == NumstatEntry("src/app.py", 10, 2)


@pytest.mark.skipif(not _git_available(), reason="git not installed")
def test_run_git_fails_outside_repo(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError):
        run_git(tmp_path, "status")


@pytest.mark.skipif(not _git_available(), reason="git not installed")
def test_author_contributions(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    t0 = datetime.now(UTC)
    _commit(
        repo,
        filename="a.txt",
        content="one\n",
        message="chore: init",
        author="Alice",
        email="alice@example.com",
        when=t0,
    )
    _commit(
        repo,
        filename="b.txt",
        content="first\nsecond\n",
        message="feat: add two lines",
        author="Bob",
        email="bob@example.com",
        when=t0 + timedelta(seconds=5),
    )

    contribs = get_author_contributions(repo)
    authors = {c.author for c in contribs}
    assert {"Alice", "Bob"} <= authors

    data = {c.author: c for c in contribs}
    assert data["Alice"].added >= 1
    assert data["Bob"].added >= 2


@pytest.mark.skipif(not _git_available(), reason="git not installed")
def test_conventional_commit_counts(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    t0 = datetime.now(UTC)
    _commit(
        repo,
        filename="c.txt",
        content="x\n",
        message="feat: add x",
        author="Carol",
        email="carol@example.com",
        when=t0,
    )
    _commit(
        repo,
        filename="d.txt",
        content="y\n",
        message="fix: bug",
        author="Carol",
        email="carol@example.com",
        when=t0 + timedelta(seconds=5),
    )

    counts = get_commit_type_counts(repo)
    assert counts["Carol"]["feat"] == 1
    assert counts["Carol"]["fix"] == 1

    summary = summarize_conventional_contributions(repo)
    line = next((s for s in summary if s.startswith("Carol")), "")
    assert "feat:1" in line and "fix:1" in line


@pytest.mark.skipif(not _git_available(), reason="git not installed")
def test_weekly_activity_window(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    prev_monday = monday - timedelta(days=7)

    prev = datetime(prev_monday.year, prev_monday.month, prev_monday.day, 12, 0, tzinfo=UTC)
    cur = datetime(monday.year, monday.month, monday.day, 12, 0, tzinfo=UTC)

    _commit(
        repo,
        filename="w1.txt",
        content="a\n",
        message="docs: prev week",
        author="Dana",
        email="dana@example.com",
        when=prev,
    )
    _commit(
        repo,
        filename="w2.txt",
        content="b\n",
        message="docs: this week",
        author="Dana",
        email="dana@example.com",
        when=cur,
    )

    bins, activity = get_weekly_activity_window(repo, start_week=prev_monday, end_week=monday)
    assert bins[0] == prev_monday and bins[-1] == monday
    assert activity["Dana"][:2] == [1, 1]

    bins2, activity2 = get_weekly_activity_window(repo, week=monday)
    assert bins2 == [monday]
    assert activity2["Dana"][0] == 1


def test_render_weekly_activity_chart_empty() -> None:
    assert render_weekly_activity_chart({}) == []
