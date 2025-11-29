from unittest.mock import patch

from capstone_project_team_5.consent_tool import ConsentTool


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
