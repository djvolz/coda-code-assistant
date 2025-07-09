# Streamlit Testing Strategy for Coda Web UI

This document outlines the comprehensive testing strategy for the Coda Streamlit web UI, based on industry best practices and patterns from major Streamlit projects.

## Overview

Our testing approach combines multiple testing methodologies to ensure comprehensive coverage:
- **Unit Testing**: Fast, isolated component tests using mocks
- **Integration Testing**: Browser-based testing with Selenium
- **Functional Testing**: End-to-end user workflow validation
- **Performance Testing**: Load and benchmark testing (optional)

## Testing Frameworks and Tools

### Core Dependencies
```toml
[tool.poetry.dev-dependencies]
pytest = "^8.0"
pytest-cov = "^4.0"
pytest-selenium = "^4.0"
pytest-timeout = "^2.0"
pytest-asyncio = "^0.21"
selenium = "^4.0"
```

### Optional Performance Testing
```toml
pytest-benchmark = "^4.0"
locust = "^2.0"
```

## Testing Approaches

### 1. Streamlit Native Testing (Recommended for Unit Tests)

Streamlit provides `streamlit.testing.v1.AppTest` for headless testing:

```python
from streamlit.testing.v1 import AppTest

def test_chat_page():
    """Test chat page renders correctly."""
    at = AppTest.from_file("coda/web/app.py")
    at.run()
    
    # Navigate to chat page
    at.radio[0].set_value("💬 Chat").run()
    
    # Verify page loaded
    assert not at.exception
    assert "Chat Interface" in at.title[0].value
    
    # Test widget interaction
    at.selectbox[0].select("openai").run()
    assert at.session_state["current_provider"] == "openai"
```

**Benefits:**
- No browser required - runs in CI/CD easily
- Direct access to session state
- Fast execution (10-100x faster than Selenium)
- Deterministic behavior

### 2. Mock-Based Unit Testing (Current Approach)

For testing individual components in isolation:

```python
@pytest.fixture
def mock_streamlit():
    """Mock Streamlit components."""
    with patch('module.st') as mock_st:
        mock_st.session_state = Mock()
        mock_st.selectbox = Mock(return_value="default")
        yield mock_st

def test_model_selector(mock_streamlit):
    """Test model selector component."""
    result = render_model_selector("openai")
    
    mock_streamlit.selectbox.assert_called_once()
    assert result == "default"
```

### 3. Selenium-Based Integration Testing

For browser-based testing of complex interactions:

```python
@pytest.fixture
def streamlit_app(unused_tcp_port):
    """Start Streamlit server."""
    port = unused_tcp_port
    process = subprocess.Popen([
        "streamlit", "run", "coda/web/app.py",
        "--server.port", str(port),
        "--server.headless", "true"
    ])
    
    # Wait for server to start
    wait_for_server(f"http://localhost:{port}")
    
    yield f"http://localhost:{port}"
    
    process.terminate()
    process.wait()

def test_chat_workflow(streamlit_app, driver):
    """Test complete chat workflow."""
    driver.get(streamlit_app)
    
    # Navigate to chat
    chat_link = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//span[text()='💬 Chat']"))
    )
    chat_link.click()
    
    # Send message
    chat_input = driver.find_element(By.CSS_SELECTOR, "[data-testid='chat-input']")
    chat_input.send_keys("Hello")
    chat_input.send_keys(Keys.RETURN)
    
    # Verify response
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'assistant')]"))
    )
```

## Test Organization

```
tests/web/
├── unit/                    # Fast, isolated tests
│   ├── components/         # Component-specific tests
│   │   ├── test_chat_widget.py
│   │   ├── test_model_selector.py
│   │   └── test_file_manager.py
│   ├── pages/             # Page-level tests
│   │   ├── test_chat_page.py
│   │   └── test_settings_page.py
│   └── utils/             # Utility tests
│       └── test_state.py
├── integration/           # Browser-based tests
│   ├── test_navigation.py
│   ├── test_chat_integration.py
│   └── test_provider_integration.py
├── functional/            # End-to-end workflows
│   ├── test_user_workflows.py
│   └── test_error_scenarios.py
├── performance/           # Optional performance tests
│   └── test_load_performance.py
├── fixtures/              # Test data and utilities
│   ├── mock_providers.py
│   └── sample_data.py
├── conftest.py           # Shared fixtures
└── pytest.ini            # Pytest configuration
```

## CI/CD Integration

### GitHub Actions Workflow

```yaml
name: Web UI Tests

on:
  push:
    paths:
      - 'coda/web/**'
      - 'tests/web/**'
  pull_request:

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install --with dev
      - name: Run unit tests
        run: |
          poetry run pytest tests/web/unit/ -v --cov=coda.web

  browser-tests:
    needs: unit-tests
    strategy:
      matrix:
        browser: [chrome, firefox]
        test-type: [integration, functional]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup browser
        uses: browser-actions/setup-${{ matrix.browser }}@v1
      - name: Start Streamlit server
        run: |
          poetry run streamlit run coda/web/app.py &
          SERVER_PID=$!
          echo "SERVER_PID=$SERVER_PID" >> $GITHUB_ENV
      - name: Run tests
        run: |
          poetry run pytest tests/web/${{ matrix.test-type }}/ \
            --browser=${{ matrix.browser }} \
            --junit-xml=results.xml
      - name: Stop server
        if: always()
        run: kill $SERVER_PID || true

  streamlit-app-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: streamlit/streamlit-app-action@v0.0.3
        with:
          app-path: coda/web/app.py
          ruff: true
```

## Best Practices

### 1. Test Isolation
- Each test should be independent
- Use fixtures for common setup
- Clean up session state between tests

### 2. Timing and Waits
```python
# Good: Explicit waits
element = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.ID, "result"))
)

# Bad: Hard-coded sleeps
time.sleep(5)  # Avoid this!
```

### 3. Session State Testing
```python
def test_state_persistence():
    """Test session state persists across reruns."""
    at = AppTest.from_file("app.py")
    
    # Set initial state
    at.session_state["counter"] = 0
    at.run()
    
    # Interact with app
    at.button[0].click().run()
    
    # Verify state changed
    assert at.session_state["counter"] == 1
```

### 4. Error Handling
```python
def test_error_recovery():
    """Test app handles errors gracefully."""
    at = AppTest.from_file("app.py")
    
    # Simulate error condition
    with patch('module.external_api') as mock_api:
        mock_api.side_effect = Exception("API error")
        at.run()
        
        # Verify error message shown
        assert "Error" in at.error[0].value
        assert at.exception is None  # App didn't crash
```

### 5. Mock External Dependencies
```python
@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider responses."""
    with patch('coda.providers.registry.ProviderFactory') as mock:
        provider = Mock()
        provider.chat.return_value = Mock(content="Test response")
        mock.return_value.create.return_value = provider
        yield mock
```

## Coverage Goals

- **Unit Tests**: 80%+ coverage of business logic
- **Integration Tests**: All major user workflows
- **Functional Tests**: Critical user journeys
- **Performance Tests**: Response time < 2s for common operations

## Running Tests

```bash
# All tests
pytest tests/web/ -v

# Unit tests only (fast)
pytest tests/web/unit/ -v

# With coverage
pytest tests/web/ --cov=coda.web --cov-report=html

# Specific browser
pytest tests/web/integration/ --browser=chrome

# Parallel execution
pytest tests/web/ -n 4

# Watch mode for development
pytest-watch tests/web/unit/ -- -v
```

## Future Enhancements

1. **Adopt Streamlit Native Testing**
   - Migrate unit tests to use `AppTest`
   - Reduce dependency on mocks
   - Improve test speed

2. **Visual Regression Testing**
   - Use Percy or similar tools
   - Catch UI regressions automatically

3. **Accessibility Testing**
   - Add axe-core for a11y validation
   - Ensure WCAG compliance

4. **Performance Monitoring**
   - Add lighthouse CI
   - Track bundle size
   - Monitor runtime performance

5. **Contract Testing**
   - Validate API contracts with providers
   - Use Pact or similar tools

## Conclusion

This testing strategy ensures robust coverage while maintaining fast feedback loops. The combination of unit, integration, and functional tests provides confidence in both individual components and complete user workflows.

Key principles:
- Fast unit tests run on every commit
- Browser tests validate critical paths
- CI/CD automates the entire process
- Coverage metrics track progress

By following these patterns, we can maintain high quality while enabling rapid development of the Streamlit web UI.