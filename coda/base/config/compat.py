"""Compatibility layer for old configuration API."""

from typing import Any
from .manager import Config

# Global config instance
_config = None


class CodaConfig:
    """Compatibility wrapper that mimics the old configuration API."""
    
    def __init__(self, config_dict: dict[str, Any]):
        self._dict = config_dict
        # Set common attributes
        self.default_provider = config_dict.get("default_provider", "mock")
        self.debug = config_dict.get("debug", False)
        self.ui = config_dict.get("ui", {})
        self.providers = config_dict.get("providers", {})
        self.temperature = config_dict.get("temperature", 0.7)
        self.max_tokens = config_dict.get("max_tokens", 4096)
        self.session = config_dict.get("session", {})
        
        # Add any other keys as attributes
        for key, value in config_dict.items():
            if not hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (compatibility method)."""
        return self._dict
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value with default (compatibility method)."""
        return self._dict.get(key, default)


def get_config() -> CodaConfig:
    """Get the global configuration instance (compatibility function).
    
    This provides backward compatibility with the old configuration API.
    """
    global _config
    if _config is None:
        _config = Config()
    
    # Return a CodaConfig object that mimics the old API
    config_dict = _config.to_dict()
    return CodaConfig(config_dict)


def save_config() -> None:
    """Save the current configuration (compatibility function)."""
    global _config
    if _config is not None:
        _config.save()


def get_config_manager() -> Config:
    """Get the config manager instance (compatibility function)."""
    global _config
    if _config is None:
        _config = Config()
    return _config


# Note: CodaConfig is defined above and should be used instead of ConfigSchema