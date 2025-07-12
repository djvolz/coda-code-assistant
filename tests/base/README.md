# Base Module Tests

This directory contains tests for the base layer modules to ensure they maintain proper independence and functionality.

## Test Files

### test_module_independence.py
Tests that base modules don't import from higher layers (services or apps).

- **Purpose**: Ensures architectural integrity by preventing base modules from depending on higher layers
- **What it checks**:
  - No imports from `coda.services.*` in base modules
  - No imports from `coda.apps.*` in base modules
  - No circular dependencies between base modules
  - All expected base modules are present

### test_standalone_imports.py
Tests that each base module can be imported and used in isolation.

- **Purpose**: Ensures base modules can be copy-pasted to other projects and work independently
- **What it checks**:
  - Each module can be imported in a fresh Python process
  - Basic functionality works without other Coda modules
  - External dependencies are properly handled (e.g., tiktoken is optional)

## Base Modules Tested

1. **config** - Configuration management with TOML/JSON/YAML support
2. **theme** - Theme management for console output
3. **providers** - LLM provider abstractions
4. **session** - Session and conversation management
5. **search** - Code intelligence and repository analysis
6. **observability** - Metrics, tracing, and monitoring

## Running the Tests

```bash
# Run all base module tests
uv run pytest tests/base/ -v

# Run only independence tests
uv run pytest tests/base/test_module_independence.py -v

# Run only standalone import tests
uv run pytest tests/base/test_standalone_imports.py -v
```

## Key Findings Fixed

1. **Session module** was importing `CommandRegistry` from the apps layer - moved `SessionCommands` to CLI layer
2. **Context module** had hard dependency on tiktoken - made it optional with graceful fallback
3. **Test improvements**:
   - Fixed overly strict import checking that was filtering out legitimate dependencies
   - Updated tests to use correct class names and initialization parameters
   - Made tests more realistic by testing actual functionality, not just imports