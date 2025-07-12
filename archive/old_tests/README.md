# Coda Test Suite Documentation

This directory contains all tests for the Coda project, organized following modern Python testing best practices for CI/CD pipelines.

## Overview

The test suite is designed with a layered approach:
- **Fast unit tests** run on every commit
- **Integration tests** run on main branch or when explicitly requested
- **Functional tests** verify end-to-end workflows
- **Smoke tests** quickly verify basic functionality

## Test Structure

```
tests/
├── unit/                    # Fast unit tests (no external dependencies)
│   ├── test_oci_parsing.py  # OCI response parsing tests
│   └── test_oci_response_parsing.py
├── integration/             # Integration tests (require credentials/services)
│   └── test_oci_genai_integration.py
├── functional/              # End-to-end functional tests
│   └── test_oci_genai_functional.py
├── test_smoke.py            # Quick smoke tests for CI
├── test_oci_genai_basic.py  # Basic OCI GenAI tests
├── test_interactive_mode.py # Interactive CLI mode tests
├── conftest.py              # Shared pytest fixtures
└── README.md                # This file
```

## How It Works

### 1. Test Discovery and Execution

Pytest automatically discovers tests following these patterns:
- Files: `test_*.py` or `*_test.py`
- Classes: `Test*`
- Functions: `test_*`

### 2. Test Markers

Tests are tagged with markers to control execution:

```python
@pytest.mark.unit        # Fast tests without external dependencies
@pytest.mark.integration # Tests requiring external services
@pytest.mark.functional  # End-to-end tests
@pytest.mark.slow        # Long-running tests
```

### 3. CI/CD Integration

The GitHub Actions workflow (`.github/workflows/test.yml`) runs tests in stages:

1. **On every push/PR**: Unit tests only
   ```bash
   pytest tests/ -v -m "unit or not integration"
   ```

2. **On main branch**: Integration tests (if secrets configured)
   ```bash
   pytest tests/ -v -m integration
   ```

3. **Manual trigger**: Include `[integration]` in commit message

### 4. Configuration

Test configuration is in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "unit: Unit tests (fast, no external dependencies)",
    "integration: Integration tests (requires OCI credentials)",
    # ...
]
```

## Running Tests Locally

### Using Make (Recommended)

```bash
make test          # Run unit tests only (fast, for CI)
make test-all      # Run all tests including integration
make test-unit     # Run only unit tests
make test-integration # Run integration tests (needs credentials)
make test-cov      # Run with coverage report
make test-fast     # Run smoke tests only
```

### Using pytest directly

```bash
# Run all tests
uv run pytest tests/

# Run only unit tests
uv run pytest tests/ -m unit

# Run tests with coverage
uv run pytest tests/ --cov=coda --cov-report=html

# Run specific test file
uv run pytest tests/test_smoke.py -v

# Run tests matching pattern
uv run pytest tests/ -k "parsing"
```

## Test Categories Explained

### Unit Tests (`@pytest.mark.unit`)
- **Purpose**: Test individual functions/classes in isolation
- **Speed**: Fast (< 1 second per test)
- **Dependencies**: None (all external deps mocked)
- **Example**: `test_oci_parsing.py` - Tests JSON parsing logic

### Integration Tests (`@pytest.mark.integration`)
- **Purpose**: Test interaction with real external services
- **Speed**: Slower (network calls)
- **Dependencies**: Requires credentials (OCI_COMPARTMENT_ID)
- **Example**: `test_oci_genai_integration.py` - Tests actual OCI API

### Functional Tests (`@pytest.mark.functional`)
- **Purpose**: Test complete user workflows
- **Speed**: Slowest
- **Dependencies**: Full application setup
- **Example**: CLI command execution, end-to-end scenarios

### Smoke Tests
- **Purpose**: Quick sanity checks
- **Speed**: Very fast
- **Dependencies**: Minimal
- **Example**: `test_smoke.py` - Verifies imports and basic CLI

## Writing New Tests

### 1. Choose the Right Category

```python
# Unit test example
@pytest.mark.unit
def test_parse_response():
    """Test response parsing without external dependencies."""
    response = {"message": {"content": [{"text": "Hello"}]}}
    assert parse_content(response) == "Hello"

# Integration test example  
@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("OCI_COMPARTMENT_ID"), 
                    reason="No credentials")
def test_real_api_call(provider):
    """Test with actual OCI service."""
    response = provider.chat(messages, model="real-model")
    assert response.content
```

### 2. Use Fixtures for Setup

```python
@pytest.fixture
def mock_response():
    """Provide mock response data."""
    return {"status": "success", "data": [...]}

def test_with_fixture(mock_response):
    assert mock_response["status"] == "success"
```

### 3. Skip Tests When Appropriate

```python
@pytest.mark.skipif(sys.platform == "win32", 
                    reason="Not supported on Windows")
def test_unix_only_feature():
    pass
```

## Coverage

Test coverage is tracked using pytest-cov:

```bash
# Generate coverage report
make test-cov

# View HTML report
open htmlcov/index.html
```

Coverage configuration in `pyproject.toml`:
- Minimum coverage: Aim for >80% for new code
- Excluded: Test files, type checking blocks

## CI/CD Pipeline

### GitHub Actions Workflow

1. **Matrix Testing**: Tests run on Python 3.11, 3.12, and 3.13
2. **Caching**: Dependencies cached for faster runs
3. **Coverage**: Uploaded to Codecov on successful runs
4. **Integration Tests**: Run conditionally based on:
   - Branch (main only)
   - Commit message contains `[integration]`
   - Secrets are configured

### Running Tests in CI

The CI environment sets `CI=true`, which affects:
- Integration test skipping
- Output formatting
- Timeout values

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure `uv sync --all-extras` has been run
2. **Integration test failures**: Check credentials are set
3. **Flaky tests**: Use `@pytest.mark.flaky(reruns=3)`
4. **Slow tests**: Add `@pytest.mark.slow` and skip in CI

### Debug Commands

```bash
# Run with verbose output
pytest -vv tests/

# Show print statements
pytest -s tests/

# Debug on failure
pytest --pdb tests/

# Run last failed
pytest --lf tests/
```

## Best Practices

1. **Keep unit tests fast**: Mock external dependencies
2. **Use descriptive names**: `test_parse_cohere_response_with_empty_content`
3. **One assertion per test**: Makes failures clear
4. **Use fixtures**: Don't repeat setup code
5. **Mark tests appropriately**: Helps with test selection
6. **Clean up**: Ensure tests don't leave artifacts

## Environment Variables

- `CI`: Set by GitHub Actions
- `RUN_INTEGRATION_TESTS`: Enable integration tests in CI
- `OCI_COMPARTMENT_ID`: Required for OCI integration tests
- `SKIP_SLOW_TESTS`: Skip tests marked as slow

Run unit and mocked tests (no credentials required):
```bash
./run_tests.sh
```

### Run Specific Test Types

```bash
# Unit tests only
uv run pytest tests/unit/ -v

# Mocked tests only (CI/CD safe)
uv run pytest tests/test_oci_genai_mocked.py -v

# Integration tests (requires OCI credentials)
RUN_INTEGRATION=true ./run_tests.sh

# Functional tests (requires OCI credentials and expect)
RUN_FUNCTIONAL=true ./run_tests.sh

# All tests
RUN_INTEGRATION=true RUN_FUNCTIONAL=true ./run_tests.sh
```

### Using pytest directly

```bash
# Run with markers
uv run pytest -m unit           # Unit tests only
uv run pytest -m integration --run-integration  # Integration tests
uv run pytest -m functional --run-functional    # Functional tests

# Run with coverage
uv run pytest tests/ --cov=coda.providers.oci_genai --cov-report=html

# Run specific test
uv run pytest tests/unit/test_oci_genai_provider.py::TestOCIGenAIProvider::test_streaming_response_parsing_xai -v
```

## Test Categories

### Unit Tests
- Test individual methods with mocked dependencies
- No network calls or external dependencies
- Fast execution
- Always run in CI/CD

### Mocked Tests
- Full workflow tests with mocked OCI responses
- Test different model formats (xAI, Cohere, Meta)
- CI/CD safe - no credentials required
- Comprehensive coverage of streaming logic

### Integration Tests
- Test actual OCI GenAI API calls
- Require valid OCI credentials
- Test real model discovery and chat completions
- Skip in CI/CD unless secrets are configured

### Functional Tests
- End-to-end tests through the CLI
- Test interactive mode with expect scripts
- Test concurrent requests and error handling
- Most comprehensive but slowest

## Environment Setup

### For Integration/Functional Tests

1. Set up OCI credentials:
```bash
export OCI_COMPARTMENT_ID="your-compartment-id"
# Ensure ~/.oci/config is properly configured
```

2. Install expect (for functional tests):
```bash
# macOS
brew install expect

# Ubuntu/Debian
sudo apt-get install expect

# RHEL/CentOS
sudo yum install expect
```

## CI/CD Configuration

The GitHub Actions workflow (`.github/workflows/test-oci-genai.yml`) runs:
1. Unit and mocked tests on every push/PR
2. Integration tests on main branch (if secrets configured)
3. Coverage reporting with codecov

To enable integration tests in CI/CD, set these secrets:
- `OCI_COMPARTMENT_ID`
- `OCI_CONFIG_FILE`
- `OCI_KEY_FILE`

## Writing New Tests

### Adding Unit Tests
```python
def test_new_feature(self, provider):
    """Test description."""
    # Arrange
    mock_response = Mock(...)
    provider.some_method = Mock(return_value=mock_response)
    
    # Act
    result = provider.new_feature()
    
    # Assert
    assert result == expected_value
```

### Adding Integration Tests
```python
@pytest.mark.integration
def test_real_api_call(self, provider):
    """Test with real OCI API."""
    # Will be skipped unless --run-integration is passed
    response = provider.chat(messages, model="real-model")
    assert response.content
```

## Debugging Tests

```bash
# Run with verbose output
uv run pytest -vv

# Show print statements
uv run pytest -s

# Drop into debugger on failure
uv run pytest --pdb

# Run last failed tests
uv run pytest --lf
```

## Test Coverage Goals

- Unit tests: >90% coverage of core logic
- Integration tests: Cover all model providers
- Functional tests: Cover main user workflows
- Edge cases: Error handling, timeouts, malformed responses