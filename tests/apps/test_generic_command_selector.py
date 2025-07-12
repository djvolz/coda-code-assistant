"""Tests for the generic command selector."""

from unittest.mock import Mock, patch

import pytest

from coda.apps.cli.command_registry import CommandDefinition, CommandRegistry, CommandType
from coda.apps.cli.generic_command_selector import GenericCommandSelector, create_command_selector


class TestGenericCommandSelector:
    """Test the GenericCommandSelector class."""

    def test_export_command_selector(self):
        """Test creating selector for export command."""
        # Find export command
        export_cmd = None
        for cmd in CommandRegistry.COMMANDS:
            if cmd.name == "export":
                export_cmd = cmd
                break

        assert export_cmd is not None

        # Create selector
        selector = GenericCommandSelector(export_cmd)

        assert selector.title == "Select Export Format"
        assert len(selector.options) == 4
        assert not selector.enable_search_override  # Small list, no search

        # Check options
        formats = [opt[0] for opt in selector.options]
        assert "json" in formats
        assert "markdown" in formats
        assert "txt" in formats
        assert "html" in formats

    def test_mode_command_selector(self):
        """Test creating selector for mode command."""
        # Find mode command
        mode_cmd = None
        for cmd in CommandRegistry.COMMANDS:
            if cmd.name == "mode":
                mode_cmd = cmd
                break

        assert mode_cmd is not None

        # Create selector
        selector = GenericCommandSelector(mode_cmd)

        assert selector.title == "Select Developer Mode"
        assert len(selector.options) == 7
        assert not selector.enable_search_override  # Small list, no search

        # Check options
        modes = [opt[0] for opt in selector.options]
        assert "general" in modes
        assert "code" in modes
        assert "debug" in modes

    def test_session_command_selector(self):
        """Test creating selector for session command."""
        # Find session command
        session_cmd = None
        for cmd in CommandRegistry.COMMANDS:
            if cmd.name == "session":
                session_cmd = cmd
                break

        assert session_cmd is not None

        # Create selector
        selector = GenericCommandSelector(session_cmd)

        assert selector.title == "Select Session Command"
        assert len(selector.options) > 5  # Has many subcommands

        # Check options
        commands = [opt[0] for opt in selector.options]
        assert "save" in commands
        assert "load" in commands
        assert "list" in commands
        assert "delete" in commands

    def test_theme_command_selector(self):
        """Test creating selector for theme command (dynamic options)."""
        # Find theme command
        theme_cmd = None
        for cmd in CommandRegistry.COMMANDS:
            if cmd.name == "theme":
                theme_cmd = cmd
                break

        assert theme_cmd is not None

        # Create selector
        selector = GenericCommandSelector(theme_cmd)

        assert selector.title == "Select Theme Option"
        assert len(selector.options) > 0  # Has theme options
        assert selector.enable_search_override  # Many themes, search enabled

    def test_command_with_metadata(self):
        """Test that metadata is included in options."""
        # Create a test command with metadata
        test_cmd = CommandDefinition(
            name="test",
            description="Test command",
            subcommands=[
                CommandDefinition(
                    name="sub1",
                    description="Subcommand 1",
                    examples=["/test sub1 arg"],
                    aliases=["s1", "one"],
                    type=CommandType.SUBCOMMAND,
                )
            ],
        )

        selector = GenericCommandSelector(test_cmd)

        # Check that metadata was extracted
        assert len(selector.options) == 1
        option = selector.options[0]
        assert option[0] == "sub1"
        assert option[1] == "Subcommand 1"
        assert option[2] is not None
        assert "example" in option[2]
        assert option[2]["example"] == "/test sub1 arg"
        assert "aliases" in option[2]
        assert "s1, one" in option[2]["aliases"]


class TestCreateCommandSelector:
    """Test the create_command_selector factory function."""

    def test_create_selector_for_export(self):
        """Test creating selector for export command."""
        selector = create_command_selector("export", CommandRegistry.COMMANDS)

        assert selector is not None
        assert isinstance(selector, GenericCommandSelector)
        assert selector.title == "Select Export Format"

    def test_create_selector_for_mode(self):
        """Test creating selector for mode command."""
        selector = create_command_selector("mode", CommandRegistry.COMMANDS)

        assert selector is not None
        assert isinstance(selector, GenericCommandSelector)
        assert selector.title == "Select Developer Mode"

    def test_create_selector_for_session(self):
        """Test creating selector for session command."""
        selector = create_command_selector("session", CommandRegistry.COMMANDS)

        assert selector is not None
        assert isinstance(selector, GenericCommandSelector)
        assert selector.title == "Select Session Command"

    def test_create_selector_with_alias(self):
        """Test creating selector using command alias."""
        # Session has alias 's'
        selector = create_command_selector("s", CommandRegistry.COMMANDS)

        assert selector is not None
        assert isinstance(selector, GenericCommandSelector)
        assert selector.title == "Select Session Command"

    def test_create_selector_for_help(self):
        """Test that help command returns None (no subcommands)."""
        selector = create_command_selector("help", CommandRegistry.COMMANDS)

        assert selector is None  # Help has no subcommands

    def test_create_selector_for_unknown_command(self):
        """Test that unknown command returns None."""
        selector = create_command_selector("unknown", CommandRegistry.COMMANDS)

        assert selector is None

    @pytest.mark.asyncio
    async def test_selector_integration(self):
        """Test selector can be used with prompt session."""
        selector = create_command_selector("export", CommandRegistry.COMMANDS)
        assert selector is not None

        # Mock the prompt session
        with patch.object(selector, "create_prompt_session") as mock_create:
            mock_session = Mock()

            async def mock_prompt(*args, **kwargs):
                return "json"

            mock_session.prompt_async = mock_prompt
            mock_create.return_value = mock_session

            result = await selector.select_interactive()

            assert result == "json"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
