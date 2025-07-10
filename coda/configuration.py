"""Configuration management for Coda."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .constants import (
    DEFAULT_MAX_HISTORY,
    DEFAULT_PROVIDER,
    ENV_DEBUG,
    ENV_DEFAULT_PROVIDER,
    ENV_OCI_COMPARTMENT_ID,
    HISTORY_FILE_NAME,
    PROJECT_CONFIG_FILE,
    PROVIDER_OCI_GENAI,
    SYSTEM_CONFIG_PATH,
    THEME_DEFAULT,
    USER_CONFIG_PATH,
    get_data_dir,
)

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
    default_provider: str = DEFAULT_PROVIDER

    # Provider configurations
    providers: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Session settings
    session: dict[str, Any] = field(
        default_factory=lambda: {
            "history_file": str(get_data_dir() / HISTORY_FILE_NAME),
            "max_history": DEFAULT_MAX_HISTORY,
            "autosave": True,
        }
    )

    # UI settings
    ui: dict[str, Any] = field(
        default_factory=lambda: {
            "theme": THEME_DEFAULT,
            "show_model_info": True,
            "show_token_usage": False,
        }
    )

    # Debug settings
    debug: bool = False

    # Observability settings
    observability: dict[str, Any] = field(default_factory=dict)

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
            "observability": self.observability,
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

        if "observability" in other:
            self.observability.update(other["observability"])


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
            paths.append(SYSTEM_CONFIG_PATH)

        # User config
        paths.append(USER_CONFIG_PATH)

        # Project config (highest priority)
        project_config = Path(PROJECT_CONFIG_FILE)
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
        if provider := os.environ.get(ENV_DEFAULT_PROVIDER):
            self.config.default_provider = provider

        # Debug mode
        if os.environ.get(ENV_DEBUG, "").lower() in ("true", "1", "yes"):
            self.config.debug = True

        # Provider-specific env vars
        # OCI GenAI
        if compartment_id := os.environ.get(ENV_OCI_COMPARTMENT_ID):
            if PROVIDER_OCI_GENAI not in self.config.providers:
                self.config.providers[PROVIDER_OCI_GENAI] = {}
            self.config.providers[PROVIDER_OCI_GENAI]["compartment_id"] = compartment_id

        # Future providers can add their env vars here
        # Example:
        # if api_key := os.environ.get("OPENAI_API_KEY"):
        #     if "openai" not in self.config.providers:
        #         self.config.providers["openai"] = {}
        #     self.config.providers["openai"]["api_key"] = api_key

    def get_provider_config(self, provider: str) -> dict[str, Any]:
        """Get configuration for a specific provider."""
        return self.config.providers.get(provider, {})

    def get_bool(self, key: str, default: bool = False, env_var: str = None) -> bool:
        """Get a boolean configuration value.

        Args:
            key: Configuration key (dot notation supported, e.g. 'observability.enabled')
            default: Default value if key not found
            env_var: Environment variable to check first

        Returns:
            Boolean configuration value
        """
        # Check environment variable first
        if env_var and env_var in os.environ:
            value = os.environ[env_var].lower()
            return value in ("true", "1", "yes", "on")

        # Navigate through nested dict using dot notation
        value = self._get_nested_value(key, default)

        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        else:
            return bool(value)

    def get_int(self, key: str, default: int = 0, env_var: str = None) -> int:
        """Get an integer configuration value.

        Args:
            key: Configuration key (dot notation supported)
            default: Default value if key not found
            env_var: Environment variable to check first

        Returns:
            Integer configuration value
        """
        # Check environment variable first
        if env_var and env_var in os.environ:
            try:
                return int(os.environ[env_var])
            except ValueError:
                pass

        value = self._get_nested_value(key, default)

        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def get_float(self, key: str, default: float = 0.0, env_var: str = None) -> float:
        """Get a float configuration value.

        Args:
            key: Configuration key (dot notation supported)
            default: Default value if key not found
            env_var: Environment variable to check first

        Returns:
            Float configuration value
        """
        # Check environment variable first
        if env_var and env_var in os.environ:
            try:
                return float(os.environ[env_var])
            except ValueError:
                pass

        value = self._get_nested_value(key, default)

        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def get_string(self, key: str, default: str = "", env_var: str = None) -> str:
        """Get a string configuration value.

        Args:
            key: Configuration key (dot notation supported)
            default: Default value if key not found
            env_var: Environment variable to check first

        Returns:
            String configuration value
        """
        # Check environment variable first
        if env_var and env_var in os.environ:
            return os.environ[env_var]

        value = self._get_nested_value(key, default)
        return str(value)

    def get_config(self) -> dict[str, Any]:
        """Get the full configuration as a dictionary.

        Returns:
            Complete configuration dictionary
        """
        return self.config.to_dict()

    def _get_nested_value(self, key: str, default: Any = None) -> Any:
        """Get a value from nested configuration using dot notation.

        Args:
            key: Dot-separated key (e.g., 'observability.metrics.enabled')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split(".")
        value = self.config.to_dict()

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def save_user_config(self) -> None:
        """Save current config to user config file."""
        if not tomllib:
            raise ImportError("toml library not available for saving config")

        config_path = USER_CONFIG_PATH

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
        config_dict = self.config.to_dict()
        if hasattr(writer, "dumps"):
            # tomli_w pattern
            content = writer.dumps(config_dict)
            with open(config_path, "w") as f:
                f.write(content)
        else:
            # toml pattern
            with open(config_path, "w") as f:
                writer.dump(config_dict, f)


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


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def save_config() -> None:
    """Save the current configuration to user config file."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    _config_manager.save_user_config()
