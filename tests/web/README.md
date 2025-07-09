# Web UI Tests

This directory contains comprehensive tests for the Coda Assistant Streamlit web UI.

## Test Structure

```
tests/web/
├── unit/          # Fast, isolated component tests
├── integration/   # Browser-based integration tests
├── functional/    # End-to-end user workflow tests
├── fixtures/      # Test data and utilities
├── conftest.py    # Shared pytest fixtures
├── pytest.ini     # Pytest configuration
└── README.md      # This file
```

## Running Tests

### Prerequisites

```bash
# Install test dependencies
uv pip install -e ".[test-web]"

# For browser tests, install browser drivers
# Chrome
brew install chromedriver  # macOS
# or
sudo apt-get install chromium-chromedriver  # Ubuntu

# Firefox
brew install geckodriver  # macOS
# or
sudo apt-get install firefox-geckodriver  # Ubuntu
```

### Unit Tests (Fast)

```bash
# Run all unit tests
pytest tests/web/unit/ -v

# Run with coverage
pytest tests/web/unit/ --cov=coda.web --cov-report=html

# Run specific test file
pytest tests/web/unit/pages/test_chat_page.py -v

# Run tests matching pattern
pytest tests/web/unit/ -k "chat" -v
```

### Integration Tests (Browser)

```bash
# Run with Chrome
pytest tests/web/integration/ --browser=chrome -v

# Run with Firefox
pytest tests/web/integration/ --browser=firefox -v

# Run headless (no browser window)
pytest tests/web/integration/ --browser=chrome --headless -v

# Run specific integration test
pytest tests/web/integration/test_navigation.py -v
```

### Functional Tests (E2E)

```bash
# Run all functional tests
pytest tests/web/functional/ --browser=chrome -v

# Run specific workflow
pytest tests/web/functional/test_user_workflows.py::test_first_time_user_workflow -v
```

### All Tests

```bash
# Run all web tests
pytest tests/web/ -v

# Run with specific markers
pytest tests/web/ -m "not slow" -v
pytest tests/web/ -m "unit" -v
pytest tests/web/ -m "requires_browser" -v
```

## Test Markers

- `@pytest.mark.unit` - Fast unit tests without external dependencies
- `@pytest.mark.integration` - Integration tests requiring browser/server
- `@pytest.mark.functional` - End-to-end functional tests
- `@pytest.mark.slow` - Tests that take more than 10 seconds
- `@pytest.mark.requires_browser` - Tests that need Selenium WebDriver

## Writing Tests

### Unit Tests

Use Streamlit's `AppTest` for fast, headless testing:

```python
from streamlit.testing.v1 import AppTest

def test_chat_page():
    at = AppTest.from_file("coda/web/app.py")
    at.run()
    
    # Navigate to chat
    at.radio[0].set_value("💬 Chat").run()
    
    # Interact with widgets
    at.text_input[0].set_value("Hello").run()
    
    # Verify state
    assert at.session_state["messages"][-1]["content"] == "Hello"
```

### Integration Tests

Use Selenium for browser-based testing:

```python
def test_navigation(driver, streamlit_server):
    driver.get(streamlit_server)
    
    chat_link = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//span[text()='💬 Chat']"))
    )
    chat_link.click()
    
    # Verify page loaded
    assert "Chat" in driver.title
```

## CI/CD Integration

Tests run automatically on GitHub Actions:

- Unit tests run on every push
- Browser tests run on PRs and main branch
- Multiple browser matrix (Chrome, Firefox)
- Coverage reports uploaded to Codecov

## Debugging Tips

1. **Save screenshots on failure**:
   ```python
   def test_something(driver):
       try:
           # test code
       except:
           driver.save_screenshot("failure.png")
           raise
   ```

2. **Run tests with more output**:
   ```bash
   pytest tests/web/ -vv -s --tb=long
   ```

3. **Run single test with debugging**:
   ```bash
   pytest tests/web/unit/test_app.py::test_app_runs -vv --pdb
   ```

4. **Check Streamlit logs**:
   ```bash
   STREAMLIT_LOG_LEVEL=debug pytest tests/web/integration/ -v
   ```

## Performance Testing (Optional)

```bash
# Install performance testing tools
uv pip install -e ".[performance]"

# Run benchmark tests
pytest tests/web/performance/ --benchmark-only

# Run load tests with Locust
locust -f tests/web/performance/locustfile.py
```