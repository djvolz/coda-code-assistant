"""Configuration service for Coda applications.

This service integrates the base config and theme modules to provide
a complete configuration solution for Coda applications.
"""

import os
from pathlib import Path
from typing import Any

from coda.base.config import Config
from coda.base.theme import ThemeManager

# Global instance
_config_service = None


class AppConfig:
    """Application-specific configuration service for Coda.

    This integrates the base config module with themes and provides
    Coda-specific defaults and behaviors.
    """

    def __init__(self, config_path: Path | None = None):
        """Initialize configuration service.

        Args:
            config_path: Path to config file. If None, uses XDG standard locations.
        """
        # Initialize base config manager
        if config_path is None:
            config_path = self._get_default_config_path()

        self.config_path = config_path  # Store for save()

        # Always create config without specifying the file
        # This ensures defaults are loaded first, then user config is layered on top
        self.config = Config(app_name="coda")

        # If user config exists, load it as an additional layer
        if config_path.exists():
            from coda.base.config.models import ConfigSource

            # Parse TOML directly
            try:
                import tomllib

                with open(config_path, "rb") as f:
                    user_config = tomllib.load(f)
            except ImportError:
                import toml

                with open(config_path) as f:
                    user_config = toml.load(f)

            # Add user config as a layer with higher priority
            # Use RUNTIME source to ensure it overrides defaults
            self.config.config.add_layer(user_config, ConfigSource.RUNTIME)
        self.theme_manager = ThemeManager()

        # Apply theme from config if set
        theme_name = self.config.get_string("ui.theme")
        if theme_name:
            try:
                self.theme_manager.set_theme(theme_name)
            except ValueError:
                # Invalid theme name, use default
                pass

    def _get_default_config_path(self) -> Path:
        """Get default config path using XDG standards."""
        # Check XDG_CONFIG_HOME first
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config_home:
            config_dir = Path(xdg_config_home) / "coda"
        else:
            config_dir = Path.home() / ".config" / "coda"

        return config_dir / "config.toml"

    # Convenience methods that delegate to base modules

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)

    def get_bool(self, key: str, default: bool = None) -> bool:
        """Get boolean configuration value."""
        return (
            self.config.get_bool(key, default) if default is not None else self.config.get_bool(key)
        )

    def get_string(self, key: str, default: str = None) -> str:
        """Get string configuration value."""
        return (
            self.config.get_string(key, default)
            if default is not None
            else self.config.get_string(key)
        )

    def get_int(self, key: str, default: int = None) -> int:
        """Get integer configuration value."""
        return (
            self.config.get_int(key, default) if default is not None else self.config.get_int(key)
        )

    def get_float(self, key: str, default: float = None) -> float:
        """Get float configuration value."""
        return (
            self.config.get_float(key, default)
            if default is not None
            else self.config.get_float(key)
        )

    def get_list(self, key: str, default: list | None = None) -> list:
        """Get list configuration value."""
        return self.config.get_list(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self.config.set(key, value)

    def save(self) -> None:
        """Save configuration to file."""
        from coda.base.config.models import ConfigFormat

        # Ensure directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Determine format from file extension
        suffix = self.config_path.suffix.lower()
        if suffix == ".toml":
            format = ConfigFormat.TOML
        elif suffix == ".json":
            format = ConfigFormat.JSON
        elif suffix in (".yml", ".yaml"):
            format = ConfigFormat.YAML
        else:
            format = ConfigFormat.TOML  # Default to TOML

        # Save to the same path we loaded from
        self.config.save(self.config_path, format=format)

    def to_dict(self) -> dict[str, Any]:
        """Get full configuration as dictionary."""
        return self.config.to_dict()

    # Application-specific defaults and helpers

    @property
    def default_provider(self) -> str:
        """Get default LLM provider."""
        # Check environment variable first
        env_provider = os.environ.get("CODA_DEFAULT_PROVIDER")
        if env_provider:
            return env_provider

        return self.get_string("default_provider")

    @property
    def debug(self) -> bool:
        """Check if debug mode is enabled."""
        # Check environment variable first
        env_debug = os.environ.get("CODA_DEBUG", os.environ.get("DEBUG"))
        if env_debug:
            return env_debug.lower() in ("true", "1", "yes", "on")

        return self.get_bool("debug")

    @property
    def temperature(self) -> float:
        """Get default temperature for LLM generation."""
        return self.get_float("temperature")

    @property
    def max_tokens(self) -> int:
        """Get default max tokens for LLM generation."""
        return self.get_int("max_tokens")

    def get_provider_config(self, provider: str) -> dict[str, Any]:
        """Get configuration for a specific provider."""
        return self.get(f"providers.{provider}", {})

    def get_data_dir(self) -> Path:
        """Get data directory path using XDG standards."""
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            data_dir = Path(xdg_data_home) / "coda"
        else:
            data_dir = Path.home() / ".local" / "share" / "coda"

        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    def get_cache_dir(self) -> Path:
        """Get cache directory path using XDG standards."""
        xdg_cache_home = os.environ.get("XDG_CACHE_HOME")
        if xdg_cache_home:
            cache_dir = Path(xdg_cache_home) / "coda"
        else:
            cache_dir = Path.home() / ".cache" / "coda"

        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    def get_session_db_path(self) -> Path:
        """Get session database path."""
        db_name = self.get_string("session.db_name", "sessions.db")
        return self.get_data_dir() / db_name

    def get_history_file_path(self) -> Path:
        """Get CLI history file path."""
        history_file = self.get_string("session.history_file")
        if history_file and history_file.startswith("~/"):
            # Expand home directory
            return Path(history_file).expanduser()
        elif history_file and Path(history_file).is_absolute():
            # Use absolute path as-is
            return Path(history_file)
        else:
            # Default to data directory
            return self.get_data_dir() / "history.txt"


def get_config_service() -> AppConfig:
    """Get or create the global application configuration instance.

    Returns:
        Global AppConfig instance
    """
    global _config_service
    if _config_service is None:
        _config_service = AppConfig()
    return _config_service
