import pytest
from src.user_config.UserConfig import UserConfig

def test_default_user_config():
    config = UserConfig()
    assert config.consent_given is False
    assert config.use_external_services is False
    assert config.external_services == {}
    assert config.default_ignore_patterns == []

def test_custom_user_config():
    config = UserConfig(
        consent_given=True,
        use_external_services=True,
        external_services={"openai": {"allowed": True}},
        default_ignore_patterns=["*.log", "*.env"]
    )
    assert config.consent_given is True
    assert config.use_external_services is True
    assert config.external_services == {"openai": {"allowed": True}}
    assert config.default_ignore_patterns == ["*.log", "*.env"]

def test_to_dict():
    config = UserConfig(
        consent_given=True,
        use_external_services=True,
        external_services={"openai": {"allowed": True}},
        default_ignore_patterns=["*.log", "*.env"]
    )
    data = config.to_dict()
    assert data.get("consent_given") is True
    assert data.get("use_external_services") is True
    assert data.get("external_services") == {"openai": {"allowed": True}}
    assert data.get("default_ignore_patterns") == ["*.log", "*.env"]

def test_from_dict():
    data = {
        "consent_given": True,
        "use_external_services": True,
        "external_services": {"openai": {"allowed": True}},
        "default_ignore_patterns": ["*.log", "*.env"]
    }
    config = UserConfig.from_dict(data)
    assert config.consent_given is True
    assert config.use_external_services is True
    assert config.external_services == {"openai": {"allowed": True}}
    assert config.default_ignore_patterns == ["*.log", "*.env"]

def test_round_trip_dict_conversion():
    original = UserConfig(
        consent_given=True,
        use_external_services=True,
        external_services={"openai": {"allowed": True}},
        default_ignore_patterns=["*.log"]
    )

    recreated = UserConfig.from_dict(original.to_dict())
    assert recreated.__dict__ == original.__dict__
