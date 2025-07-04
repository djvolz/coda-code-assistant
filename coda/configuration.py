"""Configuration management for Coda."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


@dataclass
class CodaConfig:
    """Main configuration class for Coda."""

    # Default provider
    default_provider: str = "oci_genai"

    # Provider configurations
    providers: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Session settings
    session: dict[str, Any] = field(
        default_factory=lambda: {
            "history_file": "~/.local/share/coda/history",
            "max_history": 1000,
            "autosave": True,
        }
    )

    # UI settings
    ui: dict[str, Any] = field(
        default_factory=lambda: {
            "theme": "default",
            "show_model_info": True,
            "show_token_usage": False,
        }
    )

    # Debug settings
    debug: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CodaConfig":
        """Create config from dictionary."""
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "default_provider": self.default_provider,
            "providers": self.providers,
            "session": self.session,
            "ui": self.ui,
            "debug": self.debug,
        }

    def merge(self, other: dict[str, Any]) -> None:
        """Merge another config dict into this one."""
        if "default_provider" in other:
            self.default_provider = other["default_provider"]

        if "providers" in other:
            for provider, config in other["providers"].items():
                if provider not in self.providers:
                    self.providers[provider] = {}
                self.providers[provider].update(config)

        if "session" in other:
            self.session.update(other["session"])

        if "ui" in other:
            self.ui.update(other["ui"])

        if "debug" in other:
            self.debug = other["debug"]


class ConfigManager:
    """Manages configuration loading from multiple sources."""

    def __init__(self):
        """Initialize config manager."""
        self.config = CodaConfig()
        self._load_all_configs()

    def _get_config_paths(self) -> list[Path]:
        """Get configuration file paths in priority order (lowest to highest)."""
        paths = []

        # System config (lowest priority)
        if os.name != "nt":  # Unix-like systems
            paths.append(Path("/etc/coda/config.toml"))

        # User config
        config_home = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
        user_config = Path(config_home) / "coda" / "config.toml"
        paths.append(user_config)

        # Project config (highest priority)
        project_config = Path(".coda") / "config.toml"
        if project_config.exists():
            paths.append(project_config)

        return paths

    def _load_config_file(self, path: Path) -> dict[str, Any] | None:
        """Load a single config file."""
        if not path.exists() or not tomllib:
            return None

        try:
            with open(path, "rb") as f:
                return tomllib.load(f)
        except Exception:
            return None

    def _load_all_configs(self) -> None:
        """Load all config files and merge them."""
        # Start with defaults
        self.config = CodaConfig()

        # Load and merge config files
        for path in self._get_config_paths():
            config_data = self._load_config_file(path)
            if config_data:
                self.config.merge(config_data)

        # Apply environment variables (highest priority)
        self._apply_env_vars()

    def _apply_env_vars(self) -> None:
        """Apply environment variable overrides."""
        # Default provider
        if provider := os.environ.get("CODA_DEFAULT_PROVIDER"):
            self.config.default_provider = provider

        # Debug mode
        if os.environ.get("CODA_DEBUG", "").lower() in ("true", "1", "yes"):
            self.config.debug = True

        # Provider-specific env vars
        # OCI GenAI
        if compartment_id := os.environ.get("OCI_COMPARTMENT_ID"):
            if "oci_genai" not in self.config.providers:
                self.config.providers["oci_genai"] = {}
            self.config.providers["oci_genai"]["compartment_id"] = compartment_id

        # Future providers can add their env vars here
        # Example:
        # if api_key := os.environ.get("OPENAI_API_KEY"):
        #     if "openai" not in self.config.providers:
        #         self.config.providers["openai"] = {}
        #     self.config.providers["openai"]["api_key"] = api_key

    def get_provider_config(self, provider: str) -> dict[str, Any]:
        """Get configuration for a specific provider."""
        return self.config.providers.get(provider, {})

    def save_user_config(self) -> None:
        """Save current config to user config file."""
        if not tomllib:
            raise ImportError("toml library not available for saving config")

        config_home = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
        config_path = Path(config_home) / "coda" / "config.toml"

        # Create directory if needed
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # We need toml writer (tomli-w or toml)
        try:
            import tomli_w

            writer = tomli_w
        except ImportError:
            try:
                import toml

                writer = toml
            except ImportError:
                raise ImportError("No TOML writer available (install tomli-w or toml)") from None

        # Write config
        with open(config_path, "w") as f:
            writer.dump(self.config.to_dict(), f)


# Global config instance
_config_manager: ConfigManager | None = None


def get_config() -> CodaConfig:
    """Get the global configuration."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager.config


def get_provider_config(provider: str) -> dict[str, Any]:
    """Get configuration for a specific provider."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager.get_provider_config(provider)
