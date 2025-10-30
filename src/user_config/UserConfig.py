class UserConfig:
    """Represents the users global configuration preferences and permissions."""
    def __init__(
            self,
            consent_given: bool = False,
            use_external_services: bool = False,
            external_services: dict | None = None,
            default_ignore_patterns: list[str] | None = None
    ):
        self.consent_given = consent_given
        self.use_external_services = use_external_services
        self.external_services = external_services or {}
        self.default_ignore_patterns = default_ignore_patterns or []

    def to_dict(self):
        """Returns user configurations as a dictionary."""
        return {
            "consent_given": self.consent_given,
            "use_external_services": self.use_external_services,
            "external_services": self.external_services,
            "default_ignore_patterns": self.default_ignore_patterns
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserConfig":
        """Returns a UserConfig object from a dictionary."""
        return cls(
            consent_given = data.get("consent_given", False),
            use_external_services = data.get("use_external_services", False),
            external_services = data.get("external_services", None),
            default_ignore_patterns = data.get("default_ignore_patterns", None)
        )