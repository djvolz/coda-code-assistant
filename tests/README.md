# OCI GenAI Provider Tests

This directory contains comprehensive tests for the OCI GenAI provider implementation.

## Test Structure

```
tests/
├── unit/                    # Unit tests with mocks
│   └── test_oci_genai_provider.py
├── integration/             # Integration tests (require OCI credentials)
│   └── test_oci_genai_integration.py
├── functional/              # End-to-end functional tests
│   └── test_oci_genai_functional.py
├── test_oci_genai_mocked.py # CI/CD-safe mocked tests
├── test_interactive_mode.py  # Interactive mode tests
├── conftest.py              # Shared fixtures and configuration
└── README.md                # This file
```

## Running Tests

### Quick Start

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