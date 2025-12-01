"""Consent management module for Zip2Job application.

This module provides a consent tool that manages user permissions for:
- File and directory access
- External service integrations
- Data processing and storage
"""

from __future__ import annotations

from typing import Any

import easygui as eg

from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import ConsentRecord


class ConsentTool:
    """Manages user consent for file access and external service integration.

    The ConsentTool class handles the display of consent forms, collection of user
    agreements, and storage of consent decisions for the Zip2Job application.

    Attributes:
        title: Title displayed on the main consent form dialog.
        consent_text: Main consent form text explaining file access permissions.
        external_services_consent_text: Consent text for external service integration.
        consent_given: Whether main consent has been given.
        use_external_services: Whether external services consent has been given.
        external_services: Dictionary of external service configurations.
            Each service is stored as: {"service_name": {"allowed": True, ...other config}}
            LLM config stored as: {"llm": {"allowed": True, "model_preferences": [...]}}
        default_ignore_patterns: List of patterns to ignore during file analysis.
    """

    # Available external services for integration
    AVAILABLE_EXTERNAL_SERVICES: list[str] = [
        "GitHub API",
        "Gemini",
        "LinkedIn API",
        "OpenAI/GPT",
        "Google Cloud Services",
        "AWS Services",
        "Microsoft Azure",
    ]

    # Available AI models for LLM features
    AVAILABLE_AI_MODELS: list[str] = [
        "Gemini (Google)",
        "GPT-4 (OpenAI)",
        "GPT-3.5 (OpenAI)",
        "Claude (Anthropic)",
        "LLaMA (Meta)",
        "Mistral AI",
    ]

    # Common file extensions and directories to ignore
    COMMON_IGNORE_PATTERNS: list[str] = [
        # Version control
        ".git",
        ".svn",
        ".hg",
        # Dependencies
        "node_modules",
        "vendor",
        "packages",
        "bower_components",
        # Python environments
        "venv",
        ".venv",
        "env",
        ".env",
        "virtualenv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".nox",
        # IDEs
        ".idea",
        ".vscode",
        ".vs",
        # Build outputs
        "build",
        "dist",
        "out",
        "target",
        ".next",
        ".nuxt",
        ".gradle",
        # Caches
        ".cache",
        "coverage",
        ".nyc_output",
        # OS files
        ".DS_Store",
        "Thumbs.db",
        # Common media/binary
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".class",
        ".jar",
        ".war",
        ".ear",
        # Logs
        "*.log",
        "logs",
        # Temp files
        "tmp",
        "temp",
        ".tmp",
    ]

    def __init__(self, username: str | None = None) -> None:
        """Initialize the ConsentTool with default consent text and configuration.

        Args:
            username: Optional application-level username to scope consent records.
        """
        self.username: str | None = username
        self.title: str = "Consent Form"
        self.consent_text: str = """Thank you for using Zip2Job.
Before we begin, we ask your permission to access and analyze files in directories you choose.
Please review and agree to the following:

• Access only the directories / repositories you select
• Read supported files (code, docs, images, video)
• Extract metadata (timestamps, size, file type) and version history if available
• Compute metrics (word counts, commit frequency, media dimensions)
• Group files into projects and generate visualizations
• Store derived summaries / metadata locally
• Export summaries (PDF, HTML, Markdown)
• You may exclude files / folders at any time
• Raw file contents will not be uploaded or shared
• You may revoke permission or delete data at any time

⚠️ Risk: file names or metadata may appear in summaries.
If you decline, core features will not work.
Please choose "Yes I agree" to proceed or "No, Cancel" to exit."""

        self.external_services_consent_text: str = """
To enhance functionality, Zip2Job can integrate with external services.
Please review and agree to the following:
• Share derived summaries / metadata with selected services
• Services may store data according to their policies
• You may revoke permission or delete data at any time
Please choose "Yes I agree" to proceed or "No, Cancel" to exit."""

        # Configuration state matching UserConfig structure
        self.consent_given: bool = False
        self.use_external_services: bool = False
        self.external_services: dict[str, Any] = {}
        self.default_ignore_patterns: list[str] = []

    def get_user_consent(self, text: str, title: str, choices: list[str]) -> bool:
        """Display a consent dialog and record the user's decision.

        Args:
            text: Consent text to display.
            title: Title of the consent dialog.
            choices: List of button choices for the user.

        Returns:
            True if user agrees, False if user cancels.
        """
        choice = eg.buttonbox(text, title=title, choices=choices)

        if choice == "No, Cancel":
            return False

        return choice != "No, Cancel"

    def generate_consent_form(self) -> bool:
        """Generate and display the main consent form to the user.

        This method displays the primary consent form for file access. If the user
        agrees, it proceeds to request consent for external services integration,
        LLM preferences, and file ignore patterns, then records the configuration.

        Returns:
            True if user agrees to main consent, False otherwise.
        """
        main_consent_given = self.get_user_consent(
            self.consent_text, self.title, ["Yes I agree", "No, Cancel"]
        )

        if main_consent_given:
            self.consent_given = True
            # Configure file ignore patterns
            self.default_ignore_patterns = self._configure_ignore_patterns()
            # If user agrees to main consent, request external services consent
            self.get_external_services_consent()
            # Record the collected configuration
            self.record_consent(self._build_config(), username=self.username)
            return True

        self.consent_given = False
        eg.msgbox("You chose to cancel. Exiting the application.", title="Goodbye!")
        return False

    def get_external_services_consent(self) -> bool:
        """Request and process consent for external service integration.

        Returns:
            True if user agrees to external services, False otherwise.
        """
        consent_given = self.get_user_consent(
            self.external_services_consent_text,
            "External Services Consent",
            ["Yes I agree", "No, Cancel"],
        )

        if consent_given:
            self.use_external_services = True
            # Allow user to select which external services to enable
            selected_services = self._select_external_services()
            if selected_services:
                # Store services with 'allowed' property
                self.external_services = {
                    service: {"allowed": True} for service in selected_services
                }

                # Check if user wants to use LLM features
                if self._check_llm_in_services(selected_services):
                    self._configure_llm_preferences()

                eg.msgbox(
                    f"Thank you for agreeing. Selected services: {', '.join(selected_services)}",
                    title="Welcome!",
                )
            else:
                self.external_services = {}
                eg.msgbox(
                    "No services selected. Proceeding without external integrations.",
                    title="Welcome!",
                )
            return True

        self.use_external_services = False
        eg.msgbox(
            "You chose to cancel external services integration. Proceeding without it.",
            title="Notice",
        )
        return False

    def _select_external_services(self) -> list[str]:
        """Display a multi-choice dialog for selecting external services.

        Returns:
            List of selected service names.
        """
        msg = """Select the external services you would like to integrate with Zip2Job:

Note: Each service may have its own data policies and requirements.
You can select multiple services or none."""

        selected = eg.multchoicebox(
            msg=msg,
            title="Select External Services",
            choices=self.AVAILABLE_EXTERNAL_SERVICES,
        )

        # multchoicebox returns None if user cancels, or a list of selected items
        return selected if selected is not None else []

    def _check_llm_in_services(self, selected_services: list[str]) -> bool:
        """Check if any LLM service is selected.

        Args:
            selected_services: List of selected service names.

        Returns:
            True if any LLM service is in the selected services.
        """
        llm_services = {"Gemini", "OpenAI/GPT", "Claude"}
        return any(service in selected_services for service in llm_services)

    def _configure_llm_preferences(self) -> None:
        """Configure LLM model preferences with priority order."""
        msg = """Would you like to use AI/LLM features for enhanced analysis?

AI features include:
- Automated resume bullet point generation
- Project description enhancement
- Skill analysis and recommendations

Note: This requires API keys for the selected AI services."""

        use_llm = eg.buttonbox(
            msg,
            title="AI/LLM Features",
            choices=["Yes, configure AI", "No, skip AI features"],
        )

        if use_llm == "Yes, configure AI":
            # Store LLM configuration in external_services
            self._select_ai_model_preferences()
        else:
            eg.msgbox(
                "AI features disabled. You can enable them later in settings.",
                title="Notice",
            )

    def _select_ai_model_preferences(self) -> None:
        """Allow user to select and prioritize AI models."""
        msg = """Select your preferred AI models in order of preference.

The application will try models in the order you select them.
If the first model is unavailable, it will fall back to the next one.

Default: Gemini (Google) is pre-selected as the first choice."""

        # Pre-select Gemini as default
        selected = eg.multchoicebox(
            msg=msg,
            title="AI Model Preferences",
            choices=self.AVAILABLE_AI_MODELS,
            preselect=[0],  # Pre-select first item (Gemini)
        )

        if selected and len(selected) > 0:
            ai_model_preferences = selected

            # If more than one model selected, let user set priority
            if len(selected) > 1:
                ai_model_preferences = self._set_model_priority(selected)

            # Store AI config in external_services under "llm" key
            self.external_services["llm"] = {
                "allowed": True,
                "model_preferences": ai_model_preferences,
            }

            eg.msgbox(
                "AI models configured with priority order:\n\n"
                + "\n".join([f"{i + 1}. {model}" for i, model in enumerate(ai_model_preferences)]),
                title="AI Configuration Complete",
            )
        else:
            # Default to Gemini if nothing selected
            self.external_services["llm"] = {
                "allowed": True,
                "model_preferences": ["Gemini (Google)"],
            }
            eg.msgbox(
                "No models selected. Defaulting to Gemini (Google).",
                title="Default AI Model",
            )

    def _set_model_priority(self, selected_models: list[str]) -> list[str]:
        """Allow user to set priority order for selected AI models.

        Args:
            selected_models: List of selected AI model names.

        Returns:
            List of models in priority order.
        """
        msg = """Set the priority order for your AI models.

Select models one by one in your preferred order (highest priority first).
The application will try them in this order if one fails or is unavailable."""

        ordered_models: list[str] = []
        remaining = selected_models.copy()

        while remaining:
            if len(remaining) == 1:
                # Last item, just add it
                ordered_models.append(remaining[0])
                break

            choice = eg.choicebox(
                f"{msg}\n\nAlready selected ({len(ordered_models)}):\n"
                + "\n".join([f"  {i + 1}. {m}" for i, m in enumerate(ordered_models)])
                + f"\n\nSelect priority #{len(ordered_models) + 1}:",
                title=f"Priority Selection ({len(ordered_models) + 1}/{len(selected_models)})",
                choices=remaining,
            )

            if choice:
                ordered_models.append(choice)
                remaining.remove(choice)
            else:
                # User cancelled, keep remaining in original order
                ordered_models.extend(remaining)
                break

        return ordered_models

    def _configure_ignore_patterns(self) -> list[str]:
        """Configure file and directory ignore patterns.

        Returns:
            List of patterns to ignore during file analysis.
        """
        msg = """Select files and directories to IGNORE during analysis.

These patterns will be excluded from scanning:
- Version control directories (.git, .svn)
- Dependencies (node_modules, vendor)
- Build outputs (dist, build)
- Cache and temporary files

The default selections are recommended for most projects.
You can add custom patterns later."""

        # Pre-select all default patterns
        selected = eg.multchoicebox(
            msg=msg,
            title="Configure Ignore Patterns",
            choices=self.COMMON_IGNORE_PATTERNS,
            preselect=list(range(len(self.COMMON_IGNORE_PATTERNS))),  # Pre-select all
        )

        if selected:
            # Show option to add custom patterns
            add_custom = eg.buttonbox(
                "Would you like to add custom ignore patterns?",
                title="Custom Patterns",
                choices=["Yes, add custom", "No, continue"],
            )

            if add_custom == "Yes, add custom":
                custom_patterns = self._add_custom_ignore_patterns()
                selected.extend(custom_patterns)

            return selected
        else:
            # User cancelled, use minimal defaults
            return [".git", "node_modules", "__pycache__"]

    def _add_custom_ignore_patterns(self) -> list[str]:
        """Allow user to add custom ignore patterns.

        Returns:
            List of custom ignore patterns.
        """
        custom_patterns: list[str] = []

        while True:
            pattern = eg.enterbox(
                "Enter a custom ignore pattern (e.g., '*.tmp', 'my_folder', '*.bak'):\n\n"
                "Current custom patterns:\n"
                + (
                    "\n".join([f"  - {p}" for p in custom_patterns])
                    if custom_patterns
                    else "  (none)"
                ),
                title="Add Custom Ignore Pattern",
            )

            if pattern and pattern.strip():
                custom_patterns.append(pattern.strip())

                add_more = eg.buttonbox(
                    f"Pattern '{pattern.strip()}' added.\n\nAdd another pattern?",
                    title="Add More?",
                    choices=["Yes, add more", "No, done"],
                )

                if add_more != "Yes, add more":
                    break
            else:
                break

        return custom_patterns

    def _get_default_ignore_patterns(self) -> list[str]:
        """Get default file/folder patterns to ignore during file analysis.

        Returns:
            List of default ignore patterns (e.g., .git, node_modules).
        """
        return [".git", "node_modules", "__pycache__"]

    def _build_config(self) -> dict[str, Any]:
        """Build a configuration dictionary matching UserConfig.to_dict() format.

        Returns:
            Dictionary with consent_given, use_external_services, external_services,
            and default_ignore_patterns keys.
        """
        return {
            "consent_given": self.consent_given,
            "use_external_services": self.use_external_services,
            "external_services": self.external_services,
            "default_ignore_patterns": self.default_ignore_patterns,
        }

    def load_existing_consent(self) -> bool:
        """Load the most recent consent record for this user if it exists.

        Returns:
            True if a consent record was found and loaded, False otherwise.
        """
        from capstone_project_team_5.data.models import User

        with get_session() as session:
            user_id: int | None = None
            if self.username is not None and self.username.strip():
                user = session.query(User).filter(User.username == self.username.strip()).first()
                if user is not None:
                    user_id = user.id

            record: ConsentRecord | None = None

            # Prefer a consent record scoped to this user if one exists.
            if user_id is not None:
                record = (
                    session.query(ConsentRecord)
                    .filter(ConsentRecord.user_id == user_id)
                    .order_by(ConsentRecord.created_at.desc())
                    .first()
                )

            # Fall back to the most recent global (unscoped) consent record.
            if record is None:
                record = (
                    session.query(ConsentRecord)
                    .filter(ConsentRecord.user_id.is_(None))
                    .order_by(ConsentRecord.created_at.desc())
                    .first()
                )

            if record is None:
                return False

            self.consent_given = record.consent_given
            self.use_external_services = record.use_external_services
            self.external_services = record.external_services or {}
            self.default_ignore_patterns = record.default_ignore_patterns or []
            return True

    def record_consent(self, user_config: dict[str, Any], username: str | None = None) -> None:
        """Record user consent and configuration data.

        Args:
            user_config: Dictionary containing UserConfig-compatible data with keys:
                - consent_given: bool
                - use_external_services: bool
                - external_services: dict (with nested config like {"service": {"allowed": True}})
                - default_ignore_patterns: list[str]
        """
        from capstone_project_team_5.data.models import User

        with get_session() as session:
            user_id: int | None = None
            if username is not None and username.strip():
                user = session.query(User).filter(User.username == username.strip()).first()
                if user is not None:
                    user_id = user.id

            session.add(
                ConsentRecord(
                    user_id=user_id,
                    consent_given=user_config["consent_given"],
                    use_external_services=user_config["use_external_services"],
                    external_services=user_config["external_services"],
                    default_ignore_patterns=user_config["default_ignore_patterns"],
                )
            )


if __name__ == "__main__":
    consent_tool = ConsentTool()
    consent_tool.generate_consent_form()
