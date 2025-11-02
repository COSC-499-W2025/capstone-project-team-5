from __future__ import annotations

import os
from abc import ABC, abstractmethod

from dotenv import load_dotenv

"""LLM provider implementations."""

# Load environment variables for LLM API keys (GEMINI_API_KEY, LLM_MODEL, etc.)
load_dotenv()


class LLMError(RuntimeError):
    """Raised when LLM service cannot be used or fails."""


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def generate_llm_config(
        self,
        temperature: float,
        max_tokens: int | None,
        seed: int | None,
    ) -> dict:
        """Generate llm configs

        Args:
            temperature: Controls randomness
            max_tokens: Maximum response length
            seed: Random seed for reproducibility

        Returns:
            Configuration dictionary with common parameters
        """
        config = {}

        if temperature is not None:
            config["temperature"] = temperature
        if max_tokens is not None:
            config["max_tokens"] = max_tokens
        if seed is not None:
            config["seed"] = seed

        return config

    @abstractmethod
    def send_prompt(self, prompt: str, config: dict) -> str:
        """Send a prompt to the LLM and return the text response.

        Args:
            prompt: The full prompt string to send to the LLM.
            config: Configuration dictionary for the LLM request.

        Returns:
            The text response from the LLM.
        """


class GeminiProvider(LLMProvider):
    """Gemini implementation."""

    def __init__(self) -> None:
        """Initialize Gemini provider with API key from environment.

        Note: Environment variables are loaded via load_dotenv() at package initialization.
        """
        from google import genai

        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise LLMError("Missing GEMINI_API_KEY environment variable")

        self.model = os.environ.get("LLM_MODEL", "gemini-2.0-flash-exp")
        self.client = genai.Client(api_key=self.api_key)

    def generate_llm_config(
        self,
        temperature: float,
        max_tokens: int | None,
        seed: int | None,
    ) -> dict:
        """Generate Gemini-specific configuration dictionary."""
        config = super().generate_llm_config(temperature, max_tokens, seed)

        # Map common 'max_tokens' to Gemini's 'max_output_tokens'
        if "max_tokens" in config:
            config["max_output_tokens"] = config.pop("max_tokens")

        return config

    def send_prompt(self, prompt: str, config: dict) -> str:
        """Send prompt to Gemini and return response text.

        Args:
            prompt: The full prompt string.
            config: Configuration dictionary for the Gemini API.

        Returns:
            The response text from Gemini.
        """
        try:
            response = self.client.models.generate_content(
                model=self.model, contents=prompt, config=config
            )
            return (response.text or "").strip()
        except Exception as e:
            raise LLMError(f"Gemini API call failed: {e}") from e
