"""🔧 SERVICE MODULE
Configuration service that integrates base config and theme modules.

This service provides application-level configuration management by:
- Integrating base config, theme, and other modules
- Providing sensible defaults for Coda applications
- Managing configuration file locations using XDG standards
- Handling environment variable overrides
"""

from .app_config import AppConfig, get_config_service

__all__ = ["AppConfig", "get_config_service"]
