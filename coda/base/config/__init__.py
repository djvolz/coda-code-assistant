"""🔧 BASE MODULE
Standalone configuration management module.

This module provides flexible configuration management with support for:
- Multiple configuration sources (files, environment, defaults)
- Hierarchical configuration merging
- Type-safe access methods
- Multiple file formats (TOML, JSON, YAML)
- Zero required dependencies

Example usage:
    from coda.config import Config

    # Create config manager with default path
    config = Config()

    # Get values with defaults
    debug = config.get_bool("debug", default=False)
    theme = config.get_string("ui.theme", default="dark")

    # Get entire config section
    providers = config.get_dict("providers", default={})
"""

from .manager import Config, ConfigManager
from .models import ConfigSchema, ConfigSource

__all__ = ["Config", "ConfigManager", "ConfigSchema", "ConfigSource"]
