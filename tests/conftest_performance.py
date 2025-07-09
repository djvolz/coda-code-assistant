"""Performance optimizations for pytest fixtures.

This module provides optimized fixtures that reduce test setup time
by using appropriate scopes and caching strategies.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from coda.providers.mock_provider import MockProvider
from coda.configuration import ConfigManager


@pytest.fixture(scope="session")
def mock_provider():
    """Session-scoped mock provider for tests.
    
    Reuses the same mock provider instance across all tests in a session,
    reducing initialization overhead.
    """
    return MockProvider()


@pytest.fixture(scope="session")
def temp_dir_session():
    """Session-scoped temporary directory.
    
    Creates a temporary directory that persists for the entire test session.
    Useful for tests that can share temporary files.
    """
    temp_dir = tempfile.mkdtemp(prefix="coda_test_")
    yield Path(temp_dir)
    # Cleanup after all tests
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="module")
def config_manager_module(tmp_path_factory):
    """Module-scoped configuration manager.
    
    Creates a configuration manager that persists for all tests in a module,
    reducing repeated file I/O operations.
    """
    config_dir = tmp_path_factory.mktemp("config")
    config_file = config_dir / "config.toml"
    return ConfigManager(config_file)


@pytest.fixture
def fast_mock_provider(mock_provider):
    """Fast mock provider that reuses session instance.
    
    This fixture provides test isolation while reusing the underlying
    provider instance for performance.
    """
    # Reset any state if needed
    mock_provider._conversation_history.clear()
    return mock_provider


# Performance monitoring fixtures
@pytest.fixture(scope="session")
def performance_tracker():
    """Track test performance metrics across the session."""
    metrics = {
        "slow_tests": [],
        "fixture_times": {},
        "total_time": 0
    }
    yield metrics
    
    # Report slow tests at end of session
    if metrics["slow_tests"]:
        print("\n\nSlow Tests Report:")
        print("==================")
        for test_name, duration in sorted(metrics["slow_tests"], 
                                        key=lambda x: x[1], 
                                        reverse=True)[:10]:
            print(f"{test_name}: {duration:.2f}s")


@pytest.fixture(autouse=True)
def track_test_duration(request, performance_tracker):
    """Automatically track duration of each test."""
    import time
    start_time = time.time()
    
    yield
    
    duration = time.time() - start_time
    if duration > 0.5:  # Track tests slower than 500ms
        test_name = request.node.nodeid
        performance_tracker["slow_tests"].append((test_name, duration))