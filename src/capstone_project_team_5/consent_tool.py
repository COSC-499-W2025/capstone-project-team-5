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
        default_ignore_patterns: List of patterns to ignore during file analysis.
    """

    # Available external services for integration
    AVAILABLE_EXTERNAL_SERVICES: list[str] = [
        "GitHub API",
        "LinkedIn API",
        "OpenAI/GPT",
        "Google Cloud Services",
        "AWS Services",
        "Microsoft Azure",
    ]

    def __init__(self) -> None:
        """Initialize the ConsentTool with default consent text and configuration."""
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
        then records the configuration.

        Returns:
            True if user agrees to main consent, False otherwise.
        """
        main_consent_given = self.get_user_consent(
            self.consent_text, self.title, ["Yes I agree", "No, Cancel"]
        )

        if main_consent_given:
            self.consent_given = True
            # If user agrees to main consent, request external services consent
            self.get_external_services_consent()
            # Set default ignore patterns
            self.default_ignore_patterns = self._get_default_ignore_patterns()
            # Record the collected configuration
            self.record_consent(self._build_config())
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
                self.external_services = {service: True for service in selected_services}
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

    def record_consent(self, user_config: dict[str, Any]) -> None:
        """Record user consent and configuration data.

        Args:
            user_config: Dictionary containing UserConfig-compatible data with keys:
                - consent_given: bool
                - use_external_services: bool
                - external_services: dict
                - default_ignore_patterns: list[str]
        """
        with get_session() as session:
            session.add(
                ConsentRecord(
                    consent_given=user_config["consent_given"],
                    use_external_services=user_config["use_external_services"],
                    external_services=user_config["external_services"],
                    default_ignore_patterns=user_config["default_ignore_patterns"],
                )
            )


if __name__ == "__main__":
    consent_tool = ConsentTool()
    consent_tool.generate_consent_form()
