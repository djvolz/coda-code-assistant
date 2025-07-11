# Coda Test Suite

This test suite validates the modular architecture of Coda, ensuring proper separation of concerns and module independence.

## Test Structure

```
tests/
├── base/           # Tests for base modules (must be independent)
├── services/       # Tests for service modules
├── apps/           # Tests for application modules
└── integration/    # End-to-end integration tests
```

## Key Testing Principles

### 1. Module Independence Tests (base/)

Base modules MUST NOT import from:
- `coda.services.*`
- `coda.apps.*`
- Any external dependencies not in their requirements

Each base module test includes:
- Import validation tests
- Standalone functionality tests
- Zero-dependency verification

### 2. Service Integration Tests (services/)

Service modules can import from:
- `coda.base.*` modules
- Other service dependencies

Tests verify:
- Proper integration of base modules
- Service-level functionality
- Cross-service interactions

### 3. Application Tests (apps/)

Application modules can import from:
- `coda.base.*` modules
- `coda.services.*` modules

Tests verify:
- UI functionality
- User workflows
- Configuration management

### 4. Integration Tests (integration/)

End-to-end tests that verify:
- Complete user workflows
- Cross-layer interactions
- Performance and reliability

## Running Tests

```bash
# Run all tests
pytest

# Run specific layer tests
pytest tests/base/
pytest tests/services/
pytest tests/apps/

# Run with coverage
pytest --cov=coda tests/

# Run module independence tests only
pytest tests/base/test_*_independence.py
```

## Module Independence Verification

The most critical tests are the independence tests in `tests/base/`. These ensure:

1. **Import Independence**: Base modules don't import from higher layers
2. **Dependency Independence**: Base modules only use allowed dependencies
3. **Functional Independence**: Base modules work in isolation

Example:
```python
def test_config_module_independence():
    """Ensure config module has no service/app dependencies."""
    import coda.base.config
    
    # Check no forbidden imports
    assert not has_import(coda.base.config, "coda.services")
    assert not has_import(coda.base.config, "coda.apps")
    
    # Verify it works standalone
    config = Config()
    assert config.get("test", "default") == "default"
```

## Test Guidelines

1. **Keep tests focused**: One test per concept
2. **Use fixtures**: Share common setup via pytest fixtures
3. **Mock external dependencies**: Don't rely on external services
4. **Test edge cases**: Include error conditions and boundaries
5. **Document complex tests**: Add docstrings explaining the why

## Coverage Goals

- Base modules: 90%+ coverage
- Service modules: 80%+ coverage
- Application modules: 70%+ coverage
- Critical paths: 100% coverage