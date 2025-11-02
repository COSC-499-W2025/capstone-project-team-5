from __future__ import annotations

import os

from capstone_project_team_5.services.llm_providers import (
    GeminiProvider,
    LLMProvider,
)

"""LLM service with multi-provider support. (Gemini, OpenAI, Anthropic, etc.)"""


class LLMService:
    def __init__(self, provider: LLMProvider | None = None) -> None:
        """Initialize LLM service with a specific provider.
        Args:
            provider: LLM provider instance
        """
        self.provider = provider or LLMService._get_default_llm_provider_from_env()

    def _get_default_llm_provider_from_env() -> LLMProvider:
        """Get the configured LLM provider.

        Returns:
            An instance of the configured LLM provider.
        """
        provider_name = os.environ.get("LLM_PROVIDER", "gemini").lower()

        if provider_name == "gemini":
            return GeminiProvider()
        # Future providers:
        # elif provider_name == "openai":
        #     return OpenAIProvider()
        else:
            raise RuntimeError(f"Unknown LLM provider: {provider_name}.")

    def build_prompt(self, system_instructions: str, user_content: str) -> str:
        """Construct a full prompt with system and user parts.

        Args:
            system_instructions: System-level instructions
            user_content: User-provided content

        Returns:
            The complete formatted prompt.
        """
        return f"System instruction:\n{system_instructions}\n\nUser content:\n{user_content}"

    def generate_llm_response(
        self,
        system_instructions: str,
        user_content: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        seed: int | None = None,
    ) -> str:
        """Build a prompt and send it to the LLM in one step.

        Args:
            system_instructions: System-level instructions.
            user_content: User content.
            temperature: Controls randomness (0.0-2.0). Lower = more deterministic.
            max_tokens: Maximum response length. None = provider default.
            seed: Random seed for reproducibility (if supported by provider).
            **kwargs: Additional provider-specific options.

        Returns:
            The text response from the LLM.
        """
        prompt = self.build_prompt(system_instructions, user_content)
        config = self.provider.generate_llm_config(temperature, max_tokens, seed)
        return self.provider.send_prompt(prompt, config)
