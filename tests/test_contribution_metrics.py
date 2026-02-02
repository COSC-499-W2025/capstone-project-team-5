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


def test_calculate_importance_score_basic():
    """Test basic importance score calculation."""
    metrics = {"code": 10, "test": 5, "document": 2}
    duration = timedelta(days=365)
    file_count = 50

    score, breakdown = ContributionMetrics.calculate_importance_score(metrics, duration, file_count)

    assert isinstance(score, float)
    assert score > 0
    assert isinstance(breakdown, dict)
    assert "contribution_score" in breakdown
    assert "diversity_bonus" in breakdown
    assert "duration_score" in breakdown
    assert "file_score" in breakdown


def test_calculate_importance_score_empty_metrics():
    """Test importance score with empty metrics."""
    metrics = {}
    duration = timedelta(days=30)
    file_count = 10

    score, breakdown = ContributionMetrics.calculate_importance_score(metrics, duration, file_count)

    assert isinstance(score, float)
    assert score >= 0
    assert isinstance(breakdown, dict)


def test_calculate_importance_score_zero_duration():
    """Test importance score with zero duration."""
    metrics = {"code": 5}
    duration = timedelta(days=0)
    file_count = 20

    score, breakdown = ContributionMetrics.calculate_importance_score(metrics, duration, file_count)

    assert isinstance(score, float)
    assert score > 0
    assert breakdown["duration_score"] == 0.0


def test_calculate_importance_score_diversity_bonus():
    """Test that projects with more diverse contributions get higher scores."""
    metrics_diverse = {"code": 10, "test": 5, "document": 3, "devops": 2}
    metrics_single = {"code": 20}
    duration = timedelta(days=100)
    file_count = 30

    score_diverse, _ = ContributionMetrics.calculate_importance_score(
        metrics_diverse, duration, file_count
    )
    score_single, _ = ContributionMetrics.calculate_importance_score(
        metrics_single, duration, file_count
    )

    assert score_diverse > score_single


def test_calculate_importance_score_duration_factor():
    """Test that longer projects get higher scores."""
    metrics = {"code": 10}
    duration_short = timedelta(days=30)
    duration_long = timedelta(days=365)
    file_count = 20

    score_short, _ = ContributionMetrics.calculate_importance_score(
        metrics, duration_short, file_count
    )
    score_long, _ = ContributionMetrics.calculate_importance_score(
        metrics, duration_long, file_count
    )

    assert score_long > score_short


def test_format_score_breakdown():
    """Test formatting of score breakdown for display."""
    score = 150.5
    breakdown = {
        "contribution_score": 100.0,
        "diversity_bonus": 30.0,
        "duration_score": 15.0,
        "file_score": 5.5,
        "total_contributions": 50.0,
        "diversity_count": 3.0,
    }

    formatted = ContributionMetrics.format_score_breakdown(score, breakdown)

    assert "Importance Score: 150.5" in formatted
    assert "Contributions:" in formatted
    assert "Diversity Bonus:" in formatted
    assert "Duration:" in formatted
    assert "File Count:" in formatted


def test_apply_score_factors_can_disable_components() -> None:
    """apply_score_factors should zero-out disabled components and recompute score."""
    metrics = {"code": 10, "test": 5}
    duration = timedelta(days=120)
    file_count = 40

    base_score, breakdown = ContributionMetrics.calculate_importance_score(
        metrics, duration, file_count
    )

    factors = {
        "contribution": False,
        "diversity": True,
        "duration": False,
        "file_count": True,
    }

    new_score, new_breakdown = ContributionMetrics.apply_score_factors(breakdown, factors)

    # Contribution and duration components should be zeroed.
    assert new_breakdown["contribution_score"] == 0.0
    assert new_breakdown["duration_score"] == 0.0
    # Diversity and file components remain unchanged.
    assert new_breakdown["diversity_bonus"] == breakdown["diversity_bonus"]
    assert new_breakdown["file_score"] == breakdown["file_score"]
    # New score should be lower than the base score.
    assert new_score < base_score


def test_rank_projects_basic():
    """Test basic project ranking."""
    projects = [(1, 100.0), (2, 50.0), (3, 150.0)]

    ranked = ContributionMetrics.rank_projects(projects)

    assert len(ranked) == 3
    assert ranked[0] == (3, 1)
    assert ranked[1] == (1, 2)
    assert ranked[2] == (2, 3)


def test_rank_projects_ties():
    """Test that projects with same score get same rank."""
    projects = [(1, 100.0), (2, 100.0), (3, 50.0)]

    ranked = ContributionMetrics.rank_projects(projects)

    assert len(ranked) == 3
    assert ranked[0][1] == 1
    assert ranked[1][1] == 1
    assert ranked[2][1] == 3


def test_rank_projects_empty():
    """Test ranking with empty project list."""
    ranked = ContributionMetrics.rank_projects([])

    assert ranked == []


def test_rank_projects_single():
    """Test ranking with single project."""
    projects = [(1, 100.0)]

    ranked = ContributionMetrics.rank_projects(projects)

    assert len(ranked) == 1
    assert ranked[0] == (1, 1)
