"""Tests for contributor analysis module."""

from pathlib import Path

from capstone_project_team_5.contributor_analysis import (
    ContributorDetector,
    analyze_contributors,
)


def test_is_git_repository() -> None:
    """Test detection of git repositories."""
    # Current project should be a git repo
    current_dir = Path(__file__).parent.parent
    assert ContributorDetector._is_git_repository(current_dir)

    # A temp directory should not be a git repo
    non_git_dir = Path("/tmp/non_existent_git_repo_12345")
    assert not ContributorDetector._is_git_repository(non_git_dir)


def test_analyze_contributors() -> None:
    """Test analyzing contributors from current repository."""
    repo_path = Path(__file__).parent.parent

    result = analyze_contributors(repo_path)

    # Should have contributors key
    assert "contributors" in result
    contributors = result["contributors"]

    # Should have at least one contributor
    assert len(contributors) > 0

    # Check structure of first contributor
    first = contributors[0]
    assert hasattr(first, "name")
    assert hasattr(first, "email")
    assert hasattr(first, "commits")
    assert hasattr(first, "files_modified")
    assert first.commits > 0

    # Contributors should be sorted by commits (descending)
    if len(contributors) > 1:
        assert contributors[0].commits >= contributors[1].commits


def test_analyze_contributors_non_git() -> None:
    """Test analyzing a non-git directory returns empty result."""
    non_git_dir = Path("/tmp")

    result = analyze_contributors(non_git_dir)

    assert "contributors" in result
    # Should return empty list for non-git directory
    assert result["contributors"] == []


def test_analyze_contributors_non_existent() -> None:
    """Test analyzing a non-existent directory returns empty result."""
    non_existent = Path("/tmp/non_existent_dir_12345_xyz")

    result = analyze_contributors(non_existent)

    assert "contributors" in result
    assert result["contributors"] == []
