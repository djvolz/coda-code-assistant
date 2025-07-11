"""🔧 SERVICE MODULE
Configuration service that integrates base config and theme modules.

This service provides application-level configuration management by:
- Integrating base config, theme, and other modules
- Providing sensible defaults for Coda applications
- Managing configuration file locations using XDG standards
- Handling environment variable overrides
"""

from .config_service import ConfigService, get_config_service

__all__ = ["ConfigService", "get_config_service"]