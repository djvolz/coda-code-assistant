# Coda Test Suite

This test suite validates the modular architecture of Coda, ensuring proper separation of concerns and module independence.

## Test Structure

```
tests/
├── base/                    # Tests for base layer modules
│   ├── test_module_independence.py   # Verifies no forbidden imports
│   ├── test_standalone_imports.py    # Tests modules work in isolation
│   └── README.md                     # Base layer test documentation
├── services/               # Tests for service layer
│   └── test_service_layer.py        # Service integration tests
├── apps/                   # Tests for application layer
│   └── test_cli_integration.py      # CLI functionality tests
├── integration/            # Full-stack integration tests
│   └── test_full_stack.py           # End-to-end workflows
└── archive/               # Old tests for reference
    └── old_tests/         # Pre-refactoring test suite
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
uv run pytest tests/ -v

# Run specific layer tests
uv run pytest tests/base/ -v
uv run pytest tests/services/ -v
uv run pytest tests/apps/ -v
uv run pytest tests/integration/ -v

# Run with coverage
uv run pytest tests/ --cov=coda --cov-report=html

# Run module independence tests only
uv run pytest tests/base/test_module_independence.py -v

# Run standalone import tests only
uv run pytest tests/base/test_standalone_imports.py -v
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

## Key Findings and Fixes

During test development, several architectural issues were identified and fixed:

1. **Session Module MVC Violation**: 
   - **Issue**: SessionCommands was in base layer but contained UI logic
   - **Fix**: Moved to CLI layer (apps/cli/session_commands.py)

2. **Hard Dependencies in Base Layer**:
   - **Issue**: Context module required tiktoken
   - **Fix**: Made tiktoken optional with graceful fallback

3. **Import Structure**:
   - **Issue**: Circular dependencies and layer violations
   - **Fix**: Enforced strict layering with test validation

## Coverage Goals

- Base modules: 90%+ coverage
- Service modules: 80%+ coverage
- Application modules: 70%+ coverage
- Critical paths: 100% coverage

## Test Status

✅ **Base Layer Tests**: All passing
- Module independence: 8/8 tests
- Standalone imports: 7/7 tests

✅ **Service Layer Tests**: All passing
- Service dependencies: 6/6 tests

✅ **Apps Layer Tests**: All passing
- CLI integration: 9/9 tests

✅ **Integration Tests**: All passing
- Full stack workflows: 8/8 tests

**Total**: 38 tests, all passing