# Web UI Tests

This directory contains comprehensive tests for the Coda Assistant Web UI built with Streamlit.

## Test Structure

```
tests/web/
├── unit/               # Unit tests for individual components
│   ├── components/     # Tests for UI components
│   ├── utils/         # Tests for utility functions
│   └── pages/         # Tests for page modules
├── integration/       # Integration tests for component interactions
├── functional/        # End-to-end user workflow tests
├── performance/       # Performance and load tests
├── fixtures/          # Test fixtures and mock data
├── conftest.py        # Pytest configuration and fixtures
├── pytest.ini         # Pytest settings
└── run_tests.sh      # Local test runner script
```

## Running Tests

### Quick Start

Run all tests:
```bash
./tests/web/run_tests.sh
```

### Run Specific Test Types

```bash
# Unit tests only (no browser required)
./tests/web/run_tests.sh --type unit

# Integration tests only
./tests/web/run_tests.sh --type integration

# Functional tests only
./tests/web/run_tests.sh --type functional

# All tests
./tests/web/run_tests.sh --type all
```

### Browser Options

```bash
# Use Chrome (default)
./tests/web/run_tests.sh --browser chrome

# Use Firefox
./tests/web/run_tests.sh --browser firefox

# Run in headed mode (see browser)
./tests/web/run_tests.sh --headed
```

### Direct pytest Commands

```bash
# Run unit tests
pytest tests/web/unit/ -v

# Run integration tests with specific browser
BROWSER=firefox pytest tests/web/integration/ -v

# Run tests with coverage
pytest tests/web/unit/ --cov=coda.web --cov-report=html

# Run specific test file
pytest tests/web/unit/components/test_chat_widget.py -v

# Run tests matching pattern
pytest tests/web/ -k "test_chat" -v
```

## Test Categories

### Unit Tests
- Test individual components in isolation
- Mock external dependencies
- Fast execution
- No browser or server required

### Integration Tests
- Test component interactions
- Require running Streamlit server
- Use Selenium for browser automation
- Test real user interactions

### Functional Tests
- Complete user workflows
- End-to-end scenarios
- Error handling and edge cases
- Multi-step processes

### Performance Tests
- Load testing with multiple users
- Response time measurements
- Resource usage monitoring
- Scalability testing

## Writing Tests

### Unit Test Example

```python
from unittest.mock import Mock, patch
import pytest
from coda.web.components.chat_widget import render_chat_widget

def test_render_empty_chat(mock_streamlit):
    """Test rendering with no messages."""
    mock_streamlit['session_state'].messages = []
    
    render_chat_widget()
    
    # Verify welcome message is displayed
    mock_streamlit['markdown'].assert_called()
```

### Integration Test Example

```python
def test_send_message(web_server, driver, base_url):
    """Test sending a message in chat."""
    driver.get(f"{base_url}")
    
    # Navigate to chat
    chat_tab = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Chat')]"))
    )
    chat_tab.click()
    
    # Send message
    chat_input = driver.find_element(By.XPATH, "//textarea[@data-testid='stChatInput']")
    chat_input.send_keys("Hello, world!")
    chat_input.send_keys(Keys.RETURN)
    
    # Verify message appears
    messages = driver.find_elements(By.XPATH, "//div[@data-testid='stChatMessage']")
    assert len(messages) > 0
```

## CI/CD Integration

Tests run automatically on:
- Push to main, develop, or feature branches
- Pull requests
- Manual workflow dispatch

GitHub Actions workflow: `.github/workflows/test-web-ui.yml`

## Dependencies

Required packages:
- pytest
- selenium
- streamlit
- pytest-timeout
- pytest-cov

Install all test dependencies:
```bash
pip install -r requirements-test.txt
```

## Troubleshooting

### Common Issues

1. **Server won't start**: Check if port is already in use
   ```bash
   lsof -i:8600
   ```

2. **Browser tests fail**: Ensure drivers are installed
   ```bash
   # Chrome
   brew install chromedriver
   
   # Firefox
   brew install geckodriver
   ```

3. **Timeout errors**: Increase timeout in pytest.ini or use --timeout flag

4. **Flaky tests**: Mark with @pytest.mark.flaky and investigate

### Debug Mode

Run tests with more verbose output:
```bash
pytest tests/web/ -vv --tb=long --capture=no
```

View Streamlit server logs:
```bash
tail -f tests/web/logs/streamlit.log
```

## Coverage Reports

Generate coverage report:
```bash
pytest tests/web/unit/ --cov=coda.web --cov-report=html
open htmlcov/index.html
```

## Best Practices

1. **Keep tests independent** - Each test should be runnable in isolation
2. **Use fixtures** - Share common setup code via conftest.py
3. **Mock external dependencies** - Unit tests shouldn't need real APIs
4. **Use meaningful assertions** - Be specific about what you're testing
5. **Handle timing issues** - Use WebDriverWait instead of sleep()
6. **Clean up resources** - Kill servers, close browsers, delete temp files
7. **Document flaky tests** - Mark and investigate intermittent failures

## Contributing

When adding new features:
1. Write unit tests first (TDD approach)
2. Add integration tests for UI interactions
3. Include functional tests for complete workflows
4. Update this README if needed
5. Ensure all tests pass locally before pushing