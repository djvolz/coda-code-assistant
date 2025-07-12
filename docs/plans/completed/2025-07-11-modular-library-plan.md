# Coda Modular Library Implementation Plan

## Overview

Transform Coda from a monolithic CLI application into a modular Python library where each module:
- Can be imported independently (`from coda.theme import ThemeManager`)
- Has minimal or no dependencies on other Coda modules
- Can be copy/pasted into other projects
- Works standalone with a simple example client

## Core Principles

1. **True Independence**: Each module must work without importing other Coda modules
2. **Minimal Dependencies**: Use only essential third-party packages per module
3. **Simple APIs**: Clean, intuitive interfaces that are easy to use
4. **Local First**: Everything runs locally, no network services required
5. **Progressive Enhancement**: Coda CLI uses all modules, but users can pick what they need

## Module Structure

```
coda/
├── pyproject.toml                 # Main package with optional dependencies
├── README.md                      # Overview and quick start
├── src/
│   └── coda/
│       ├── __init__.py           # Package initialization
│       ├── theme/                # Terminal/UI theming
│       │   ├── __init__.py
│       │   ├── manager.py        # Core theme functionality
│       │   ├── models.py         # Theme data models
│       │   └── example.py        # Standalone example
│       ├── config/               # Configuration management
│       │   ├── __init__.py
│       │   ├── manager.py        # Config storage/retrieval
│       │   ├── models.py         # Config data models
│       │   └── example.py        # Standalone example
│       ├── constants/            # Static values and enums
│       │   ├── __init__.py
│       │   ├── definitions.py    # All constants
│       │   └── example.py        # Standalone example
│       ├── intelligence/         # AI/LLM integration
│       │   ├── __init__.py
│       │   ├── base.py          # Abstract base classes
│       │   ├── providers/        # Different AI providers
│       │   │   ├── __init__.py
│       │   │   ├── openai.py
│       │   │   ├── anthropic.py
│       │   │   └── local.py
│       │   └── example.py        # Standalone example
│       └── cli/                  # Full CLI using all modules
│           ├── __init__.py
│           └── main.py
├── tests/                        # Module-specific tests
│   ├── test_theme.py
│   ├── test_config.py
│   ├── test_constants.py
│   └── test_intelligence.py
└── examples/                     # Standalone usage examples
    ├── theme_only.py
    ├── config_only.py
    ├── constants_only.py
    └── intelligence_only.py
```

## Implementation Phases

### Phase 1: Foundation Modules (Week 1-2)

#### 1.1 Constants Module
- **Purpose**: Static values, enums, and application constants
- **Dependencies**: None (pure Python)
- **Example Usage**:
```python
from coda.constants import UI, API, DEFAULTS

print(UI.MAX_LINE_LENGTH)  # 80
print(API.TIMEOUT)         # 30
print(DEFAULTS.THEME)      # "dark"
```

#### 1.2 Config Module  
- **Purpose**: Local configuration management
- **Dependencies**: `pyyaml` or `toml` (optional)
- **Example Usage**:
```python
from coda.config import Config

config = Config("~/.myapp")
config.set("theme", "dark")
theme = config.get("theme", default="light")
```

#### 1.3 Theme Module
- **Purpose**: Terminal colors, formatting, UI themes
- **Dependencies**: `rich` or `colorama` (optional)
- **Example Usage**:
```python
from coda.theme import Theme

theme = Theme("dark")
print(theme.style("success", "Operation completed!"))
print(theme.color.primary("Important text"))
```

### Phase 2: Intelligence Module (Week 3-4)

#### 2.1 Provider Interface
- **Purpose**: Unified interface for AI/LLM providers
- **Dependencies**: Provider-specific (openai, anthropic, etc.)
- **Example Usage**:
```python
from coda.intelligence import get_provider

# Each provider is optional
ai = get_provider("openai", api_key="...")
response = ai.complete("Explain Python decorators")
```

#### 2.2 Local Provider
- **Purpose**: Offline/local model support
- **Dependencies**: `transformers` or `llama-cpp-python` (optional)

### Phase 3: Integration (Week 5)

#### 3.1 Combined CLI
- **Purpose**: Full Coda experience using all modules
- **Dependencies**: All Coda modules
- **Example**: The current Coda CLI reimplemented with modular components

#### 3.2 Testing & Documentation
- **Purpose**: Ensure true module independence
- **Approach**: Each module must pass tests without other Coda modules

## Module Independence Verification

Each module will have:

1. **Standalone Example** (`example.py`):
```python
#!/usr/bin/env python3
"""
Standalone example showing this module works without other Coda modules.
Run with: python -m coda.theme.example
"""
```

2. **Minimal Dependencies**:
```toml
# In pyproject.toml
[project.optional-dependencies]
theme = ["rich>=10.0.0"]
config = ["pyyaml>=6.0"]
intelligence-openai = ["openai>=1.0"]
intelligence-anthropic = ["anthropic>=0.8"]
```

3. **Copy-Paste Test**:
- Module folder can be copied to another project
- Changes import from `coda.theme` to `theme`
- Still works perfectly

## Migration Strategy

1. **Analyze Current Dependencies**:
   - Map current inter-module imports
   - Identify shared code to extract
   - Plan decoupling strategy

2. **Start with Leaf Modules**:
   - Constants (no dependencies)
   - Config (minimal dependencies)
   - Theme (UI only)

3. **Refactor Incrementally**:
   - One module at a time
   - Maintain backward compatibility
   - Test standalone functionality

4. **Update Imports**:
   - From: `from coda.module import thing`
   - To: `from coda.module import thing` (same, but now truly independent)

## Success Criteria

1. **Each module works standalone**:
   ```bash
   # This should work for each module
   cp -r src/coda/theme ~/myproject/
   cd ~/myproject
   python -c "from theme import Theme; t = Theme(); print(t.style('success', 'Works!'))"
   ```

2. **Minimal install works**:
   ```bash
   pip install coda  # Gets core only
   pip install "coda[theme]"  # Just theme features
   pip install "coda[all]"    # Everything
   ```

3. **No circular dependencies**:
   - Dependency graph is a DAG
   - Core modules depend on nothing
   - Higher modules depend only on lower ones

## Example Module: Theme

To illustrate the approach, here's a complete theme module:

```python
# coda/theme/__init__.py
from .manager import Theme, ThemeManager
from .models import ColorScheme, StyleDefinition

__all__ = ['Theme', 'ThemeManager', 'ColorScheme', 'StyleDefinition']

# coda/theme/manager.py
from typing import Dict, Optional
from pathlib import Path
import json

class Theme:
    """Standalone theme manager for terminal applications."""
    
    def __init__(self, theme_name: str = "default"):
        self.theme_name = theme_name
        self.colors = self._load_theme(theme_name)
    
    def _load_theme(self, name: str) -> Dict[str, str]:
        """Load theme from built-in definitions."""
        themes = {
            "default": {
                "primary": "\033[34m",    # Blue
                "success": "\033[32m",    # Green  
                "error": "\033[31m",      # Red
                "reset": "\033[0m"
            },
            "dark": {
                "primary": "\033[94m",    # Bright Blue
                "success": "\033[92m",    # Bright Green
                "error": "\033[91m",      # Bright Red
                "reset": "\033[0m"
            }
        }
        return themes.get(name, themes["default"])
    
    def style(self, style_name: str, text: str) -> str:
        """Apply style to text."""
        color = self.colors.get(style_name, "")
        reset = self.colors.get("reset", "")
        return f"{color}{text}{reset}"

# coda/theme/example.py
#!/usr/bin/env python3
"""Standalone theme example - no other coda imports needed."""

from coda.theme import Theme

# Or if copy-pasted: from theme import Theme

def main():
    # Create theme
    theme = Theme("dark")
    
    # Use it
    print(theme.style("success", "✓ This works standalone!"))
    print(theme.style("error", "✗ Errors look like this"))
    print(theme.style("primary", "→ Primary information"))

if __name__ == "__main__":
    main()
```

## Next Steps

1. **Review and refine this plan** based on your feedback
2. **Start with Phase 1** modules (constants, config, theme)  
3. **Create standalone examples** to verify independence
4. **Build up to full integration** in the CLI

This approach gives you:
- True modularity 
- Copy-paste ability
- Minimal dependencies
- Progressive enhancement
- Clean, simple APIs

Does this plan better match your vision for Coda?