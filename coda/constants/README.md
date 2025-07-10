# Coda Constants Module

A standalone, zero-dependency constants module that can be used in any Python project.

## Features

- **Zero Dependencies**: Uses only Python standard library
- **Organized by Category**: Constants grouped logically (UI, API, DEFAULTS, etc.)
- **Type-Safe**: Includes enums and type hints
- **Immutable**: Constants cannot be modified at runtime
- **Copy-Paste Ready**: Can be copied to any project and used immediately

## Installation

### As part of Coda

```python
from coda.constants import UI, API, DEFAULTS, PROVIDERS
```

### Standalone Usage

1. Copy the entire `constants/` directory to your project
2. Import directly:

```python
from constants import UI, API, DEFAULTS, PROVIDERS
```

## Usage Examples

### Basic Usage

```python
from coda.constants import UI, API, DEFAULTS

# UI constants
print(f"Max display width: {UI.MAX_LINE_LENGTH}")
print(f"Console width: {UI.CONSOLE_WIDTH_DEFAULT}")

# API constants
print(f"Cache duration: {API.MODEL_CACHE_DURATION} seconds")
print(f"Context ratio: {API.CONTEXT_BALANCED_RATIO}")

# Default values
print(f"Default provider: {DEFAULTS.PROVIDER}")
print(f"Default temperature: {DEFAULTS.TEMPERATURE}")
```

### Using Enums

```python
from coda.constants.models import ProviderType, ThemeType, DeveloperMode

# Type-safe provider selection
provider = ProviderType.OLLAMA
print(f"Using provider: {provider.value}")

# Theme selection
theme = ThemeType.DARK
print(f"Current theme: {theme.value}")

# Developer mode
mode = DeveloperMode.CODE
print(f"Mode: {mode.value}")
```

### Accessing Lists

```python
from coda.constants import PROVIDERS, THEMES, MODES

# Get all available options
print(f"Providers: {PROVIDERS.ALL}")
print(f"Themes: {THEMES.ALL}")
print(f"Modes: {MODES.ALL}")
```

### Error Messages

```python
from coda.constants import ERRORS

# Format error messages
error = ERRORS.PROVIDER_NOT_FOUND.format(provider='test-provider')
print(error)  # "Provider 'test-provider' not found"
```

## Categories

### APP
Application metadata (name, display name)

### UI
User interface constants (display limits, styles, messages)

### API
API and network constants (timeouts, cache durations, context ratios)

### DEFAULTS
Default configuration values

### LIMITS
System limits and constraints

### PROVIDERS
Provider identifiers and list of available providers

### THEMES
Theme identifiers and list of available themes

### MODES
Developer mode identifiers

### EXPORT
Export format identifiers

### ROLES
Message role identifiers (user, assistant, system, tool)

### SESSION
Session-related constants (status values, naming patterns, database)

### ERRORS
Error message templates and help text

### FILES
File system constants (directory names, file names, extensions)

### ENV
Environment variable names

### OBSERVABILITY
Observability default values

## Immutability

All constants are immutable and cannot be modified at runtime:

```python
from coda.constants import UI

# This will raise an AttributeError
UI.MAX_LINE_LENGTH = 100  # Error: Cannot modify constant
```

## Testing

Run the standalone example to verify the module works independently:

```bash
python -m coda.constants.example
```

Or copy the module to a new location and test:

```bash
cp -r src/coda/constants /tmp/my_constants
cd /tmp
python -c "from my_constants import UI; print(UI.MAX_LINE_LENGTH)"
```

## Migration from Old Constants

If you're migrating from the old `coda.constants` module:

```python
# Old way (when constants.py existed)
from coda.constants import DEFAULT_PROVIDER, MAX_LINE_LENGTH

# New way (current)
from coda.constants import DEFAULTS, UI
provider = DEFAULTS.PROVIDER
max_length = UI.MAX_LINE_LENGTH
```

## Contributing

When adding new constants:

1. Choose the appropriate category or create a new one
2. Add to the relevant class in `definitions.py`
3. Update any enums in `models.py` if needed
4. Ensure no external dependencies are introduced
5. Add usage examples to `example.py`