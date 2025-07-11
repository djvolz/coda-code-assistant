"""Compatibility layer for old configuration API."""

from .manager import Config
from .models import ConfigSchema

# Global config instance
_config = None


def get_config() -> ConfigSchema:
    """Get the global configuration instance (compatibility function).
    
    This provides backward compatibility with the old configuration API.
    """
    global _config
    if _config is None:
        _config = Config()
    
    # Return a ConfigSchema object that mimics the old API
    config_dict = _config.to_dict()
    
    # Create a ConfigSchema with defaults if needed
    schema = ConfigSchema(
        default_provider=config_dict.get("default_provider", "mock"),
        debug=config_dict.get("debug", False),
        ui=config_dict.get("ui", {}),
        providers=config_dict.get("providers", {}),
        temperature=config_dict.get("temperature", 0.7),
        max_tokens=config_dict.get("max_tokens", 4096),
    )
    
    # Make it compatible with old API that accessed attributes directly
    for key, value in config_dict.items():
        if not hasattr(schema, key):
            setattr(schema, key, value)
    
    return schema


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


# Re-export for backward compatibility
CodaConfig = ConfigSchema