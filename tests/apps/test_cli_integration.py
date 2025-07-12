"""
Test CLI integration and apps layer functionality.

The apps layer should:
- Integrate services and base modules
- Provide user-facing functionality
- Handle UI/UX concerns
"""

from pathlib import Path


def test_cli_imports_structure():
    """Test that CLI properly imports from services and base layers."""
    cli_dir = Path("coda/apps/cli")

    # CLI should exist
    assert cli_dir.exists(), "CLI directory should exist"

    # Check main entry points
    expected_files = ["interactive_cli.py", "session_commands.py", "command_registry.py"]

    for filename in expected_files:
        file_path = cli_dir / filename
        assert file_path.exists(), f"Expected CLI file {filename} not found"


def test_session_commands_moved_to_cli():
    """Test that SessionCommands is in CLI layer, not base layer."""
    # Should be able to import from CLI
    from coda.apps.cli.session_commands import SessionCommands

    # Should have expected methods
    assert hasattr(SessionCommands, "handle_session_command")
    assert hasattr(SessionCommands, "handle_export_command")

    # Should NOT be in base layer
    try:
        from coda.base.session.commands import SessionCommands as BaseCommands  # noqa: F401

        raise AssertionError("SessionCommands should not be in base layer")
    except ImportError:
        pass  # This is expected


def test_cli_uses_config_service():
    """Test that CLI uses the config service properly."""
    from coda.apps.cli.session_commands import SessionCommands

    # Create instance
    commands = SessionCommands()

    # Should have console from theme manager
    assert hasattr(commands, "console")
    assert commands.console is not None


def test_interactive_cli_structure():
    """Test InteractiveCLI has proper command structure."""
    from coda.apps.cli.interactive_cli import InteractiveCLI

    cli = InteractiveCLI()

    # Should have command registry
    assert hasattr(cli, "commands")
    assert len(cli.commands) > 0

    # Should have key commands
    expected_commands = ["help", "model", "session", "theme", "clear", "exit"]

    for cmd in expected_commands:
        assert cmd in cli.commands, f"Expected command '{cmd}' not found"


def test_command_registry():
    """Test command registry structure."""
    from coda.apps.cli.command_registry import CommandDefinition, CommandRegistry

    # Should have commands list
    assert hasattr(CommandRegistry, "COMMANDS")
    assert isinstance(CommandRegistry.COMMANDS, list)

    # All commands should be CommandDefinition instances
    for cmd in CommandRegistry.COMMANDS:
        assert isinstance(cmd, CommandDefinition)
        assert hasattr(cmd, "name")
        assert hasattr(cmd, "description")
        assert hasattr(cmd, "aliases")


def test_cli_entry_point():
    """Test that CLI can be invoked through the script entry point."""
    # Test the actual CLI entry point
    # Since we're in the development environment, we'll test the direct import
    try:
        from coda.apps.cli.cli import cli

        # CLI function should exist
        assert cli is not None
        assert callable(cli)

        # Could also test with subprocess if coda is installed:
        # result = subprocess.run(["coda", "--help"], capture_output=True, text=True)
        # but that requires the package to be installed

    except ImportError as e:
        raise AssertionError(f"Failed to import CLI entry point: {e}") from e


def test_cli_theme_integration():
    """Test that CLI properly integrates with theme system."""
    from coda.apps.cli.interactive_cli import InteractiveCLI

    cli = InteractiveCLI()

    # Should have style created from theme
    assert hasattr(cli, "style")
    assert cli.style is not None

    # Should have theme-related commands
    assert "theme" in cli.commands


def test_cli_session_integration():
    """Test that CLI properly integrates with session system."""
    from coda.apps.cli.interactive_cli import InteractiveCLI

    cli = InteractiveCLI()

    # Should have session commands
    assert hasattr(cli, "session_commands")

    # Should have session command in registry
    assert "session" in cli.commands

    # Session command should have subcommands
    session_cmd = cli.commands["session"]
    assert hasattr(session_cmd, "handler")


def test_cli_handles_mvc_separation():
    """Test that CLI follows MVC separation."""
    from coda.apps.cli.session_commands import SessionCommands

    # SessionCommands should handle UI concerns
    commands = SessionCommands()

    # Should format output for display
    result = commands._show_session_help()
    assert result is None  # Help is printed, not returned

    # Should use console for output
    assert hasattr(commands, "console")
