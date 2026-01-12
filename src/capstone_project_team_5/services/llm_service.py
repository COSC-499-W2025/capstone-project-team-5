from __future__ import annotations

import json
import os
import re

from capstone_project_team_5.services.llm_providers import (
    GeminiProvider,
    LLMError,
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

    @classmethod
    def from_model_preferences(cls, model_preferences: list[str]) -> LLMService:
        """Create an LLM service based on user's model preferences.

        Tries each model preference in order until one successfully initializes.

        Args:
            model_preferences: List of model names in priority order
                (e.g., ["Gemini (Google)", "GPT-4 (OpenAI)"]).

        Returns:
            LLMService instance configured with the first available provider.
        """
        if not model_preferences:
            return cls()

        # Map user-friendly model names to providers
        # Try each preference in order until one works
        for model_name in model_preferences:
            model_lower = model_name.lower()
            if "gemini" in model_lower:
                try:
                    return cls(provider=GeminiProvider())
                except LLMError:
                    continue
            # Future: add OpenAI, Claude, etc. providers here
            # elif "gpt" in model_lower or "openai" in model_lower:
            #     try:
            #         return cls(provider=OpenAIProvider())
            #     except LLMError:
            #         continue

        # Fallback to default if no preferred provider works
        return cls()

    @staticmethod
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
            raise LLMError(f"Unknown LLM provider: {provider_name}.")

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

        Returns:
            The text response from the LLM.
        """
        prompt = self.build_prompt(system_instructions, user_content)
        config = self.provider.generate_llm_config(temperature, max_tokens, seed)
        return self.provider.send_prompt(prompt, config)

    @staticmethod
    def extract_json_from_response(response: str) -> dict | list:
        """Extract and parse JSON from an LLM response.
        Args:
            response: Raw LLM response text

        Returns:
            Parsed JSON as a dictionary or list

        """
        text = response.strip()

        # First, try to parse the response as-is.
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Next, search for one or more fenced code blocks and try each in order.
        code_block_pattern = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL | re.IGNORECASE)
        candidates: list[str] = []

        for match in code_block_pattern.finditer(text):
            candidate = match.group(1).strip()
            if candidate:
                candidates.append(candidate)

        # Fallback: grab the first JSON-looking substring if no code block worked.
        if not candidates:
            inline_match = re.search(r"[\{\[].*[\}\]]", text, re.DOTALL)
            if inline_match:
                candidates.append(inline_match.group(0).strip())

        for candidate in candidates:
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue

        raise LLMError("Failed to parse JSON from LLM response: no valid JSON found.")
