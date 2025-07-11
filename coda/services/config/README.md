# Configuration Service

The Configuration Service provides a high-level interface for managing Coda's configuration, integrating the base config and theme modules with application-specific defaults and behaviors.

## Overview

The `AppConfig` class acts as a facade that:
- Loads comprehensive defaults from `default.toml`
- Manages configuration loading and saving
- Integrates theme management
- Provides XDG directory support
- Maintains backward compatibility during migration

## Architecture

```
services/config/
├── __init__.py          # Public API exports
├── app_config.py        # Main AppConfig implementation
├── default.toml         # Comprehensive default configuration
├── example.py           # Usage examples
└── README.md           # This file
```

## Usage

### Basic Usage

```python
from coda.services.config import get_config_service

# Get the global config service instance
config = get_config_service()

# Access configuration values
provider = config.default_provider
debug_mode = config.debug

# Get nested values
theme_name = config.get("ui.theme", "dracula")
max_tokens = config.get("max_tokens", 2000)

# Set configuration values
config.set("temperature", 0.8)
config.set("providers.ollama.base_url", "http://localhost:11434")

# Save configuration
config.save()
```

### Theme Integration

```python
# Get theme manager
theme_manager = config.theme_manager

# Get themed console
console = theme_manager.get_console()

# Get theme for display
theme = theme_manager.get_console_theme()

# Change theme
theme_manager.set_theme("monokai")
config.set("ui.theme", "monokai")
config.save()
```

### Custom Configuration Path

```python
from pathlib import Path
from coda.services.config import AppConfig

# Use custom config file
custom_config = AppConfig(config_path=Path("/custom/path/config.toml"))
```

## Configuration Structure

All default configuration values are defined in `default.toml`. Here's a summary of the main sections:

```toml
# General settings
default_provider = "mock"    # Default LLM provider
debug = false               # Debug mode
temperature = 0.7           # LLM temperature
max_tokens = 2000          # Max tokens for generation

# Provider configurations
[providers.oci_genai]
enabled = false
compartment_id = ""
profile = "DEFAULT"
region = "us-chicago-1"
default_model = "cohere.command-r-plus"

[providers.ollama]
enabled = false
base_url = "http://localhost:11434"
default_model = "llama3.2:3b"

# UI settings
[ui]
theme = "default"
show_model_info = true
streaming = true
console_width = 80

# Session settings
[session]
history_file = "~/.local/share/coda/history.txt"
max_history = 1000
autosave = true

# Search settings
[search]
chunk_size = 1000
search_k = 5
similarity_threshold = 0.7

# And many more...
```

See `default.toml` for the complete list of available settings.

## Key Features

### 1. Configuration Hierarchy

Configuration values are loaded and merged in this order (highest priority first):
1. Runtime changes via `config.set()`
2. Environment variables (e.g., `CODA_DEBUG=true`)
3. Project config (`.coda/config.toml`)
4. User config (`~/.config/coda/config.toml`)
5. System config (`/etc/coda/config.toml`)
6. Package defaults (`default.toml`)

This means user settings override defaults, and environment variables override everything except runtime changes.

### 2. XDG Directory Support

The service automatically uses XDG directory standards:
- Config: `~/.config/coda/config.toml` (or `$XDG_CONFIG_HOME/coda/config.toml`)
- Data: `~/.local/share/coda/` (or `$XDG_DATA_HOME/coda/`)
- Cache: `~/.cache/coda/` (or `$XDG_CACHE_HOME/coda/`)

### 3. Environment Variable Support

Configuration values can be overridden with environment variables:
- `CODA_DEBUG=true` - Enable debug mode
- `CODA_DEFAULT_PROVIDER=ollama` - Set default provider
- `OCI_COMPARTMENT_ID=...` - Provider-specific settings

### 3. Attribute Access

Common configuration values are accessible as attributes:

```python
config = get_config_service()
print(config.default_provider)  # Direct attribute access
print(config.debug)            # Boolean values
print(config.temperature)      # Numeric values
```

### 4. Dictionary Interface

The service provides a dictionary-like interface:

```python
# Get configuration as dictionary
config_dict = config.to_dict()

# Access nested values
providers = config_dict["providers"]
ollama_settings = providers["ollama"]
```

## Integration with Base Modules

The AppConfig service integrates two base modules:

1. **base.config.Config** - Handles TOML file I/O and value management
2. **base.theme.ThemeManager** - Manages color themes and console styling

This integration provides a unified interface for applications while maintaining module independence.

## Migration from Old Configuration

If you have existing configuration files from the old system, you can migrate them:

```python
from coda.services.config.migrate import migrate_configuration

# Migrate old config to new format
migrate_configuration(
    old_path=Path("~/.coda/config.toml"),
    new_path=Path("~/.config/coda/config.toml")
)
```

## Best Practices

1. **Use the singleton**: Always use `get_config_service()` for the global instance
2. **Save sparingly**: Only call `save()` after making multiple changes
3. **Use defaults**: Always provide defaults when using `get()`
4. **Validate inputs**: The service doesn't validate provider-specific settings

## Example: Creating a Provider

```python
from coda.services.config import get_config_service
from coda.base.providers import ProviderFactory

# Get configuration
config = get_config_service()

# Create provider factory with config
factory = ProviderFactory(config.to_dict())

# Create provider instance
provider = factory.create(config.default_provider)
```

## Thread Safety

The AppConfig service is NOT thread-safe. If you need to use it in a multi-threaded environment, you should:
- Create separate instances per thread, or
- Add your own synchronization primitives

## Future Enhancements

1. **Validation**: Add schema validation for configuration values
2. **Reload**: Support hot-reloading of configuration changes
3. **Profiles**: Support multiple configuration profiles
4. **Encryption**: Add support for encrypting sensitive values