from __future__ import annotations

import os
from abc import ABC, abstractmethod

"""LLM provider implementations."""


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def send_prompt(self, prompt: str) -> str:
        """Send a prompt to the LLM and return the text response.

        Args:
            prompt: The full prompt string to send to the LLM.

        Returns:
            The text response from the LLM.
        """


class GeminiProvider(LLMProvider):
    """Gemini implementation."""

    def __init__(self) -> None:
        """Initialize Gemini provider with API key from environment."""
        from google import genai

        self.api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise RuntimeError("Missing GEMINI_API_KEY or GOOGLE_API_KEY environment variable")

        self.model = os.environ.get("LLM_MODEL", "gemini-2.0-flash-exp")
        self.client = genai.Client(api_key=self.api_key)

    def send_prompt(self, prompt: str) -> str:
        """Send prompt to Gemini and return response text.

        Args:
            prompt: The full prompt string.

        Returns:
            The response text from Gemini.
        """
        try:
            response = self.client.models.generate_content(model=self.model, contents=prompt)
            return (response.text or "").strip()
        except Exception as e:
            raise RuntimeError(f"Gemini API call failed: {e}") from e
