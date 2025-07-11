"""Core configuration manager implementation.

This module provides the main configuration management functionality.
It has zero external dependencies and uses only Python standard library.
"""

import json
import os
from pathlib import Path
from typing import Any, TypeVar

from .models import ConfigFormat, ConfigPath, ConfigSource, LayeredConfig

# Type variable for generic return types
T = TypeVar("T")


class ConfigManager:
    """Manages configuration from multiple sources with layered priority."""

    def __init__(
        self,
        app_name: str = "app",
        config_paths: list[ConfigPath] | None = None,
        env_prefix: str = "",
        defaults: dict[str, Any] | None = None,
    ):
        """Initialize configuration manager.

        Args:
            app_name: Application name for default paths
            config_paths: List of configuration file paths to load
            env_prefix: Prefix for environment variables (e.g., "MYAPP_")
            defaults: Default configuration values
        """
        self.app_name = app_name
        self.env_prefix = env_prefix
        self.config = LayeredConfig()

        # First, try to load package default.toml
        self._load_package_defaults()

        # Add provided defaults (if any)
        if defaults:
            self.config.add_layer(defaults, ConfigSource.DEFAULT)

        # Load configuration files
        if config_paths:
            for config_path in config_paths:
                self._load_config_file(config_path)
        else:
            # Load from default locations
            self._load_default_configs()

        # Apply environment variables
        self._load_environment_vars()

    def _load_package_defaults(self) -> None:
        """Load default.toml from the package if it exists."""
        try:
            import importlib.resources

            # For Python 3.9+
            if hasattr(importlib.resources, "files"):
                # Try multiple locations for default.toml
                locations = [
                    self.app_name,  # package root
                    f"{self.app_name}.config",  # config subpackage
                    f"{self.app_name}.services.config",  # services.config subpackage
                ]

                for location in locations:
                    try:
                        files = importlib.resources.files(location)
                        if files and (files / "default.toml").is_file():
                            default_content = (files / "default.toml").read_text()
                            default_config = self._parse_toml(default_content)
                            self.config.add_layer(default_config, ConfigSource.DEFAULT)
                            return  # Found it, stop looking
                    except Exception:
                        continue
            else:
                # Fallback for Python 3.8
                import pkg_resources

                locations = [
                    (self.app_name, "default.toml"),
                    (f"{self.app_name}.config", "default.toml"),
                    (f"{self.app_name}.services.config", "default.toml"),
                ]

                for package, resource in locations:
                    try:
                        if pkg_resources.resource_exists(package, resource):
                            default_content = pkg_resources.resource_string(
                                package, resource
                            ).decode("utf-8")
                            default_config = self._parse_toml(default_content)
                            self.config.add_layer(default_config, ConfigSource.DEFAULT)
                            return  # Found it, stop looking
                    except Exception:
                        continue
        except Exception:
            # If loading package defaults fails, continue
            pass

    def _load_default_configs(self) -> None:
        """Load configuration from default locations."""
        # Define default config locations
        default_paths = [
            # System-wide config
            ConfigPath(
                Path(f"/etc/{self.app_name}/config.toml"), ConfigFormat.TOML, required=False
            ),
            # User config
            ConfigPath(
                Path.home() / f".config/{self.app_name}/config.toml",
                ConfigFormat.TOML,
                required=False,
            ),
            # Project config
            ConfigPath(Path(f".{self.app_name}/config.toml"), ConfigFormat.TOML, required=False),
        ]

        # Also check for JSON alternatives
        for path in list(default_paths):
            json_path = ConfigPath(
                path.path.with_suffix(".json"), ConfigFormat.JSON, required=False
            )
            default_paths.append(json_path)

        # Load each config file
        for config_path in default_paths:
            if config_path.is_readable():
                self._load_config_file(config_path)

    def _load_config_file(self, config_path: ConfigPath) -> None:
        """Load a configuration file."""
        if not config_path.exists():
            if config_path.required:
                raise FileNotFoundError(f"Required config file not found: {config_path.path}")
            return

        try:
            content = config_path.path.read_text()

            if config_path.format == ConfigFormat.JSON:
                data = json.loads(content)
            elif config_path.format == ConfigFormat.TOML:
                data = self._parse_toml(content)
            elif config_path.format == ConfigFormat.YAML:
                data = self._parse_yaml(content)
            elif config_path.format == ConfigFormat.INI:
                data = self._parse_ini(content)
            else:
                raise ValueError(f"Unsupported format: {config_path.format}")

            self.config.add_layer(data, ConfigSource.FILE)
        except Exception:
            if config_path.required:
                raise
            # Silently ignore optional config files that fail to load
            pass

    def _parse_toml(self, content: str) -> dict[str, Any]:
        """Parse TOML content (basic implementation)."""
        # Try to use tomllib if available (Python 3.11+)
        try:
            import tomllib

            return tomllib.loads(content)
        except ImportError:
            pass

        # Try tomli as fallback
        try:
            import tomli

            return tomli.loads(content)
        except ImportError:
            pass

        # Basic fallback parser for simple TOML
        result = {}
        current_section = result

        for line in content.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Section header
            if line.startswith("[") and line.endswith("]"):
                section_name = line[1:-1]
                if "." in section_name:
                    # Nested section
                    parts = section_name.split(".")
                    current = result
                    for part in parts[:-1]:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                    current[parts[-1]] = {}
                    current_section = current[parts[-1]]
                else:
                    result[section_name] = {}
                    current_section = result[section_name]
            elif "=" in line:
                # Key-value pair
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                # Parse value
                if value.startswith('"') and value.endswith('"'):
                    current_section[key] = value[1:-1]
                elif value.lower() in ("true", "false"):
                    current_section[key] = value.lower() == "true"
                elif value.isdigit():
                    current_section[key] = int(value)
                elif "." in value and all(part.isdigit() for part in value.split(".")):
                    current_section[key] = float(value)
                else:
                    current_section[key] = value

        return result

    def _parse_yaml(self, content: str) -> dict[str, Any]:
        """Parse YAML content."""
        try:
            import yaml

            return yaml.safe_load(content)
        except ImportError:
            raise ImportError("PyYAML is required for YAML config files") from None

    def _parse_ini(self, content: str) -> dict[str, Any]:
        """Parse INI content."""
        import configparser

        parser = configparser.ConfigParser()
        parser.read_string(content)

        result = {}
        for section in parser.sections():
            result[section] = dict(parser.items(section))

        return result

    def _load_environment_vars(self) -> None:
        """Load configuration from environment variables."""
        env_config = {}
        prefix = self.env_prefix.upper()

        for key, value in os.environ.items():
            if prefix and not key.startswith(prefix):
                continue

            # Remove prefix
            if prefix:
                key = key[len(prefix) :]

            # Convert to lowercase and nested structure
            parts = key.lower().split("_")
            current = env_config

            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                elif not isinstance(current[part], dict):
                    # Skip if we hit a non-dict value
                    continue
                current = current[part]

            # Parse value (only if current is still a dict)
            if isinstance(current, dict):
                current[parts[-1]] = self._parse_env_value(value)

        if env_config:
            self.config.add_layer(env_config, ConfigSource.ENVIRONMENT)

    def _parse_env_value(self, value: str) -> Any:
        """Parse environment variable value."""
        # Boolean
        if value.lower() in ("true", "1", "yes", "on"):
            return True
        elif value.lower() in ("false", "0", "no", "off"):
            return False

        # Number
        if value.isdigit():
            return int(value)

        try:
            return float(value)
        except ValueError:
            pass

        # JSON
        if value.startswith(("{", "[")):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass

        # String
        return value

    def get(self, key: str, default: T = None) -> T:
        """Get a configuration value.

        Args:
            key: Dot-separated key (e.g., "database.host")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        parts = key.split(".")
        current = self.config.get_merged()

        try:
            for part in parts:
                current = current[part]
            return current
        except (KeyError, TypeError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a boolean configuration value."""
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)

    def get_int(self, key: str, default: int = 0) -> int:
        """Get an integer configuration value."""
        value = self.get(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get a float configuration value."""
        value = self.get(key, default)
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def get_string(self, key: str, default: str = "") -> str:
        """Get a string configuration value."""
        value = self.get(key, default)
        return str(value) if value is not None else default

    def get_list(self, key: str, default: list[Any] | None = None) -> list[Any]:
        """Get a list configuration value."""
        value = self.get(key, default or [])
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            # Try to parse comma-separated values
            return [v.strip() for v in value.split(",") if v.strip()]
        return list(value) if value else []

    def get_dict(self, key: str, default: dict[str, Any] | None = None) -> dict[str, Any]:
        """Get a dictionary configuration value."""
        value = self.get(key, default or {})
        if isinstance(value, dict):
            return value
        return {}

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value at runtime.

        Args:
            key: Dot-separated key
            value: Value to set
        """
        parts = key.split(".")
        runtime_config = {}
        current = runtime_config

        # Build nested structure
        for part in parts[:-1]:
            current[part] = {}
            current = current[part]

        current[parts[-1]] = value

        # Add as runtime layer (highest priority)
        self.config.add_layer(runtime_config, ConfigSource.RUNTIME)

    def to_dict(self) -> dict[str, Any]:
        """Get the entire configuration as a dictionary."""
        return self.config.get_merged()

    def get_config_dir(self) -> Path:
        """Get the configuration directory path.

        Returns:
            Path to configuration directory
        """
        # Check XDG_CONFIG_HOME first
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            return Path(xdg_config) / self.app_name

        # Default to ~/.config/app_name
        return Path.home() / ".config" / self.app_name

    def get_data_dir(self) -> Path:
        """Get the data directory path.

        Returns:
            Path to data directory
        """
        # Check XDG_DATA_HOME first
        xdg_data = os.environ.get("XDG_DATA_HOME")
        if xdg_data:
            return Path(xdg_data) / self.app_name

        # Default to ~/.local/share/app_name
        return Path.home() / ".local" / "share" / self.app_name

    def get_cache_dir(self) -> Path:
        """Get the cache directory path.

        Returns:
            Path to cache directory
        """
        # Check XDG_CACHE_HOME first
        xdg_cache = os.environ.get("XDG_CACHE_HOME")
        if xdg_cache:
            return Path(xdg_cache) / self.app_name

        # Default to ~/.cache/app_name
        return Path.home() / ".cache" / self.app_name

    def save(self, path: Path, format: ConfigFormat = ConfigFormat.JSON) -> None:
        """Save configuration to a file.

        Args:
            path: File path to save to
            format: Configuration format
        """
        config_dict = self.to_dict()

        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        if format == ConfigFormat.JSON:
            with open(path, "w") as f:
                json.dump(config_dict, f, indent=2)
        elif format == ConfigFormat.TOML:
            # Try to use tomli-w if available
            try:
                import tomli_w

                with open(path, "wb") as f:
                    tomli_w.dump(config_dict, f)
            except ImportError:
                raise ImportError("tomli-w is required for saving TOML files") from None
        elif format == ConfigFormat.YAML:
            try:
                import yaml

                with open(path, "w") as f:
                    yaml.dump(config_dict, f, default_flow_style=False)
            except ImportError:
                raise ImportError("PyYAML is required for saving YAML files") from None
        else:
            raise ValueError(f"Unsupported format for saving: {format}")


# Convenience class with simpler API
class Config(ConfigManager):
    """Simplified configuration manager with sensible defaults."""

    def __init__(
        self,
        app_name: str = "app",
        config_file: str | Path | None = None,
        env_prefix: str | None = None,
        defaults: dict[str, Any] | None = None,
    ):
        """Initialize simplified config manager.

        Args:
            app_name: Application name
            config_file: Optional specific config file to load
            env_prefix: Environment variable prefix (defaults to APP_NAME_)
            defaults: Default configuration values
        """
        if env_prefix is None:
            env_prefix = f"{app_name.upper()}_"

        config_paths = []
        if config_file:
            path = Path(config_file)
            # Detect format from extension
            suffix = path.suffix.lower()
            if suffix == ".toml":
                format = ConfigFormat.TOML
            elif suffix == ".json":
                format = ConfigFormat.JSON
            elif suffix in (".yml", ".yaml"):
                format = ConfigFormat.YAML
            elif suffix == ".ini":
                format = ConfigFormat.INI
            else:
                format = ConfigFormat.JSON  # Default

            config_paths = [ConfigPath(path, format, required=True)]

        super().__init__(
            app_name=app_name,
            config_paths=config_paths,
            env_prefix=env_prefix,
            defaults=defaults,
        )
