"""Data models for configuration module.

This module contains configuration-related data structures.
Zero dependencies - uses only Python standard library.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ConfigSource(Enum):
    """Configuration source types."""

    DEFAULT = "default"
    FILE = "file"
    ENVIRONMENT = "environment"
    RUNTIME = "runtime"


class ConfigFormat(Enum):
    """Supported configuration file formats."""

    TOML = "toml"
    JSON = "json"
    YAML = "yaml"
    INI = "ini"


@dataclass
class ConfigSchema:
    """Schema definition for configuration validation."""

    # Field definitions: name -> (type, default, description)
    fields: dict[str, tuple[type, Any, str]] = field(default_factory=dict)

    # Required fields
    required: list[str] = field(default_factory=list)

    # Nested schemas
    nested: dict[str, "ConfigSchema"] = field(default_factory=dict)

    def add_field(
        self,
        name: str,
        field_type: type,
        default: Any = None,
        description: str = "",
        required: bool = False,
    ) -> None:
        """Add a field to the schema."""
        self.fields[name] = (field_type, default, description)
        if required and name not in self.required:
            self.required.append(name)

    def add_nested(self, name: str, schema: "ConfigSchema") -> None:
        """Add a nested schema."""
        self.nested[name] = schema


@dataclass
class ConfigValue:
    """A configuration value with metadata."""

    value: Any
    source: ConfigSource
    path: Path | None = None  # For file sources
    key: str | None = None  # For environment sources

    def __str__(self) -> str:
        """String representation."""
        if self.source == ConfigSource.FILE and self.path:
            return f"{self.value} (from {self.path})"
        elif self.source == ConfigSource.ENVIRONMENT and self.key:
            return f"{self.value} (from ${self.key})"
        else:
            return f"{self.value} (from {self.source.value})"


@dataclass
class LayeredConfig:
    """Represents configuration from multiple layers."""

    # Configuration layers in priority order (highest to lowest)
    layers: list[dict[str, Any]] = field(default_factory=list)

    # Source tracking for each layer
    sources: list[ConfigSource] = field(default_factory=list)

    # Merged configuration cache
    _merged: dict[str, Any] | None = field(default=None, init=False)

    def add_layer(self, config: dict[str, Any], source: ConfigSource) -> None:
        """Add a configuration layer.

        Runtime configs are prepended (highest priority),
        others are appended (lower priority).
        """
        if source == ConfigSource.RUNTIME:
            # Runtime configs have highest priority, add to beginning
            self.layers.insert(0, config)
            self.sources.insert(0, source)
        else:
            # Other configs are added in order
            self.layers.append(config)
            self.sources.append(source)
        self._merged = None  # Invalidate cache

    def get_merged(self) -> dict[str, Any]:
        """Get merged configuration from all layers."""
        if self._merged is None:
            self._merged = {}
            # Apply layers in reverse order (lowest to highest priority)
            for layer in reversed(self.layers):
                self._merge_dict(self._merged, layer)
        return self._merged

    def _merge_dict(self, target: dict[str, Any], source: dict[str, Any]) -> None:
        """Recursively merge source dict into target dict."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_dict(target[key], value)
            else:
                target[key] = value


@dataclass
class ConfigPath:
    """Configuration file path with metadata."""

    path: Path
    format: ConfigFormat
    required: bool = False
    description: str = ""

    def exists(self) -> bool:
        """Check if the config file exists."""
        return self.path.exists()

    def is_readable(self) -> bool:
        """Check if the config file is readable."""
        return self.path.exists() and self.path.is_file()


# Pre-defined schemas for common configuration patterns
@dataclass
class ApplicationConfig:
    """Common application configuration schema."""

    name: str
    version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    config_dir: Path | None = None
    data_dir: Path | None = None
    cache_dir: Path | None = None


@dataclass
class ServerConfig:
    """Common server configuration schema."""

    host: str = "localhost"
    port: int = 8080
    workers: int = 1
    timeout: int = 30
    ssl_enabled: bool = False
    ssl_cert: Path | None = None
    ssl_key: Path | None = None


@dataclass
class DatabaseConfig:
    """Common database configuration schema."""

    url: str | None = None
    host: str = "localhost"
    port: int = 5432
    name: str = "db"
    user: str = "user"
    password: str = ""
    pool_size: int = 10
    echo: bool = False
