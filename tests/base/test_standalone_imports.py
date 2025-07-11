"""
Test that base modules can be imported and used standalone.

This verifies that each base module works without requiring other layers.
"""
import subprocess
import sys
from pathlib import Path
import tempfile
import textwrap


def run_isolated_import(module_name: str, test_code: str = "") -> tuple[bool, str]:
    """Run import test in isolated Python process."""
    code = f"""
import sys
# Only allow stdlib and the specific module
sys.path = [p for p in sys.path if 'site-packages' not in p]

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
        cwd=Path(__file__).parent.parent.parent  # Project root
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
    from coda.base.session import SessionManager, SessionContext
    from pathlib import Path
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        
        # Create manager with explicit path
        manager = SessionManager(db_path=db_path)
        
        # Create a session
        session_id = manager.create_session(
            provider="test",
            model="test-model"
        )
        
        assert session_id is not None
        
        # List sessions
        sessions = manager.list_sessions()
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
    
    # Create a test file
    with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as f:
        f.write(b'def test_function():\\n    pass\\n')
        test_file = Path(f.name)
    
    try:
        # Test repo map
        repo_map = RepoMap(root_path=test_file.parent)
        
        # Should be able to get tags (even if empty for simple file)
        tags = repo_map.get_tags()
        assert isinstance(tags, dict)
    finally:
        test_file.unlink()
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
        assert not obs_manager.tracing_enabled
        assert not obs_manager.metrics_enabled
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