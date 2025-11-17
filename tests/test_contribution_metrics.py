import os
import subprocess
import time
from datetime import timedelta
from pathlib import Path

from capstone_project_team_5.contribution_metrics import ContributionMetrics


def init_mock_git_repo(tmp_path: Path):
    """Initialize a Git repo with commits for different file types."""

    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=tmp_path, check=True)

    files_by_category = {
        "code": ["main.py", "utils.js", "example.py"],
        "test": ["test_main.py", "test_utils.js"],
        "document": ["README.md", "docs/guide.md"],
        "design": ["design/mockup.sketch"],
        "devops": [".github/workflows/ci.yml", "Dockerfile"],
        "data": ["data/sample.csv"],
    }

    for category, files in files_by_category.items():
        for i, file_path in enumerate(files):
            full_path = tmp_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(f"Dummy content for {category} file {i}")
            subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)

            # Commit date sequential days
            commit_date = f"2025-01-{i + 1:02d}T12:00:00"
            env = dict(**os.environ, GIT_AUTHOR_DATE=commit_date, GIT_COMMITTER_DATE=commit_date)

            subprocess.run(
                ["git", "commit", "-m", f"Add {file_path}"], cwd=tmp_path, check=True, env=env
            )


def test_git_project_duration(tmp_path: Path):
    """Tests Git project duration using a mock Git repo."""

    init_mock_git_repo(tmp_path)

    duration, formatted = ContributionMetrics.get_project_duration(tmp_path)

    # Since commits are sequential days, duration should be 2 days
    assert isinstance(duration, timedelta)
    assert duration.days == 2
    assert "Started:" in formatted and "Ended:" in formatted


def test_non_git_project_duration(tmp_path: Path):
    """Tests non-Git project duration using real file creation and modified timestamps."""

    file1 = tmp_path / "file1.py"
    file2 = tmp_path / "file2.py"
    file1.write_text("print('hello')")
    file2.write_text("print('world')")

    # Use the real creation time as start, patch modified time for end

    t2 = time.time() + (3600 * 72)  # some time after creation (3 days)
    os.utime(file2, (t2, t2))  # set access and modified times

    duration, formatted = ContributionMetrics._get_non_git_project_duration(tmp_path)

    assert isinstance(duration, timedelta)
    assert duration.days == 3
    assert "Started:" in formatted
    assert "Ended:" in formatted


def test_git_metrics(tmp_path: Path):
    """Tests a Git project contribution metrics."""

    init_mock_git_repo(tmp_path)

    result = ContributionMetrics.get_project_contribution_metrics(tmp_path)
    metrics = result[0]
    source = result[1]

    assert metrics["code"] == 3
    assert metrics["test"] == 2
    assert metrics["document"] == 2
    assert metrics["design"] == 1
    assert metrics["devops"] == 2
    assert metrics["data"] == 1
    assert source == "based on Git commits"


def test_non_git_metrics(tmp_path: Path):
    """Tests non-Git metrics using mock files."""

    files_by_category = {
        "code": ["main.py", "utils.js"],
        "test": ["test_main.py", "test_utils.js"],
        "document": ["README.md", "docs/guide.md"],
        "design": ["design/mockup.sketch"],
        "devops": [".github/workflows/ci.yml", "Dockerfile"],
        "data": ["data/sample.csv"],
    }

    for category, files in files_by_category.items():
        for file_path in files:
            full_path = tmp_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(f"Dummy content for {category} file")

    result = ContributionMetrics.get_project_contribution_metrics(tmp_path)
    metrics = result[0]
    source = result[1]

    for category, files in files_by_category.items():
        assert metrics[category] == len(files)

    assert source == "based on file counts"
