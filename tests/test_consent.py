from __future__ import annotations

from unittest.mock import patch

from capstone_project_team_5.consent_tool import ConsentTool
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import ConsentRecord, User


def test_consent_tool_initialization() -> None:
    """Test that ConsentTool initializes with correct default values."""
    consent_tool = ConsentTool()
    assert consent_tool.consent_given is False
    assert consent_tool.use_external_services is False
    assert consent_tool.external_services == {}
    assert consent_tool.title == "Consent Form"


def test_consent_tool_build_config() -> None:
    """Test that _build_config returns correct configuration dictionary."""
    consent_tool = ConsentTool()
    consent_tool.consent_given = True
    consent_tool.use_external_services = True
    consent_tool.external_services = {"test_service": "value"}
    consent_tool.default_ignore_patterns = [".git", "node_modules"]

    config = consent_tool._build_config()

    assert config["consent_given"] is True
    assert config["use_external_services"] is True
    assert config["external_services"] == {"test_service": "value"}
    assert config["default_ignore_patterns"] == [".git", "node_modules"]


def test_select_external_services_with_selections() -> None:
    """Test that _select_external_services returns selected services."""
    consent_tool = ConsentTool()

    # Mock multchoicebox to return selected services
    with patch("easygui.multchoicebox", return_value=["GitHub API", "OpenAI/GPT"]):
        selected = consent_tool._select_external_services()

    assert selected == ["GitHub API", "OpenAI/GPT"]


def test_select_external_services_with_no_selections() -> None:
    """Test that _select_external_services returns empty list when user cancels."""
    consent_tool = ConsentTool()

    # Mock multchoicebox to return None (user cancelled)
    with patch("easygui.multchoicebox", return_value=None):
        selected = consent_tool._select_external_services()

    assert selected == []


def test_get_external_services_consent_with_selections() -> None:
    """Test external services consent with user selecting services."""
    consent_tool = ConsentTool()

    # Mock the dialog responses
    with (
        patch("easygui.buttonbox", return_value="Yes I agree"),
        patch("easygui.multchoicebox", return_value=["GitHub API", "LinkedIn API"]),
        patch("easygui.msgbox"),
    ):
        result = consent_tool.get_external_services_consent()

    assert result is True
    assert consent_tool.use_external_services is True
    assert consent_tool.external_services == {
        "GitHub API": {"allowed": True},
        "LinkedIn API": {"allowed": True},
    }


def test_get_external_services_consent_no_selections() -> None:
    """Test external services consent when user selects no services."""
    consent_tool = ConsentTool()

    # Mock the dialog responses
    with (
        patch("easygui.buttonbox", return_value="Yes I agree"),
        patch("easygui.multchoicebox", return_value=[]),
        patch("easygui.msgbox"),
    ):
        result = consent_tool.get_external_services_consent()

    assert result is True
    assert consent_tool.use_external_services is True
    assert consent_tool.external_services == {}


def test_get_external_services_consent_declined() -> None:
    """Test external services consent when user declines."""
    consent_tool = ConsentTool()

    # Mock the dialog responses
    with patch("easygui.buttonbox", return_value="No, Cancel"), patch("easygui.msgbox"):
        result = consent_tool.get_external_services_consent()

    assert result is False
    assert consent_tool.use_external_services is False


def test_load_existing_consent_prefers_user_then_global() -> None:
    """load_existing_consent should prefer user-scoped consent, then global."""
    import uuid

    # Use unique usernames to avoid collision with other tests
    alice_username = f"alice-test-{uuid.uuid4().hex[:8]}"
    bob_username = f"bob-test-{uuid.uuid4().hex[:8]}"

    # Set up one global consent record and one user-specific consent record.
    with get_session() as session:
        global_consent = ConsentRecord(
            user_id=None,
            consent_given=True,
            use_external_services=False,
            external_services={"global": {"allowed": True}},
            default_ignore_patterns=[".git"],
        )
        user = User(username=alice_username, password_hash="dummy-hash")
        session.add(global_consent)
        session.add(user)

    # First, a tool for a user with no user-specific record should load global consent.
    tool_for_new_user = ConsentTool(username=bob_username)
    assert tool_for_new_user.load_existing_consent() is True
    assert tool_for_new_user.consent_given is True
    assert tool_for_new_user.external_services.get("global") == {"allowed": True}

    # Now add a user-specific consent for alice that differs from the global one.
    with get_session() as session:
        alice = session.query(User).filter(User.username == alice_username).first()
        assert alice is not None
        alice_consent = ConsentRecord(
            user_id=alice.id,
            consent_given=True,
            use_external_services=True,
            external_services={alice_username: {"allowed": True}},
            default_ignore_patterns=["node_modules"],
        )
        session.add(alice_consent)

    # Tool for alice should prefer her user-scoped record over the global one.
    tool_for_alice = ConsentTool(username=alice_username)
    assert tool_for_alice.load_existing_consent() is True
    assert tool_for_alice.consent_given is True
    assert tool_for_alice.use_external_services is True
    assert tool_for_alice.external_services.get(alice_username) == {"allowed": True}
