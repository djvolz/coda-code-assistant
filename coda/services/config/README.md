# Configuration Service

The Configuration Service provides a high-level interface for managing Coda's configuration, integrating the base config and theme modules with application-specific defaults and behaviors.

## Overview

The `ConfigService` class acts as a facade that:
- Manages configuration loading and saving
- Integrates theme management
- Provides XDG directory support
- Maintains backward compatibility during migration

## Architecture

```
services/config/
├── __init__.py          # Public API exports
├── config_service.py    # Main ConfigService implementation
├── example.py          # Usage examples
└── migrate.py          # Migration tool for old configs
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

The configuration follows this structure:

```toml
# Provider settings
default_provider = "ollama"

[providers.ollama]
base_url = "http://localhost:11434"
timeout = 300

[providers.oci_genai]
compartment_id = "ocid1.compartment.oc1..."
endpoint = "https://generativeai.aiservice.us-chicago-1.oci.oraclecloud.com"

# UI settings
[ui]
theme = "dracula"

# Model parameters
temperature = 0.7
max_tokens = 2000

# Session settings
[session]
autosave = true
history_limit = 100

# Debug settings
debug = false
```

## Key Features

### 1. XDG Directory Support

The service automatically uses XDG directory standards:
- Config: `~/.config/coda/config.toml` (or `$XDG_CONFIG_HOME/coda/config.toml`)
- Data: `~/.local/share/coda/` (or `$XDG_DATA_HOME/coda/`)
- Cache: `~/.cache/coda/` (or `$XDG_CACHE_HOME/coda/`)

### 2. Environment Variable Support

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