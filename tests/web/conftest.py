"""Shared pytest fixtures for web UI tests."""

import os
import subprocess
import sys
import time
from unittest.mock import Mock, patch

import pytest
import streamlit as st
from selenium import webdriver
from streamlit.testing.v1 import AppTest

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)


# Utility Functions
def wait_for_server(url: str, timeout: int = 30) -> bool:
    """Wait for Streamlit server to be ready."""
    import requests

    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return True
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(0.5)

    return False


# Mock Fixtures
@pytest.fixture
def mock_streamlit():
    """Mock Streamlit components for unit testing."""
    with patch("streamlit") as mock_st:
        # Mock session state
        mock_st.session_state = {}

        # Mock common components
        mock_st.write = Mock()
        mock_st.error = Mock()
        mock_st.success = Mock()
        mock_st.info = Mock()
        mock_st.warning = Mock()
        mock_st.sidebar = Mock()
        mock_st.columns = Mock(return_value=[Mock(), Mock()])
        mock_st.container = Mock()
        mock_st.expander = Mock()
        mock_st.tabs = Mock(return_value=[Mock(), Mock()])

        # Mock input components
        mock_st.text_input = Mock(return_value="")
        mock_st.text_area = Mock(return_value="")
        mock_st.selectbox = Mock(return_value=None)
        mock_st.multiselect = Mock(return_value=[])
        mock_st.slider = Mock(return_value=0)
        mock_st.number_input = Mock(return_value=0)
        mock_st.checkbox = Mock(return_value=False)
        mock_st.radio = Mock(return_value=None)
        mock_st.button = Mock(return_value=False)
        mock_st.file_uploader = Mock(return_value=None)

        # Mock layout components
        mock_st.set_page_config = Mock()
        mock_st.title = Mock()
        mock_st.header = Mock()
        mock_st.subheader = Mock()
        mock_st.markdown = Mock()

        # Mock data display
        mock_st.dataframe = Mock()
        mock_st.table = Mock()
        mock_st.json = Mock()
        mock_st.code = Mock()

        yield mock_st


@pytest.fixture
def mock_provider_registry():
    """Mock provider registry for testing."""
    with patch("coda.providers.registry.ProviderFactory") as mock_factory:
        # Create mock provider
        mock_provider = Mock()
        mock_provider.name = "test-provider"
        mock_provider.chat = Mock(return_value=Mock(content="Test response"))
        mock_provider.stream_chat = Mock(return_value=iter(["Test", " response"]))

        # Setup factory
        mock_factory.create = Mock(return_value=mock_provider)
        mock_factory.list_providers = Mock(return_value=["openai", "anthropic", "test-provider"])

        yield mock_factory


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing."""
    response = Mock()
    response.content = "This is a test response from the LLM."
    response.model = "test-model"
    response.usage = {"prompt_tokens": 10, "completion_tokens": 20}
    return response


# Streamlit App Test Fixtures
@pytest.fixture
def app_test():
    """Create AppTest instance for Streamlit native testing."""
    # Create a temporary app file for testing
    app_path = os.path.join(project_root, "coda/web/app.py")
    at = AppTest.from_file(app_path)
    return at


@pytest.fixture
def clean_session_state():
    """Clean session state before each test."""
    if hasattr(st, "session_state"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
    yield
    # Cleanup after test
    if hasattr(st, "session_state"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]


# Browser Testing Fixtures
@pytest.fixture(scope="session")
def browser_choice(request):
    """Get browser choice from command line."""
    return request.config.getoption("--browser", default="chrome")


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--browser",
        action="store",
        default="chrome",
        help="Browser to use for testing: chrome or firefox",
    )
    parser.addoption(
        "--headless", action="store_true", default=False, help="Run browser in headless mode"
    )


@pytest.fixture
def driver(request, browser_choice):
    """Create Selenium WebDriver instance."""
    headless = request.config.getoption("--headless")

    if browser_choice == "chrome":
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        driver = webdriver.Chrome(options=options)
    elif browser_choice == "firefox":
        options = webdriver.FirefoxOptions()
        if headless:
            options.add_argument("--headless")
        driver = webdriver.Firefox(options=options)
    else:
        raise ValueError(f"Unsupported browser: {browser_choice}")

    driver.set_window_size(1280, 720)
    driver.implicitly_wait(10)

    yield driver

    driver.quit()


@pytest.fixture
def streamlit_server(unused_tcp_port):
    """Start Streamlit server for integration testing."""
    port = unused_tcp_port
    env = os.environ.copy()
    env["STREAMLIT_SERVER_PORT"] = str(port)
    env["STREAMLIT_SERVER_HEADLESS"] = "true"

    # Start Streamlit process
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            os.path.join(project_root, "coda/web/app.py"),
            "--server.port",
            str(port),
            "--server.headless",
            "true",
            "--server.enableCORS",
            "false",
            "--server.enableXsrfProtection",
            "false",
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to start
    server_url = f"http://localhost:{port}"
    if not wait_for_server(server_url):
        process.terminate()
        raise RuntimeError("Streamlit server failed to start")

    yield server_url

    # Cleanup
    process.terminate()
    process.wait(timeout=5)


# Test Data Fixtures
@pytest.fixture
def sample_chat_messages():
    """Sample chat messages for testing."""
    return [
        {"role": "user", "content": "Hello, how are you?"},
        {"role": "assistant", "content": "I'm doing well, thank you! How can I help you today?"},
        {"role": "user", "content": "Can you explain what Streamlit is?"},
        {
            "role": "assistant",
            "content": "Streamlit is an open-source Python library that makes it easy to create web applications for data science and machine learning projects.",
        },
    ]


@pytest.fixture
def sample_provider_config():
    """Sample provider configuration for testing."""
    return {
        "openai": {"api_key": "test-api-key", "model": "gpt-4", "temperature": 0.7},
        "anthropic": {"api_key": "test-api-key", "model": "claude-3", "max_tokens": 1000},
    }


@pytest.fixture
def mock_file_upload():
    """Mock file upload for testing."""
    mock_file = Mock()
    mock_file.name = "test_file.txt"
    mock_file.type = "text/plain"
    mock_file.size = 1024
    mock_file.read = Mock(return_value=b"Test file content")
    return mock_file


# Performance Testing Fixtures
@pytest.fixture
def benchmark_timer():
    """Simple timer for performance benchmarking."""

    class Timer:
        def __init__(self):
            self.times = []

        def __enter__(self):
            self.start = time.time()
            return self

        def __exit__(self, *args):
            self.times.append(time.time() - self.start)

        def average(self):
            return sum(self.times) / len(self.times) if self.times else 0

    return Timer()


# Helper fixtures for common test scenarios
@pytest.fixture
def authenticated_session(mock_streamlit):
    """Mock authenticated session state."""
    mock_streamlit.session_state.update(
        {
            "authenticated": True,
            "user_id": "test-user",
            "current_provider": "openai",
            "messages": [],
        }
    )
    return mock_streamlit


@pytest.fixture
def chat_session_with_history(authenticated_session, sample_chat_messages):
    """Mock session with chat history."""
    authenticated_session.session_state["messages"] = sample_chat_messages
    return authenticated_session
