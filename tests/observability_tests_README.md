# Observability Test Suite

This directory contains comprehensive tests for the Coda observability and telemetry system.

## Test Structure

```
tests/
├── unit/                      # Fast, isolated unit tests
│   ├── observability/         # Tests for observability components
│   │   ├── test_base.py      # Base component tests
│   │   ├── test_storage.py   # Storage backend tests
│   │   ├── test_collections.py # Memory-aware collections tests
│   │   ├── test_sanitizer.py # Data sanitizer tests
│   │   ├── test_scheduler.py # Task scheduler tests
│   │   ├── test_security.py  # Security utilities tests
│   │   ├── test_manager.py   # ObservabilityManager tests
│   │   ├── test_metrics.py   # MetricsCollector tests
│   │   ├── test_tracing.py   # TracingManager tests
│   │   ├── test_health.py    # HealthMonitor tests
│   │   └── test_error_tracker.py # ErrorTracker tests
│   ├── cli/
│   │   └── test_observability_commands.py # CLI command tests
│   └── test_configuration.py # Configuration enhancements tests
├── integration/               # Tests requiring system integration
│   └── observability/
│       ├── test_full_stack.py # Full observability stack tests
│       └── test_cli_integration.py # CLI integration tests
└── functional/                # End-to-end workflow tests
    └── test_observability_workflows.py # Complete workflow scenarios
```

## Running Tests

### Quick Start

Run all observability tests:
```bash
./scripts/test_observability.sh
```

### Specific Test Types

Run only unit tests:
```bash
./scripts/test_observability.sh --unit
```

Run only integration tests:
```bash
./scripts/test_observability.sh --integration
```

Run only functional tests:
```bash
./scripts/test_observability.sh --functional
```

Generate coverage report only:
```bash
./scripts/test_observability.sh --coverage
```

### Using pytest directly

Run all tests with coverage:
```bash
pytest tests/ -v --cov=coda.observability --cov=coda.cli --cov-report=html
```

Run specific test file:
```bash
pytest tests/unit/observability/test_metrics.py -v
```

Run tests by marker:
```bash
pytest tests/ -m unit          # Unit tests only
pytest tests/ -m integration   # Integration tests only
pytest tests/ -m functional    # Functional tests only
```

## Test Coverage

Current coverage targets:
- **Unit Tests**: 90% coverage for critical components
- **Integration Tests**: 80% coverage for system interactions
- **Overall**: 80% minimum coverage required

View coverage report after running tests:
```bash
open test-results/htmlcov/index.html
```

## CI/CD Integration

Tests run automatically on:
- Every push to main, develop, or feature branches
- Pull requests to main
- When observability-related files are modified

See `.github/workflows/test-observability.yml` for CI configuration.

## Test Markers

- `@pytest.mark.unit` - Fast unit tests without external dependencies
- `@pytest.mark.integration` - Integration tests requiring system setup
- `@pytest.mark.functional` - End-to-end functional tests
- `@pytest.mark.slow` - Long-running tests

## Writing New Tests

### Unit Tests
- Test individual components in isolation
- Mock external dependencies
- Focus on edge cases and error conditions
- Should run in < 1 second each

### Integration Tests
- Test component interactions
- Use real file system and threading
- Verify data flow between components
- May take a few seconds to run

### Functional Tests
- Test complete user workflows
- Simulate real usage scenarios
- Verify end-to-end functionality
- May take longer to execute

## Test Data

- Tests use temporary directories for file operations
- Mock data is generated within tests
- No external test data files required
- All tests clean up after themselves

## Debugging Tests

Run tests with more verbose output:
```bash
pytest tests/unit/observability/test_metrics.py -vv -s
```

Run specific test method:
```bash
pytest tests/unit/observability/test_metrics.py::TestMetricsCollector::test_record_session_event -v
```

Drop into debugger on failure:
```bash
pytest tests/unit/observability/test_metrics.py --pdb
```

## Performance Testing

Performance tests can be triggered with `[perf]` in commit message.
These tests validate:
- Memory usage stays within bounds
- No memory leaks
- Acceptable performance overhead
- Thread pool efficiency