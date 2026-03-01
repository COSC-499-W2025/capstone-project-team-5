"""Tests for role_detector module."""

from __future__ import annotations

from pathlib import Path

from capstone_project_team_5.role_detector import (
    UserRole,
    detect_user_role,
    format_role_summary,
)
from capstone_project_team_5.utils.file_patterns import (
    is_code_file,
    is_documentation_file,
    is_infrastructure_file,
    is_initialization_file,
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

    def test_core_contributor_50_percent(self) -> None:
        """Test core contributor with 50% contribution."""
        contributions = [
            AuthorContribution(author="Alice", commits=50, added=5000, deleted=500),
            AuthorContribution(author="Bob", commits=50, added=5000, deleted=500),
        ]

        role = detect_user_role(
            project_path=Path("/fake/path"),
            current_user="Bob",
            author_contributions=contributions,
            collaborator_count=2,
        )

        assert role is not None
        assert role.role == "Core Contributor"
        assert 48.0 <= role.contribution_percentage <= 52.0
        assert role.confidence == "High"

    def test_core_contributor_40_percent(self) -> None:
        """Test core contributor with 40% contribution."""
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
        assert role.role == "Core Contributor"
        assert 38.0 <= role.contribution_percentage <= 42.0
        assert role.confidence == "High"

    def test_major_contributor_30_percent(self) -> None:
        """Test major contributor with 30% contribution."""
        contributions = [
            AuthorContribution(author="Alice", commits=60, added=6000, deleted=600),
            AuthorContribution(author="Bob", commits=30, added=3000, deleted=300),
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
        assert 28.0 <= role.contribution_percentage <= 32.0
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

    def test_format_lead_developer(self) -> None:
        """Test formatting lead developer role."""
        role = UserRole(
            role="Lead Developer",
            contribution_percentage=70.5,
            is_collaborative=True,
            confidence="High",
            total_commits=100,
            total_contributors=3,
            justification=(
                "100 commits representing 70.5% of contributions with 2 other contributors"
            ),
        )

        summary = format_role_summary(role)

        assert "Lead Developer" in summary
        assert "70.5%" in summary
        assert "100 commits" in summary

    def test_format_contributor(self) -> None:
        """Test formatting contributor role."""
        role = UserRole(
            role="Contributor",
            contribution_percentage=15.0,
            is_collaborative=True,
            confidence="Medium",
            total_commits=10,
            total_contributors=5,
            justification=(
                "10 commits representing 15.0% of contributions with 4 other contributors"
            ),
        )

        summary = format_role_summary(role)

        assert "Contributor" in summary
        assert "15.0%" in summary
        assert "10 commits" in summary

    def test_format_core_contributor(self) -> None:
        """Test formatting core contributor role."""
        role = UserRole(
            role="Core Contributor",
            contribution_percentage=45.0,
            is_collaborative=True,
            confidence="High",
            total_commits=45,
            total_contributors=3,
            justification=(
                "45 commits representing 45.0% of contributions with 2 other contributors"
            ),
        )

        summary = format_role_summary(role)

        assert "Core Contributor" in summary
        assert "45.0%" in summary
        assert "45 commits" in summary

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


class TestSpecializedRoleDetection:
    """Tests for multi-pass specialized role overrides."""

    def test_project_creator_override(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        """Project Creator should override contribution-only role when signal is present."""
        contributions = [
            AuthorContribution(author="Alice", commits=30, added=3000, deleted=200),
            AuthorContribution(author="Bob", commits=70, added=7000, deleted=400),
        ]

        monkeypatch.setattr(
            "capstone_project_team_5.role_detector._is_project_creator", lambda *_: True
        )
        monkeypatch.setattr("capstone_project_team_5.role_detector._is_tech_lead", lambda *_: False)
        monkeypatch.setattr(
            "capstone_project_team_5.role_detector._is_maintainer", lambda *_: False
        )

        role = detect_user_role(
            project_path=Path("/fake/path"),
            current_user="Alice",
            author_contributions=contributions,
            collaborator_count=2,
        )

        assert role is not None
        assert role.role == "Project Creator"
        assert "earliest project author" in role.justification

    def test_tech_lead_override(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        """Tech Lead should override base role when infrastructure signal is present."""
        contributions = [
            AuthorContribution(author="Alice", commits=35, added=3500, deleted=350),
            AuthorContribution(author="Bob", commits=65, added=6500, deleted=650),
        ]

        monkeypatch.setattr(
            "capstone_project_team_5.role_detector._is_project_creator", lambda *_: False
        )
        monkeypatch.setattr("capstone_project_team_5.role_detector._is_tech_lead", lambda *_: True)
        monkeypatch.setattr(
            "capstone_project_team_5.role_detector._is_maintainer", lambda *_: False
        )

        role = detect_user_role(
            project_path=Path("/fake/path"),
            current_user="Alice",
            author_contributions=contributions,
            collaborator_count=2,
        )

        assert role is not None
        assert role.role == "Tech Lead"
        assert "infrastructure" in role.justification

    def test_maintainer_override(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        """Maintainer should override base role when sustained activity signal is present."""
        contributions = [
            AuthorContribution(author="Alice", commits=28, added=2800, deleted=280),
            AuthorContribution(author="Bob", commits=72, added=7200, deleted=720),
        ]

        monkeypatch.setattr(
            "capstone_project_team_5.role_detector._is_project_creator", lambda *_: False
        )
        monkeypatch.setattr("capstone_project_team_5.role_detector._is_tech_lead", lambda *_: False)
        monkeypatch.setattr("capstone_project_team_5.role_detector._is_maintainer", lambda *_: True)

        role = detect_user_role(
            project_path=Path("/fake/path"),
            current_user="Alice",
            author_contributions=contributions,
            collaborator_count=2,
        )

        assert role is not None
        assert role.role == "Maintainer"
        assert "maintenance" in role.justification

    def test_documentation_lead_override(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        """Documentation Lead should override base role when docs-heavy signal is present."""
        contributions = [
            AuthorContribution(author="Alice", commits=22, added=2200, deleted=220),
            AuthorContribution(author="Bob", commits=78, added=7800, deleted=780),
        ]

        monkeypatch.setattr(
            "capstone_project_team_5.role_detector._is_project_creator", lambda *_: False
        )
        monkeypatch.setattr("capstone_project_team_5.role_detector._is_tech_lead", lambda *_: False)
        monkeypatch.setattr(
            "capstone_project_team_5.role_detector._is_documentation_lead", lambda *_: True
        )
        monkeypatch.setattr(
            "capstone_project_team_5.role_detector._is_maintainer", lambda *_: False
        )

        role = detect_user_role(
            project_path=Path("/fake/path"),
            current_user="Alice",
            author_contributions=contributions,
            collaborator_count=2,
        )

        assert role is not None
        assert role.role == "Documentation Lead"
        assert "documentation" in role.justification

    def test_security_lead_override(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        """Security Lead should override base role when security signal is present."""
        contributions = [
            AuthorContribution(author="Alice", commits=24, added=2400, deleted=240),
            AuthorContribution(author="Bob", commits=76, added=7600, deleted=760),
        ]

        monkeypatch.setattr(
            "capstone_project_team_5.role_detector._is_project_creator", lambda *_: False
        )
        monkeypatch.setattr("capstone_project_team_5.role_detector._is_tech_lead", lambda *_: False)
        monkeypatch.setattr(
            "capstone_project_team_5.role_detector._is_security_lead", lambda *_: True
        )
        monkeypatch.setattr(
            "capstone_project_team_5.role_detector._is_documentation_lead", lambda *_: False
        )
        monkeypatch.setattr(
            "capstone_project_team_5.role_detector._is_maintainer", lambda *_: False
        )

        role = detect_user_role(
            project_path=Path("/fake/path"),
            current_user="Alice",
            author_contributions=contributions,
            collaborator_count=2,
        )

        assert role is not None
        assert role.role == "Security Lead"
        assert "security" in role.justification


class TestFilePatternUtilities:
    """Tests for file-pattern-based role signal utilities."""

    def test_is_initialization_file(self) -> None:
        assert is_initialization_file("package.json") is True
        assert is_initialization_file("backend/requirements.txt") is True
        assert is_initialization_file("src/main.py") is False

    def test_is_infrastructure_file(self) -> None:
        assert is_infrastructure_file("Dockerfile") is True
        assert is_infrastructure_file(".github/workflows/ci.yml") is True
        assert is_infrastructure_file("src/app.py") is False

    def test_is_documentation_file(self) -> None:
        assert is_documentation_file("README.md") is True
        assert is_documentation_file("docs/architecture.md") is True
        assert is_documentation_file("src/service.ts") is False

    def test_is_code_file(self) -> None:
        assert is_code_file("src/service.ts") is True
        assert is_code_file("backend/main.py") is True
        assert is_code_file("README.md") is False
