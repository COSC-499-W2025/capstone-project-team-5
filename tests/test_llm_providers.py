from __future__ import annotations

import pytest

from capstone_project_team_5.services.llm_providers import (
    GeminiProvider,
    LLMError,
    LLMProvider,
    OpenAIProvider,
)


class MockLLMProvider(LLMProvider):
    """Mock provider for testing abstract base class."""

    def send_prompt(self, prompt: str, config: dict) -> str:
        return f"Mock response to: {prompt}"


def test_generate_llm_config_with_all_parameters() -> None:
    """Test config generation with all parameters set."""
    provider = MockLLMProvider()
    config = provider.generate_llm_config(temperature=0.5, max_tokens=100, seed=42)

    assert config == {"temperature": 0.5, "max_tokens": 100, "seed": 42}


def test_generate_llm_config_with_only_temperature() -> None:
    """Test config generation with only temperature set."""
    provider = MockLLMProvider()
    config = provider.generate_llm_config(temperature=0.7, max_tokens=None, seed=None)

    assert config == {"temperature": 0.7}
    assert "max_tokens" not in config
    assert "seed" not in config


def test_generate_llm_config_with_only_max_tokens() -> None:
    """Test config generation with only max_tokens set."""
    provider = MockLLMProvider()
    config = provider.generate_llm_config(temperature=None, max_tokens=500, seed=None)

    assert config == {"max_tokens": 500}
    assert "temperature" not in config
    assert "seed" not in config


def test_generate_llm_config_with_only_seed() -> None:
    """Test config generation with only seed set."""
    provider = MockLLMProvider()
    config = provider.generate_llm_config(temperature=None, max_tokens=None, seed=42)

    assert config == {"seed": 42}
    assert "temperature" not in config
    assert "max_tokens" not in config


def test_generate_llm_config_with_no_parameters() -> None:
    """Test config generation with all parameters as None."""
    provider = MockLLMProvider()
    config = provider.generate_llm_config(temperature=None, max_tokens=None, seed=None)

    assert config == {}


def test_gemini_initialization_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test successful initialization with API key."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-api-key-123")
    monkeypatch.setenv("LLM_MODEL", "gemini-2.0-flash-exp")

    # Mock the genai.Client to prevent actual API calls
    class _FakeClient:
        def __init__(self, api_key: str) -> None:
            self.api_key = api_key

    import google.genai as _genai

    monkeypatch.setattr(_genai, "Client", _FakeClient, raising=True)

    provider = GeminiProvider()
    assert provider.api_key == "test-api-key-123"
    assert provider.model == "gemini-2.0-flash-exp"


def test_gemini_initialization_missing_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test initialization fails without API key."""
    # Ensure GEMINI_API_KEY is not set
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(LLMError, match="Missing GEMINI_API_KEY environment variable"):
        GeminiProvider()


def test_gemini_initialization_default_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that default model is used when LLM_MODEL is not set."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("LLM_MODEL", raising=False)

    class _FakeClient:
        def __init__(self, api_key: str) -> None:
            pass

    import google.genai as _genai

    monkeypatch.setattr(_genai, "Client", _FakeClient, raising=True)

    provider = GeminiProvider()
    assert provider.model == "gemini-2.0-flash-exp"


def test_gemini_generate_llm_config_maps_max_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that max_tokens is mapped to max_output_tokens for Gemini."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    class _FakeClient:
        def __init__(self, api_key: str) -> None:
            pass

    import google.genai as _genai

    monkeypatch.setattr(_genai, "Client", _FakeClient, raising=True)

    provider = GeminiProvider()
    config = provider.generate_llm_config(temperature=0.8, max_tokens=200, seed=123)

    assert config == {
        "temperature": 0.8,
        "max_output_tokens": 200,
        "seed": 123,
    }
    assert "max_tokens" not in config


def test_gemini_send_prompt_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test successful prompt sending and response."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "gemini-test-model")

    class _FakeResponse:
        def __init__(self, text: str) -> None:
            self.text = text

    class _FakeModels:
        def generate_content(self, *, model: str, contents: str, config: dict) -> _FakeResponse:
            return _FakeResponse("  Test response from Gemini  ")

    class _FakeClient:
        def __init__(self, api_key: str) -> None:
            self.models = _FakeModels()

    import google.genai as _genai

    monkeypatch.setattr(_genai, "Client", _FakeClient, raising=True)

    provider = GeminiProvider()
    response = provider.send_prompt("Test prompt", {"temperature": 0.7, "max_output_tokens": 100})

    assert response == "Test response from Gemini"


def test_gemini_send_prompt_api_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that API failures are properly wrapped in LLMError."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    class _FakeModels:
        def generate_content(self, *, model: str, contents: str, config: dict) -> None:
            raise RuntimeError("API rate limit exceeded")

    class _FakeClient:
        def __init__(self, api_key: str) -> None:
            self.models = _FakeModels()

    import google.genai as _genai

    monkeypatch.setattr(_genai, "Client", _FakeClient, raising=True)

    provider = GeminiProvider()
    with pytest.raises(LLMError, match="Gemini API call failed.*rate limit"):
        provider.send_prompt("Test prompt", {})


def test_gemini_send_prompt_empty_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test handling of empty response from API."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    class _FakeResponse:
        def __init__(self) -> None:
            self.text = None

    class _FakeModels:
        def generate_content(self, *, model: str, contents: str, config: dict) -> _FakeResponse:
            return _FakeResponse()

    class _FakeClient:
        def __init__(self, api_key: str) -> None:
            self.models = _FakeModels()

    import google.genai as _genai

    monkeypatch.setattr(_genai, "Client", _FakeClient, raising=True)

    provider = GeminiProvider()

    with pytest.raises(LLMError, match="Gemini returned None response"):
        provider.send_prompt("Test prompt", {})


# OpenAI Provider Tests


def test_openai_initialization_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test successful initialization with API key."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-123")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o-mini")

    # Mock the OpenAI client to prevent actual API calls
    class _FakeClient:
        def __init__(self, api_key: str) -> None:
            self.api_key = api_key

    import openai

    monkeypatch.setattr(openai, "OpenAI", _FakeClient, raising=True)

    provider = OpenAIProvider()
    assert provider.api_key == "test-api-key-123"
    assert provider.model == "gpt-4o-mini"


def test_openai_initialization_missing_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test initialization fails without API key."""
    # Ensure OPENAI_API_KEY is not set
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(LLMError, match="Missing OPENAI_API_KEY environment variable"):
        OpenAIProvider()


def test_openai_initialization_default_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that default model is used when LLM_MODEL is not set."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("LLM_MODEL", raising=False)

    class _FakeClient:
        def __init__(self, api_key: str) -> None:
            pass

    import openai

    monkeypatch.setattr(openai, "OpenAI", _FakeClient, raising=True)

    provider = OpenAIProvider()
    assert provider.model == "gpt-4o-mini"


def test_openai_send_prompt_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test successful prompt sending and response."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o-mini")

    class _FakeMessage:
        def __init__(self, content: str) -> None:
            self.content = content

    class _FakeChoice:
        def __init__(self, message: _FakeMessage) -> None:
            self.message = message
            self.finish_reason = "stop"

    class _FakeResponse:
        def __init__(self, choices: list[_FakeChoice]) -> None:
            self.choices = choices

    class _FakeCompletions:
        def create(self, *, model: str, messages: list[dict], **kwargs: dict) -> _FakeResponse:
            return _FakeResponse([_FakeChoice(_FakeMessage("  Test response from OpenAI  "))])

    class _FakeChat:
        def __init__(self) -> None:
            self.completions = _FakeCompletions()

    class _FakeClient:
        def __init__(self, api_key: str) -> None:
            self.chat = _FakeChat()

    import openai

    monkeypatch.setattr(openai, "OpenAI", _FakeClient, raising=True)

    provider = OpenAIProvider()
    response = provider.send_prompt("Test prompt", {"temperature": 0.7, "max_tokens": 100})

    assert response == "Test response from OpenAI"


def test_openai_send_prompt_api_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that API failures are properly wrapped in LLMError."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class _FakeCompletions:
        def create(self, *, model: str, messages: list[dict], **kwargs: dict) -> None:
            raise RuntimeError("API rate limit exceeded")

    class _FakeChat:
        def __init__(self) -> None:
            self.completions = _FakeCompletions()

    class _FakeClient:
        def __init__(self, api_key: str) -> None:
            self.chat = _FakeChat()

    import openai

    monkeypatch.setattr(openai, "OpenAI", _FakeClient, raising=True)

    provider = OpenAIProvider()
    with pytest.raises(LLMError, match="OpenAI API call failed.*rate limit"):
        provider.send_prompt("Test prompt", {})


def test_openai_send_prompt_empty_choices(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test handling of empty choices list from API."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class _FakeResponse:
        def __init__(self) -> None:
            self.choices = []

    class _FakeCompletions:
        def create(self, *, model: str, messages: list[dict], **kwargs: dict) -> _FakeResponse:
            return _FakeResponse()

    class _FakeChat:
        def __init__(self) -> None:
            self.completions = _FakeCompletions()

    class _FakeClient:
        def __init__(self, api_key: str) -> None:
            self.chat = _FakeChat()

    import openai

    monkeypatch.setattr(openai, "OpenAI", _FakeClient, raising=True)

    provider = OpenAIProvider()

    with pytest.raises(LLMError, match="OpenAI returned empty choices list"):
        provider.send_prompt("Test prompt", {})


def test_openai_send_prompt_none_content(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test handling of None content in response."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class _FakeMessage:
        def __init__(self) -> None:
            self.content = None

    class _FakeChoice:
        def __init__(self) -> None:
            self.message = _FakeMessage()
            self.finish_reason = "length"

    class _FakeResponse:
        def __init__(self) -> None:
            self.choices = [_FakeChoice()]

    class _FakeCompletions:
        def create(self, *, model: str, messages: list[dict], **kwargs: dict) -> _FakeResponse:
            return _FakeResponse()

    class _FakeChat:
        def __init__(self) -> None:
            self.completions = _FakeCompletions()

    class _FakeClient:
        def __init__(self, api_key: str) -> None:
            self.chat = _FakeChat()

    import openai

    monkeypatch.setattr(openai, "OpenAI", _FakeClient, raising=True)

    provider = OpenAIProvider()

    with pytest.raises(LLMError, match="OpenAI returned None response"):
        provider.send_prompt("Test prompt", {})
