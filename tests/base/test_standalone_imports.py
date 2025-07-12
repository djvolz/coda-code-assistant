"""
Test that base modules can be imported and used standalone.

This verifies that each base module works without requiring other layers.
"""

import subprocess
import sys
from pathlib import Path


def run_isolated_import(module_name: str, test_code: str = "") -> tuple[bool, str]:
    """Run import test in isolated Python process."""
    code = f"""
try:
    import {module_name}
{test_code}
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {{e}}")
    import traceback
    traceback.print_exc()
"""

    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent,  # Project root
    )

    success = "SUCCESS" in result.stdout
    output = result.stdout + result.stderr

    return success, output


def test_config_standalone_import():
    """Test that config module can be imported standalone."""
    test_code = """
    # Test basic functionality
    from coda.base.config import Config
    from pathlib import Path
    import tempfile

    with tempfile.NamedTemporaryFile(suffix='.toml', delete=False) as f:
        config_path = Path(f.name)

    config = Config(config_file=config_path)
    config.set('test_key', 'test_value')
    assert config.get('test_key') == 'test_value'

    # Cleanup
    config_path.unlink()
"""

    success, output = run_isolated_import("coda.base.config", test_code)
    assert success, f"Config standalone import failed:\n{output}"


def test_theme_standalone_import():
    """Test that theme module can be imported standalone."""
    test_code = """
    # Test basic functionality
    from coda.base.theme import ThemeManager, THEMES

    manager = ThemeManager()
    assert manager.current_theme_name in THEMES

    # Test getting themes
    console_theme = manager.get_console_theme()
    assert console_theme.info  # Has color values

    # Test listing themes
    themes = manager.list_themes()
    assert len(themes) > 0
"""

    success, output = run_isolated_import("coda.base.theme", test_code)
    assert success, f"Theme standalone import failed:\n{output}"


def test_providers_standalone_import():
    """Test that providers module can be imported standalone."""
    test_code = """
    # Test basic functionality
    from coda.base.providers import Message, Role, ProviderFactory

    # Create a message
    msg = Message(role=Role.USER, content="test")
    assert msg.content == "test"

    # Test factory with minimal config
    factory = ProviderFactory({})
    available = factory.list_available()
    assert 'mock' in available  # Mock provider should always be available
"""

    success, output = run_isolated_import("coda.base.providers", test_code)
    assert success, f"Providers standalone import failed:\n{output}"


def test_session_standalone_import():
    """Test that session module can be imported standalone."""
    test_code = """
    # Test basic functionality
    from coda.base.session import SessionManager, SessionDatabase
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"

        # Create database and manager
        database = SessionDatabase(db_path=db_path)
        manager = SessionManager(database=database)

        # Create a session
        session = manager.create_session(
            name="test session",
            provider="test",
            model="test-model"
        )

        assert session is not None
        assert session.id is not None

        # List sessions - returns Session objects, not just IDs
        sessions = manager.get_active_sessions()
        assert len(sessions) > 0
"""

    success, output = run_isolated_import("coda.base.session", test_code)
    assert success, f"Session standalone import failed:\n{output}"


def test_search_standalone_import():
    """Test that search module can be imported standalone."""
    test_code = """
    # Test basic functionality
    from coda.base.search import RepoMap
    from pathlib import Path
    import tempfile

    # Create a test directory with a file
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        test_file = test_dir / "test.py"
        test_file.write_text('def test_function():\\n    pass\\n')

        # Test repo map
        repo_map = RepoMap(root_path=test_dir)

        # Should be able to scan repository
        repo_map.scan_repository()

        # Should have found our test file
        assert len(repo_map.files) > 0

        # Should be able to get summary
        summary = repo_map.get_summary()
        assert isinstance(summary, dict)
        assert summary['total_files'] > 0
"""

    success, output = run_isolated_import("coda.base.search", test_code)
    assert success, f"Search standalone import failed:\n{output}"


def test_observability_standalone_import():
    """Test that observability module can be imported standalone."""
    test_code = """
    # Test basic functionality
    from coda.base.observability import ObservabilityManager
    from coda.base.config import Config
    from pathlib import Path
    import tempfile

    with tempfile.NamedTemporaryFile(suffix='.toml', delete=False) as f:
        config_path = Path(f.name)

    try:
        # Create config
        config = Config(config_file=config_path)

        # Create observability manager
        obs_manager = ObservabilityManager(config)

        # Should be disabled by default
        assert not obs_manager.enabled
        assert obs_manager.metrics_collector is None  # Not initialized when disabled
        assert obs_manager.tracing_manager is None  # Not initialized when disabled
    finally:
        config_path.unlink()
"""

    success, output = run_isolated_import("coda.base.observability", test_code)
    assert success, f"Observability standalone import failed:\n{output}"


def test_cross_base_module_imports():
    """Test that base modules can import from each other correctly."""
    # This is allowed - base modules can depend on other base modules
    test_code = """
    # Session uses providers
    from coda.base.session import SessionManager
    from coda.base.providers import Message, Role

    # Config is used by many
    from coda.base.config import Config
    from coda.base.theme import ThemeManager
    from coda.base.observability import ObservabilityManager

    # All imports should work
    print("All cross-base imports successful")
"""

    success, output = run_isolated_import("coda.base", test_code)
    assert success, f"Cross-base module imports failed:\n{output}"


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
