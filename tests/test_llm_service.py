from __future__ import annotations

import pytest

from capstone_project_team_5.services.llm_providers import (
    GeminiProvider,
    LLMError,
    LLMProvider,
)
from capstone_project_team_5.services.llm_service import LLMService


class MockProvider(LLMProvider):
    """Mock provider for testing LLMService."""

    def __init__(self) -> None:
        self.last_prompt: str | None = None
        self.last_config: dict | None = None
        self.response = "Mock LLM response"

    def send_prompt(self, prompt: str, config: dict) -> str:
        self.last_prompt = prompt
        self.last_config = config
        return self.response


def test_llm_service_initialization_with_custom_provider() -> None:
    """Test service initialization with a custom provider."""
    mock_provider = MockProvider()
    service = LLMService(provider=mock_provider)

    assert service.provider is mock_provider


def test_llm_service_initialization_with_default_gemini_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that Gemini is used as default provider when none specified."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("LLM_PROVIDER", "gemini")

    class _FakeClient:
        def __init__(self, api_key: str) -> None:
            pass

    import google.genai as _genai

    monkeypatch.setattr(_genai, "Client", _FakeClient, raising=True)

    service = LLMService()
    assert isinstance(service.provider, GeminiProvider)


def test_llm_service_initialization_with_unknown_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that initialization fails with unknown provider name."""
    monkeypatch.setenv("LLM_PROVIDER", "unknown_provider")

    with pytest.raises(LLMError, match="Unknown LLM provider: unknown_provider"):
        LLMService()


def test_llm_service_build_prompt() -> None:
    """Test prompt building with system instructions and user content."""
    mock_provider = MockProvider()
    service = LLMService(provider=mock_provider)

    system_instructions = "You are a helpful assistant."
    user_content = "What is Python?"

    prompt = service.build_prompt(system_instructions, user_content)

    expected = "System instruction:\nYou are a helpful assistant.\n\nUser content:\nWhat is Python?"
    assert prompt == expected


def test_llm_service_generate_llm_response_with_default_parameters() -> None:
    """Test response generation with default parameters."""
    mock_provider = MockProvider()
    mock_provider.response = "Python is a programming language"
    service = LLMService(provider=mock_provider)

    response = service.generate_llm_response(
        system_instructions="Answer concisely.",
        user_content="What is Python?",
    )

    assert response == "Python is a programming language"
    assert mock_provider.last_prompt is not None
    assert "Answer concisely." in mock_provider.last_prompt
    assert "What is Python?" in mock_provider.last_prompt
    assert mock_provider.last_config == {"temperature": 0.7}


def test_llm_service_generate_llm_response_with_custom_parameters() -> None:
    """Test response generation with custom temperature, max_tokens, and seed."""
    mock_provider = MockProvider()
    mock_provider.response = "Detailed explanation"
    service = LLMService(provider=mock_provider)

    response = service.generate_llm_response(
        system_instructions="Explain in detail.",
        user_content="How does Python work?",
        temperature=0.3,
        max_tokens=500,
        seed=42,
    )

    assert response == "Detailed explanation"
    assert mock_provider.last_config == {
        "temperature": 0.3,
        "max_tokens": 500,
        "seed": 42,
    }


def test_llm_service_generate_llm_response_with_temperature_zero() -> None:
    """Test response generation with temperature=0.0 (deterministic)."""
    mock_provider = MockProvider()
    service = LLMService(provider=mock_provider)

    service.generate_llm_response(
        system_instructions="Test",
        user_content="Test",
        temperature=0.0,
    )
    assert mock_provider.last_config["temperature"] == 0.0


def test_llm_service_generate_llm_response_with_temperature_max() -> None:
    """Test response generation with temperature=2.0 (maximum randomness)."""
    mock_provider = MockProvider()
    service = LLMService(provider=mock_provider)

    service.generate_llm_response(
        system_instructions="Test",
        user_content="Test",
        temperature=2.0,
    )
    assert mock_provider.last_config["temperature"] == 2.0


def test_llm_service_generate_llm_response_passes_prompt_correctly() -> None:
    """Test that the generated prompt is correctly passed to the provider."""
    mock_provider = MockProvider()
    service = LLMService(provider=mock_provider)

    service.generate_llm_response(
        system_instructions="Be helpful",
        user_content="What is 2+2?",
    )

    assert mock_provider.last_prompt is not None
    assert "System instruction:\nBe helpful" in mock_provider.last_prompt
    assert "User content:\nWhat is 2+2?" in mock_provider.last_prompt


def test_llm_service_generate_llm_response_integration_with_gemini(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test end-to-end integration with mocked Gemini provider."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "gemini-test")

    class _FakeResponse:
        def __init__(self, text: str) -> None:
            self.text = text

    class _FakeModels:
        def generate_content(self, *, model: str, contents: str, config: dict) -> _FakeResponse:
            # Verify the prompt structure
            assert "System instruction:" in contents
            assert "User content:" in contents
            # Verify config has Gemini-specific mapping
            assert "max_output_tokens" in config
            return _FakeResponse("Integration test response")

    class _FakeClient:
        def __init__(self, api_key: str) -> None:
            self.models = _FakeModels()

    import google.genai as _genai

    monkeypatch.setattr(_genai, "Client", _FakeClient, raising=True)

    service = LLMService()  # Uses default Gemini provider
    response = service.generate_llm_response(
        system_instructions="You are a test assistant.",
        user_content="Generate a test response.",
        temperature=0.5,
        max_tokens=100,
    )

    assert response == "Integration test response"


def test_extract_json_from_plain_json() -> None:
    """Test extracting JSON from a plain JSON string."""
    response = '{"tools": ["Docker", "PyTest"], "practices": ["TDD"]}'
    result = LLMService.extract_json_from_response(response)
    assert result == {"tools": ["Docker", "PyTest"], "practices": ["TDD"]}


def test_extract_json_from_markdown_code_block() -> None:
    """Test extracting JSON from markdown code block."""
    response = """```json
{"tools": ["Git", "Ruff"], "practices": ["Version Control"]}
```"""
    result = LLMService.extract_json_from_response(response)
    assert result == {"tools": ["Git", "Ruff"], "practices": ["Version Control"]}


def test_extract_json_from_markdown_without_language() -> None:
    """Test extracting JSON from markdown code block without language identifier."""
    response = """```
{"tools": ["Docker"], "practices": ["Testing"]}
```"""
    result = LLMService.extract_json_from_response(response)
    assert result == {"tools": ["Docker"], "practices": ["Testing"]}


def test_extract_json_raises_error_on_invalid_json() -> None:
    """Test that invalid JSON raises LLMError."""
    response = '{"tools": ["Docker", "practices": ["TDD"]}'  # Missing bracket
    with pytest.raises(LLMError, match="Failed to parse JSON"):
        LLMService.extract_json_from_response(response)


def test_extract_json_handles_array_at_root() -> None:
    """Test extracting JSON arrays at root level."""
    response = '["tool1", "tool2", "tool3"]'
    result = LLMService.extract_json_from_response(response)
    assert result == ["tool1", "tool2", "tool3"]


def test_extract_json_with_surrounding_text() -> None:
    """Test extracting JSON when surrounded by explanatory text."""
    response = 'Based on analysis: {"tools": ["SQL"], "practices": ["Testing"]} as shown'
    result = LLMService.extract_json_from_response(response)
    assert result == {"tools": ["SQL"], "practices": ["Testing"]}


def test_from_model_preferences_returns_gemini_for_gemini_preference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test from_model_preferences creates Gemini provider for Gemini preference."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    class _FakeClient:
        def __init__(self, api_key: str) -> None:
            pass

    import google.genai as _genai

    monkeypatch.setattr(_genai, "Client", _FakeClient, raising=True)

    service = LLMService.from_model_preferences(["Gemini (Google)", "GPT-4 (OpenAI)"])
    assert isinstance(service.provider, GeminiProvider)


def test_from_model_preferences_returns_default_for_empty_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test from_model_preferences falls back to default for empty preferences."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("LLM_PROVIDER", "gemini")

    class _FakeClient:
        def __init__(self, api_key: str) -> None:
            pass

    import google.genai as _genai

    monkeypatch.setattr(_genai, "Client", _FakeClient, raising=True)

    service = LLMService.from_model_preferences([])
    # Should use default provider (Gemini from env)
    assert isinstance(service.provider, GeminiProvider)
