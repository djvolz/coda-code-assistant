# Config Module API Reference

## Overview

The Config module provides centralized configuration management for Coda applications. It handles loading configuration from multiple sources, environment variable resolution, and type-safe access to settings.

## Installation

The Config module is part of the base Coda package:

```bash
pip install coda-assistant
```

## Quick Start

```python
from coda.base.config import Config

# Load default configuration
config = Config()

# Access configuration values
api_key = config.get("openai.api_key")
theme = config.get("theme.name", default="monokai")

# Convert to dictionary
config_dict = config.to_dict()
```

## API Reference

### Config Class

```python
class Config:
    """Manages application configuration from multiple sources."""
    
    def __init__(
        self,
        config_path: str | Path | None = None,
        env_prefix: str = "CODA_",
        auto_load: bool = True
    ):
        """
        Initialize configuration.
        
        Args:
            config_path: Path to config file (default: auto-detect)
            env_prefix: Prefix for environment variables
            auto_load: Whether to load config immediately
        """
```

#### Methods

##### get(key: str, default: Any = None) -> Any

Get a configuration value using dot notation.

```python
# Get nested value
model = config.get("providers.openai.model")

# With default
timeout = config.get("network.timeout", default=30)
```

##### set(key: str, value: Any) -> None

Set a configuration value.

```python
config.set("theme.name", "dracula")
config.set("providers.anthropic.api_key", "sk-...")
```

##### has(key: str) -> bool

Check if a configuration key exists.

```python
if config.has("openai.api_key"):
    provider = create_openai_provider()
```

##### to_dict() -> dict[str, Any]

Get entire configuration as a dictionary.

```python
config_dict = config.to_dict()
# Pass to other components
factory = ProviderFactory(config_dict)
```

##### load_file(path: str | Path) -> None

Load configuration from a specific file.

```python
config.load_file("~/my-config.toml")
```

##### reload() -> None

Reload configuration from all sources.

```python
# After changing config file
config.reload()
```

##### get_provider_config(provider_name: str) -> dict[str, Any]

Get configuration for a specific provider.

```python
openai_config = config.get_provider_config("openai")
# Returns: {"api_key": "sk-...", "model": "gpt-4", ...}
```

### Configuration Sources

Configuration is loaded from multiple sources in order of precedence:

1. **Environment Variables** (highest priority)
   ```bash
   export CODA_OPENAI_API_KEY="sk-..."
   export CODA_THEME_NAME="monokai"
   ```

2. **User Config File**
   - Linux/Mac: `~/.config/coda/config.toml`
   - Windows: `%APPDATA%/coda/config.toml`

3. **Project Config File**
   - `.coda/config.toml` in current directory or parents

4. **Default Values** (lowest priority)

### Configuration File Format

Configuration files use TOML format:

```toml
# Theme configuration
[theme]
name = "monokai"
show_line_numbers = true

# Provider configuration
[providers.openai]
api_key = "sk-..."
model = "gpt-4"
temperature = 0.7

[providers.anthropic]
api_key = "sk-ant-..."
model = "claude-3-opus-20240229"

# Session configuration
[session]
autosave = true
history_limit = 1000

# Search configuration
[search]
index_extensions = [".py", ".js", ".ts", ".md"]
exclude_patterns = ["**/node_modules/**", "**/.git/**"]
```

### Environment Variable Resolution

Environment variables are automatically resolved in config values:

```toml
[providers.openai]
api_key = "${OPENAI_API_KEY}"  # Resolves from environment

[database]
url = "${DATABASE_URL:-postgresql://localhost/coda}"  # With default
```

### Type Conversion

The Config module automatically converts types:

```python
# String to bool
debug = config.get("debug")  # "true" -> True

# String to int
port = config.get("server.port")  # "8080" -> 8080

# String to list
extensions = config.get("search.extensions")  # "py,js" -> ["py", "js"]
```

## Examples

### Basic Usage

```python
from coda.base.config import Config

# Initialize with defaults
config = Config()

# Check for required configuration
if not config.has("openai.api_key"):
    print("Please set CODA_OPENAI_API_KEY environment variable")
    exit(1)

# Get configuration with defaults
theme_name = config.get("theme.name", default="monokai")
model = config.get("openai.model", default="gpt-4")
```

### Custom Configuration Path

```python
from pathlib import Path

# Load from specific file
config = Config(config_path=Path("./my-config.toml"))

# Or load after initialization
config = Config(auto_load=False)
config.load_file("./configs/production.toml")
```

### Provider Configuration

```python
# Get all provider configs
providers_config = config.get("providers", default={})

for provider_name, provider_config in providers_config.items():
    print(f"Provider: {provider_name}")
    print(f"  Model: {provider_config.get('model')}")
    print(f"  API Key: {'***' if provider_config.get('api_key') else 'Not set'}")
```

### Dynamic Configuration

```python
# Update configuration at runtime
config.set("theme.name", "dracula")
config.set("session.autosave", True)

# Save to file (if you implement persistence)
# config.save()  # Future feature
```

### Configuration Validation

```python
def validate_config(config: Config) -> list[str]:
    """Validate configuration and return errors."""
    errors = []
    
    # Check required fields
    required = [
        "providers.openai.api_key",
        "theme.name",
    ]
    
    for key in required:
        if not config.has(key):
            errors.append(f"Missing required config: {key}")
    
    # Validate types
    if config.has("server.port"):
        port = config.get("server.port")
        if not isinstance(port, int) or port < 1 or port > 65535:
            errors.append("Invalid port number")
    
    return errors
```

## Advanced Usage

### Configuration Profiles

```python
class ProfileConfig(Config):
    """Config with profile support."""
    
    def __init__(self, profile: str = "default", **kwargs):
        super().__init__(**kwargs)
        self.profile = profile
        self._load_profile()
    
    def _load_profile(self):
        """Load profile-specific configuration."""
        profile_path = f"~/.config/coda/profiles/{self.profile}.toml"
        if Path(profile_path).expanduser().exists():
            self.load_file(profile_path)

# Use different profiles
dev_config = ProfileConfig(profile="development")
prod_config = ProfileConfig(profile="production")
```

### Configuration Observers

```python
class ObservableConfig(Config):
    """Config with change notifications."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._observers = []
    
    def add_observer(self, callback):
        """Add a configuration change observer."""
        self._observers.append(callback)
    
    def set(self, key: str, value: Any) -> None:
        """Set value and notify observers."""
        old_value = self.get(key)
        super().set(key, value)
        
        for observer in self._observers:
            observer(key, old_value, value)

# Usage
config = ObservableConfig()
config.add_observer(lambda k, o, n: print(f"{k}: {o} -> {n}"))
config.set("theme.name", "dracula")  # Prints: theme.name: monokai -> dracula
```

### Encrypted Values

```python
def decrypt_value(encrypted: str) -> str:
    """Decrypt an encrypted configuration value."""
    # Implementation depends on your encryption method
    return decrypted_value

class SecureConfig(Config):
    """Config with encrypted value support."""
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value, decrypting if necessary."""
        value = super().get(key, default)
        
        if isinstance(value, str) and value.startswith("enc:"):
            return decrypt_value(value[4:])
        
        return value

# Usage with encrypted API keys
# config.toml:
# [providers.openai]
# api_key = "enc:U2FsdGVkX1+..."
```

## Best Practices

1. **Use Environment Variables for Secrets**
   ```bash
   export CODA_OPENAI_API_KEY="sk-..."
   ```

2. **Provide Sensible Defaults**
   ```python
   timeout = config.get("network.timeout", default=30)
   ```

3. **Validate Early**
   ```python
   def startup():
       config = Config()
       errors = validate_config(config)
       if errors:
           raise ValueError(f"Configuration errors: {errors}")
   ```

4. **Use Dot Notation**
   ```python
   # Good
   model = config.get("providers.openai.model")
   
   # Less flexible
   model = config.to_dict()["providers"]["openai"]["model"]
   ```

5. **Document Configuration**
   ```toml
   # Maximum number of retries for API calls
   # Default: 3
   [network]
   max_retries = 3
   
   # Request timeout in seconds
   # Default: 30
   timeout = 30
   ```

## Error Handling

```python
from coda.base.config import ConfigError

try:
    config = Config(config_path="/invalid/path.toml")
except ConfigError as e:
    print(f"Configuration error: {e}")
    # Use defaults or exit

# Handle missing values gracefully
api_key = config.get("openai.api_key")
if not api_key:
    print("OpenAI API key not configured")
    print("Set CODA_OPENAI_API_KEY or add to config file")
```

## See Also

- [Integration Guide](../integration-guide.md) - Using Config with other modules
- [Example: Simple Chatbot](../../tests/examples/simple_chatbot/) - Config in practice
- [Environment Variables](../reference/environment-variables.md) - Full list of env vars