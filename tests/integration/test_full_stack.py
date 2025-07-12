"""
Integration tests that verify the full stack works together.

These tests ensure that:
- Base modules integrate properly
- Services use base modules correctly
- Apps layer integrates everything
- The full system works end-to-end
"""

import tempfile
from pathlib import Path


def test_config_theme_integration():
    """Test that config and theme modules work together through the service layer."""
    from coda.services.config import get_config_service

    # Get config service
    config = get_config_service()

    # Should have theme manager
    assert config.theme_manager is not None

    # Should be able to get current theme
    theme_name = config.theme_manager.current_theme_name
    valid_themes = [
        "default",
        "dark",
        "light",
        "minimal",
        "vibrant",
        "monokai_dark",
        "monokai_light",
        "dracula_dark",
        "dracula_light",
        "gruvbox_dark",
        "gruvbox_light",
    ]
    assert theme_name in valid_themes

    # Should be able to change theme
    original_theme = theme_name
    new_theme = "dark" if original_theme != "dark" else "light"

    config.theme_manager.set_theme(new_theme)
    assert config.theme_manager.current_theme_name == new_theme

    # Change back
    config.theme_manager.set_theme(original_theme)


def test_session_persistence_full_stack():
    """Test session management through the full stack."""
    from coda.apps.cli.session_commands import SessionCommands
    from coda.base.session import SessionDatabase, SessionManager

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"

        # Create database and manager
        database = SessionDatabase(db_path=db_path)
        manager = SessionManager(database=database)

        # Create session commands (UI layer)
        commands = SessionCommands(session_manager=manager)

        # Add a message through UI layer
        commands.add_message("user", "Hello, AI!", {"test": "metadata"})
        commands.add_message("assistant", "Hello! How can I help?", {"model": "test-model"})

        # Should trigger auto-save
        assert commands.current_session_id is not None

        # Should be able to list sessions
        sessions = manager.get_active_sessions()
        assert len(sessions) == 1

        # Should have correct message count
        assert sessions[0].message_count == 2


def test_provider_with_config_integration():
    """Test that providers can be configured through the config system."""
    from coda.base.providers import ProviderFactory
    from coda.services.config import get_config_service

    config = get_config_service()

    # Create provider factory with config
    factory = ProviderFactory(config.to_dict())

    # Should list available providers
    available = factory.list_available()
    assert "mock" in available  # Mock provider should always be available


def test_search_functionality():
    """Test search/intelligence functionality."""
    from coda.base.search import RepoMap

    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)

        # Create test files
        (test_dir / "main.py").write_text(
            '''
def main():
    """Main entry point."""
    print("Hello, World!")

if __name__ == "__main__":
    main()
'''
        )

        (test_dir / "utils.py").write_text(
            '''
def helper_function():
    """A helper function."""
    return 42
'''
        )

        # Create repo map
        repo_map = RepoMap(test_dir)
        repo_map.scan_repository()

        # Should find both files
        assert len(repo_map.files) == 2

        # Should identify Python files
        py_files = repo_map.get_files_by_language("python")
        assert len(py_files) == 2

        # Should get summary
        summary = repo_map.get_summary()
        assert summary["total_files"] == 2
        assert "python" in summary["languages"]


def test_cli_command_execution_flow():
    """Test command execution flow through the stack."""
    from coda.apps.cli.interactive_cli import InteractiveCLI

    # Create CLI instance
    cli = InteractiveCLI()

    # Test that CLI has initialized properly
    assert cli.session_commands is not None
    assert cli.session_commands.console is not None

    # Execute theme list command
    cli._list_available_themes()  # This should work without errors

    # Test session help command
    result = cli.session_commands._show_session_help()
    assert result is None  # Help is printed, not returned


def test_observability_integration():
    """Test observability can be used with real config."""
    from coda.base.observability import ObservabilityManager
    from coda.services.config import get_config_service

    config = get_config_service()

    # Create observability manager
    obs_manager = ObservabilityManager(config.config)

    # Should be disabled by default
    assert not obs_manager.enabled

    # If enabled, would have components
    if obs_manager.enabled:
        status = obs_manager.get_health_status()
        assert "observability" in status


def test_mvc_separation():
    """Test that MVC separation is maintained."""
    # Model layer (base) should not know about views
    from coda.base.session import SessionManager

    # SessionManager should not have any UI methods
    assert not hasattr(SessionManager, "console")
    assert not hasattr(SessionManager, "_show_session_help")

    # View layer (CLI) should handle presentation
    from coda.apps.cli.session_commands import SessionCommands

    # SessionCommands instances should have UI methods
    commands = SessionCommands()
    assert hasattr(commands, "console")
    assert hasattr(commands, "_show_session_help")


def test_agent_service_integration():
    """Test agent service integration if available."""
    try:
        from coda.services.agents import Agent, AgentCapability, AgentManager
        from coda.services.config import get_config_service

        get_config_service()

        # Create agent manager
        manager = AgentManager()

        # Create and register an agent
        agent = Agent(
            name="test_agent",
            description="Test agent for integration testing",
            capabilities=[AgentCapability.CODE_ANALYSIS],
        )

        manager.register_agent(agent)

        # Should be able to find the agent
        agents = manager.list_agents()
        assert any(a.name == "test_agent" for a in agents)

    except ImportError:
        # Agent service might not be fully implemented
        pass
