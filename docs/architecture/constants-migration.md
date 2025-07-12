# Constants Migration Guide

## Current State

The codebase currently has a centralized constants module (`coda/constants/`) that is used by 199+ files. While this provides a single source of truth, it violates our modular architecture principles by creating unnecessary dependencies between modules.

## Target Architecture

Each module should define its own constants, making it truly standalone and copy-pasteable.

## Good Examples

### Theme Module
The theme module correctly defines its constants in `models.py`:
```python
class ThemeNames:
    """Standard theme name constants."""
    DEFAULT = "default"
    DARK = "dark"
    LIGHT = "light"
    # ... etc
```

### Providers Module
The providers module has its own `constants.py`:
```python
class PROVIDERS:
    """Provider identifiers."""
    OCI_GENAI = "oci_genai"
    LITELLM = "litellm"
    # ... etc

# Model defaults
DEFAULT_CONTEXT_LENGTH = 4096
DEFAULT_TEMPERATURE = 0.7
```

## Migration Strategy

### For New Code
- **Always** define constants within the module that uses them
- **Never** import from `coda.constants` in new modules
- Put constants in the most logical file within the module
- Only create a separate `constants.py` if many constants are shared across multiple files

### For Existing Code
Given the scale (199+ files), we should:
1. Keep the central constants module for backward compatibility
2. When modifying a module, migrate its constants locally
3. Mark migrated constants in the central module as deprecated
4. Eventually remove the central constants module when no longer used

### Where to Put Constants

#### Few constants used in one file
Put them directly in that file:
```python
# In session/database.py
FTS_TABLE_NAME = "messages_fts"
FTS_CONTENT_TABLE = "messages"
```

#### Constants used across multiple files in a module
Create a `constants.py` in the module:
```python
# In cli/constants.py
MAX_LINE_LENGTH = 80
CONSOLE_WIDTH_DEFAULT = 80
```

#### Constants that define module interface
Put them in the module's `__init__.py` or main class:
```python
# In providers/__init__.py
class ProviderType(Enum):
    LITELLM = "litellm"
    OLLAMA = "ollama"
```

## Anti-Patterns to Avoid

1. **Don't** create a constants module just because "every module needs one"
2. **Don't** import constants from other modules (breaks independence)
3. **Don't** duplicate constants across modules (use configuration instead)

## Example Migration

Before:
```python
# In coda/session/database.py
from ..constants import FTS_TABLE_NAME, SESSION_DB_PATH
```

After:
```python
# In coda/session/database.py
# Local constants
FTS_TABLE_NAME = "messages_fts"
FTS_CONTENT_TABLE = "messages"

# Or if shared across session module:
from .constants import FTS_TABLE_NAME
```

## Configuration vs Constants

Some "constants" might actually be configuration:
- Constants: `FTS_TABLE_NAME = "messages_fts"` (never changes)
- Configuration: `DEFAULT_THEME = "dark"` (user can override)

Configuration should use the config module, not constants.