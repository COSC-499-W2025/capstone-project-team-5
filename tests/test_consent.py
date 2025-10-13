from capstone_project_team_5.consent_tool import ConsentTool


def test_consent_tool_initialization() -> None:
    """Test that ConsentTool initializes with correct default values."""
    consent_tool = ConsentTool()
    assert consent_tool.consent_given is False
    assert consent_tool.use_external_services is False
    assert consent_tool.external_services == {}
    assert consent_tool.title == "Consent Form"


def test_consent_tool_build_config() -> None:
    """Test that _build_config_ returns correct configuration dictionary."""
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
