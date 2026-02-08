"""Tests for role taxonomy and constants."""

from __future__ import annotations

from capstone_project_team_5.constants.roles import (
    ROLE_METADATA,
    ProjectRole,
    get_role_description,
    get_role_priority,
)


class TestProjectRole:
    """Tests for ProjectRole enum."""

    def test_all_roles_have_metadata(self) -> None:
        """Test that all ProjectRole values have corresponding metadata."""
        for role in ProjectRole:
            assert role in ROLE_METADATA
            metadata = ROLE_METADATA[role]
            assert metadata.role == role
            assert metadata.description
            assert metadata.display_priority > 0

    def test_role_enum_values(self) -> None:
        """Test that role enum values match expected strings."""
        assert ProjectRole.SOLO_DEVELOPER.value == "Solo Developer"
        assert ProjectRole.LEAD_DEVELOPER.value == "Lead Developer"
        assert ProjectRole.CORE_CONTRIBUTOR.value == "Core Contributor"
        assert ProjectRole.MAJOR_CONTRIBUTOR.value == "Major Contributor"
        assert ProjectRole.CONTRIBUTOR.value == "Contributor"
        assert ProjectRole.MINOR_CONTRIBUTOR.value == "Minor Contributor"

    def test_role_priorities_are_unique(self) -> None:
        """Test that each role has a unique priority level."""
        priorities = [meta.display_priority for meta in ROLE_METADATA.values()]
        assert len(priorities) == len(set(priorities))


class TestRoleHelperFunctions:
    """Tests for role helper functions."""

    def test_get_role_description_with_enum(self) -> None:
        """Test getting description from ProjectRole enum."""
        desc = get_role_description(ProjectRole.CORE_CONTRIBUTOR)
        assert "contributor" in desc.lower()
        assert len(desc) > 0

    def test_get_role_description_with_string(self) -> None:
        """Test getting description from role string."""
        desc = get_role_description("Solo Developer")
        assert "sole" in desc.lower() or "only" in desc.lower()

    def test_get_role_description_unknown_role(self) -> None:
        """Test getting description for unknown role returns default."""
        desc = get_role_description("Unknown Role")
        assert desc == "Unknown role"

    def test_get_role_priority_with_enum(self) -> None:
        """Test getting priority from ProjectRole enum."""
        priority = get_role_priority(ProjectRole.SOLO_DEVELOPER)
        assert priority == 1  # Should be highest priority

    def test_get_role_priority_with_string(self) -> None:
        """Test getting priority from role string."""
        priority = get_role_priority("Minor Contributor")
        assert priority == 9  # Should be lowest priority

    def test_get_role_priority_unknown_role(self) -> None:
        """Test getting priority for unknown role returns default."""
        priority = get_role_priority("Unknown Role")
        assert priority == 99
