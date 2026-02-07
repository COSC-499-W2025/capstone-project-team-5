"""Tests for role_detector module."""

from __future__ import annotations

from pathlib import Path

from capstone_project_team_5.role_detector import (
    UserRole,
    detect_user_role,
    format_role_summary,
)
from capstone_project_team_5.utils.git import AuthorContribution


class TestDetectUserRole:
    """Test suite for detect_user_role function."""

    def test_solo_developer_100_percent(self) -> None:
        """Test detection of solo developer with 100% contribution."""
        contributions = [
            AuthorContribution(author="Alice", commits=50, added=1000, deleted=200),
        ]

        role = detect_user_role(
            project_path=Path("/fake/path"),
            current_user="Alice",
            author_contributions=contributions,
            collaborator_count=1,
        )

        assert role is not None
        assert role.role == "Solo Developer"
        assert role.contribution_percentage == 100.0
        assert role.is_collaborative is False
        assert role.confidence == "High"
        assert role.total_commits == 50

    def test_solo_developer_low_commits(self) -> None:
        """Test solo developer with few commits has medium confidence."""
        contributions = [
            AuthorContribution(author="Bob", commits=3, added=100, deleted=20),
        ]

        role = detect_user_role(
            project_path=Path("/fake/path"),
            current_user="Bob",
            author_contributions=contributions,
            collaborator_count=1,
        )

        assert role is not None
        assert role.role == "Solo Developer"
        assert role.confidence == "Medium"

    def test_lead_developer_high_contribution(self) -> None:
        """Test lead developer with 70% contribution."""
        contributions = [
            AuthorContribution(author="Alice", commits=70, added=7000, deleted=1000),
            AuthorContribution(author="Bob", commits=30, added=3000, deleted=500),
        ]

        role = detect_user_role(
            project_path=Path("/fake/path"),
            current_user="Alice",
            author_contributions=contributions,
            collaborator_count=2,
        )

        assert role is not None
        assert role.role == "Lead Developer"
        assert 65.0 <= role.contribution_percentage <= 75.0
        assert role.is_collaborative is True
        assert role.confidence == "High"
        assert role.total_contributors == 2

    def test_lead_developer_edge_case_60_percent(self) -> None:
        """Test lead developer at 60% threshold."""
        contributions = [
            AuthorContribution(author="Charlie", commits=60, added=6000, deleted=0),
            AuthorContribution(author="Dave", commits=40, added=4000, deleted=0),
        ]

        role = detect_user_role(
            project_path=Path("/fake/path"),
            current_user="Charlie",
            author_contributions=contributions,
            collaborator_count=2,
        )

        assert role is not None
        assert role.role == "Lead Developer"
        assert role.contribution_percentage == 60.0

    def test_major_contributor_40_percent(self) -> None:
        """Test major contributor with 40% contribution."""
        contributions = [
            AuthorContribution(author="Alice", commits=50, added=5000, deleted=500),
            AuthorContribution(author="Bob", commits=40, added=4000, deleted=400),
            AuthorContribution(author="Charlie", commits=10, added=1000, deleted=100),
        ]

        role = detect_user_role(
            project_path=Path("/fake/path"),
            current_user="Bob",
            author_contributions=contributions,
            collaborator_count=3,
        )

        assert role is not None
        assert role.role == "Major Contributor"
        assert 38.0 <= role.contribution_percentage <= 42.0
        assert role.confidence == "High"

    def test_contributor_20_percent(self) -> None:
        """Test contributor with 20% contribution."""
        contributions = [
            AuthorContribution(author="Alice", commits=60, added=6000, deleted=0),
            AuthorContribution(author="Bob", commits=20, added=2000, deleted=0),
            AuthorContribution(author="Charlie", commits=20, added=2000, deleted=0),
        ]

        role = detect_user_role(
            project_path=Path("/fake/path"),
            current_user="Bob",
            author_contributions=contributions,
            collaborator_count=3,
        )

        assert role is not None
        assert role.role == "Contributor"
        assert 18.0 <= role.contribution_percentage <= 22.0

    def test_minor_contributor_5_percent(self) -> None:
        """Test minor contributor with 5% contribution."""
        contributions = [
            AuthorContribution(author="Alice", commits=90, added=9000, deleted=0),
            AuthorContribution(author="Bob", commits=5, added=500, deleted=0),
            AuthorContribution(author="Charlie", commits=5, added=500, deleted=0),
        ]

        role = detect_user_role(
            project_path=Path("/fake/path"),
            current_user="Bob",
            author_contributions=contributions,
            collaborator_count=3,
        )

        assert role is not None
        assert role.role == "Minor Contributor"
        assert role.contribution_percentage < 10.0

    def test_no_user_contributions_returns_none(self) -> None:
        """Test returns None when user not found in contributions."""
        contributions = [
            AuthorContribution(author="Alice", commits=50, added=5000, deleted=0),
            AuthorContribution(author="Bob", commits=50, added=5000, deleted=0),
        ]

        role = detect_user_role(
            project_path=Path("/fake/path"),
            current_user="Charlie",
            author_contributions=contributions,
            collaborator_count=2,
        )

        assert role is None

    def test_empty_contributions_returns_none(self) -> None:
        """Test returns None with empty contributions list."""
        role = detect_user_role(
            project_path=Path("/fake/path"),
            current_user="Alice",
            author_contributions=[],
            collaborator_count=0,
        )

        assert role is None

    def test_none_current_user_returns_none(self) -> None:
        """Test returns None when current_user is None."""
        contributions = [
            AuthorContribution(author="Alice", commits=50, added=5000, deleted=0),
        ]

        role = detect_user_role(
            project_path=Path("/fake/path"),
            current_user=None,
            author_contributions=contributions,
            collaborator_count=1,
        )

        assert role is None

    def test_case_insensitive_user_matching(self) -> None:
        """Test user matching is case-insensitive."""
        contributions = [
            AuthorContribution(author="Alice Smith", commits=50, added=5000, deleted=0),
        ]

        role = detect_user_role(
            project_path=Path("/fake/path"),
            current_user="alice smith",
            author_contributions=contributions,
            collaborator_count=1,
        )

        assert role is not None
        assert role.role == "Solo Developer"

    def test_whitespace_handling_in_user_matching(self) -> None:
        """Test user matching handles whitespace."""
        contributions = [
            AuthorContribution(author="  Bob Jones  ", commits=50, added=5000, deleted=0),
        ]

        role = detect_user_role(
            project_path=Path("/fake/path"),
            current_user="Bob Jones",
            author_contributions=contributions,
            collaborator_count=1,
        )

        assert role is not None
        assert role.role == "Solo Developer"

    def test_weighted_contribution_calculation(self) -> None:
        """Test that contribution % uses weighted average of commits and changes."""
        # User has 50% of commits but 70% of changes
        contributions = [
            AuthorContribution(author="Alice", commits=50, added=7000, deleted=0),
            AuthorContribution(author="Bob", commits=50, added=3000, deleted=0),
        ]

        role = detect_user_role(
            project_path=Path("/fake/path"),
            current_user="Alice",
            author_contributions=contributions,
            collaborator_count=2,
        )

        assert role is not None
        # Expected: 0.6 * 50 + 0.4 * 70 = 30 + 28 = 58%
        assert 57.0 <= role.contribution_percentage <= 59.0


class TestFormatRoleSummary:
    """Test suite for format_role_summary function."""

    def test_format_solo_developer(self) -> None:
        """Test formatting solo developer role."""
        role = UserRole(
            role="Solo Developer",
            contribution_percentage=100.0,
            is_collaborative=False,
            confidence="High",
            total_commits=50,
            total_contributors=1,
            justification="Sole author with 50 commits",
        )

        summary = format_role_summary(role)

        assert "Solo Developer" in summary
        assert "50 commits" in summary
        assert "👨‍💻" in summary

    def test_format_lead_developer(self) -> None:
        """Test formatting lead developer role."""
        role = UserRole(
            role="Lead Developer",
            contribution_percentage=70.5,
            is_collaborative=True,
            confidence="High",
            total_commits=100,
            total_contributors=3,
            justification="100 commits representing 70.5% of contributions with 2 other contributors",
        )

        summary = format_role_summary(role)

        assert "Lead Developer" in summary
        assert "70.5%" in summary
        assert "100 commits" in summary
        assert "🎯" in summary

    def test_format_contributor(self) -> None:
        """Test formatting contributor role."""
        role = UserRole(
            role="Contributor",
            contribution_percentage=15.0,
            is_collaborative=True,
            confidence="Medium",
            total_commits=10,
            total_contributors=5,
            justification="10 commits representing 15.0% of contributions with 4 other contributors",
        )

        summary = format_role_summary(role)

        assert "Contributor" in summary
        assert "15.0%" in summary
        assert "10 commits" in summary

    def test_format_none_returns_unknown(self) -> None:
        """Test formatting None returns unknown message."""
        summary = format_role_summary(None)

        assert "Unknown" in summary
        assert "insufficient data" in summary.lower()


class TestRoleJustification:
    """Test suite for role justification generation."""

    def test_solo_developer_justification(self) -> None:
        """Test justification for solo developer."""
        contributions = [
            AuthorContribution(author="Alice", commits=50, added=1000, deleted=200),
        ]

        role = detect_user_role(
            project_path=Path("/fake/path"),
            current_user="Alice",
            author_contributions=contributions,
            collaborator_count=1,
        )

        assert role is not None
        assert role.justification == "Sole author with 50 commits"

    def test_solo_developer_single_commit(self) -> None:
        """Test justification for solo developer with one commit uses singular."""
        contributions = [
            AuthorContribution(author="Bob", commits=1, added=10, deleted=2),
        ]

        role = detect_user_role(
            project_path=Path("/fake/path"),
            current_user="Bob",
            author_contributions=contributions,
            collaborator_count=1,
        )

        assert role is not None
        assert role.justification == "Sole author with 1 commit"

    def test_collaborative_justification_two_contributors(self) -> None:
        """Test justification for collaborative project with 2 contributors."""
        contributions = [
            AuthorContribution(author="Alice", commits=70, added=7000, deleted=700),
            AuthorContribution(author="Bob", commits=30, added=3000, deleted=300),
        ]

        role = detect_user_role(
            project_path=Path("/fake/path"),
            current_user="Alice",
            author_contributions=contributions,
            collaborator_count=2,
        )

        assert role is not None
        assert "70 commits" in role.justification
        assert "70.0%" in role.justification
        assert "1 other contributor" in role.justification

    def test_collaborative_justification_multiple_contributors(self) -> None:
        """Test justification for collaborative project with multiple contributors."""
        contributions = [
            AuthorContribution(author="Alice", commits=50, added=5000, deleted=500),
            AuthorContribution(author="Bob", commits=30, added=3000, deleted=300),
            AuthorContribution(author="Charlie", commits=20, added=2000, deleted=200),
        ]

        role = detect_user_role(
            project_path=Path("/fake/path"),
            current_user="Alice",
            author_contributions=contributions,
            collaborator_count=3,
        )

        assert role is not None
        assert "50 commits" in role.justification
        assert "50.0%" in role.justification
        assert "2 other contributors" in role.justification
