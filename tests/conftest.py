"""Pytest configuration and shared fixtures."""

import os
from unittest.mock import Mock, patch

import pytest


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-integration", action="store_true", default=False, help="Run integration tests"
    )
    parser.addoption(
        "--run-functional", action="store_true", default=False, help="Run functional tests"
    )


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "functional: mark test as functional test")
    config.addinivalue_line("markers", "unit: mark test as unit test")


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on markers."""
    skip_integration = pytest.mark.skip(reason="need --run-integration option to run")
    skip_functional = pytest.mark.skip(reason="need --run-functional option to run")

    for item in items:
        if "integration" in item.keywords and not config.getoption("--run-integration"):
            item.add_marker(skip_integration)
        if "functional" in item.keywords and not config.getoption("--run-functional"):
            item.add_marker(skip_functional)


@pytest.fixture
def mock_oci_config():
    """Mock OCI configuration for testing."""
    return {
        "user": "ocid1.user.oc1..test",
        "fingerprint": "aa:bb:cc:dd:ee:ff:00:11:22:33:44:55:66:77:88:99",
        "tenancy": "ocid1.tenancy.oc1..test",
        "region": "us-phoenix-1",
        "key_file": "/path/to/key.pem",
    }


@pytest.fixture
def mock_oci_models():
    """Mock OCI model responses."""
    return [
        Mock(
            id="ocid1.generativeaimodel.oc1.phx.xai.grok3fast",
            display_name="Grok 3 Fast",
            vendor="xai",
            version="1.0",
            lifecycle_state="ACTIVE",
            capabilities=["TEXT_GENERATION", "CHAT"],
            time_created="2024-01-01T00:00:00Z",
        ),
        Mock(
            id="ocid1.generativeaimodel.oc1.phx.cohere.commandr",
            display_name="Command R",
            vendor="cohere",
            version="1.0",
            lifecycle_state="ACTIVE",
            capabilities=["TEXT_GENERATION", "CHAT"],
            time_created="2024-01-01T00:00:00Z",
        ),
        Mock(
            id="ocid1.generativeaimodel.oc1.phx.meta.llama3",
            display_name="Llama 3.3 70B Instruct",
            vendor="meta",
            version="1.0",
            lifecycle_state="ACTIVE",
            capabilities=["TEXT_GENERATION", "CHAT"],
            time_created="2024-01-01T00:00:00Z",
        ),
    ]


@pytest.fixture
def mock_streaming_events_xai():
    """Mock streaming events for xAI models."""
    events = [
        Mock(data='{"message":{"role":"ASSISTANT","content":[{"type":"TEXT","text":"Hello"}]}}'),
        Mock(data='{"message":{"role":"ASSISTANT","content":[{"type":"TEXT","text":" from"}]}}'),
        Mock(data='{"message":{"role":"ASSISTANT","content":[{"type":"TEXT","text":" xAI"}]}}'),
        Mock(data='{"finishReason":"stop"}'),
    ]
    for event in events:
        event.event = "message"
    return events


@pytest.fixture
def mock_streaming_events_cohere():
    """Mock streaming events for Cohere models."""
    events = [
        Mock(data='{"apiFormat":"COHERE","text":"Hello"}'),
        Mock(data='{"apiFormat":"COHERE","text":" from"}'),
        Mock(data='{"apiFormat":"COHERE","text":" Cohere"}'),
        Mock(data='{"apiFormat":"COHERE","text":"Hello from Cohere","finishReason":"MAX_TOKENS"}'),
    ]
    for event in events:
        event.event = "message"
    return events


@pytest.fixture
def mock_streaming_events_meta():
    """Mock streaming events for Meta models."""
    events = [
        Mock(data='{"message":{"role":"ASSISTANT","content":[{"type":"TEXT","text":"Hello"}]}}'),
        Mock(data='{"message":{"role":"ASSISTANT","content":[{"type":"TEXT","text":" from"}]}}'),
        Mock(data='{"message":{"role":"ASSISTANT","content":[{"type":"TEXT","text":" Meta"}]}}'),
        Mock(data='{"finishReason":"stop"}'),
    ]
    for event in events:
        event.event = "message"
    return events


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory."""
    config_dir = tmp_path / ".config" / "coda"
    config_dir.mkdir(parents=True)

    config_file = config_dir / "config.toml"
    config_file.write_text(
        """
[oci]
compartment_id = "test-compartment-id"

[cli]
default_provider = "oci_genai"
"""
    )

    return config_dir


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    original_env = os.environ.copy()

    test_env = {
        "OCI_COMPARTMENT_ID": "test-compartment-id",
        "OCI_CONFIG_FILE": "~/.oci/config",
        "OCI_CONFIG_PROFILE": "DEFAULT",
    }

    with patch.dict(os.environ, test_env):
        yield test_env

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def capture_streaming_output():
    """Helper to capture streaming output."""

    class StreamCapture:
        def __init__(self):
            self.chunks = []
            self.finished = False

        def add_chunk(self, chunk):
            self.chunks.append(chunk)
            if chunk.finish_reason:
                self.finished = True

        def get_full_response(self):
            return "".join(chunk.content for chunk in self.chunks)

        def get_chunk_count(self):
            return len(self.chunks)

    return StreamCapture()
