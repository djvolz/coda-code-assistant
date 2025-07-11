"""Test command registry functionality."""

from coda.cli.command_registry import CommandRegistry, CommandType


class TestCommandRegistry:
    """Test the centralized command registry."""

    def test_session_subcommands_defined(self):
        """Test that all session subcommands are defined."""
        expected_subcommands = {
            "save",
            "load",
            "last",
            "list",
            "branch",
            "delete",
            "delete-all",
            "rename",
            "info",
            "search",
        }

        actual_subcommands = {cmd.name for cmd in CommandRegistry.SESSION_SUBCOMMANDS}
        assert actual_subcommands == expected_subcommands

    def test_get_command(self):
        """Test getting command by name."""
        session_cmd = CommandRegistry.get_command("session")
        assert session_cmd is not None
        assert session_cmd.name == "session"
        assert "s" in session_cmd.aliases

    def test_get_command_by_alias(self):
        """Test getting command by alias."""
        session_cmd = CommandRegistry.get_command("s")
        assert session_cmd is not None
        assert session_cmd.name == "session"

    def test_get_subcommand(self):
        """Test getting subcommand."""
        session_cmd = CommandRegistry.get_command("session")
        save_cmd = session_cmd.get_subcommand("save")
        assert save_cmd is not None
        assert save_cmd.name == "save"
        assert save_cmd.type == CommandType.SUBCOMMAND

    def test_get_subcommand_by_alias(self):
        """Test getting subcommand by alias."""
        session_cmd = CommandRegistry.get_command("session")
        save_cmd = session_cmd.get_subcommand("s")  # alias for save
        assert save_cmd is not None
        assert save_cmd.name == "save"

    def test_autocomplete_options(self):
        """Test getting autocomplete options."""
        options = CommandRegistry.get_autocomplete_options()

        # Check session options
        assert "session" in options
        session_options = options["session"]

        # Should be list of tuples
        assert isinstance(session_options, list)
        assert all(isinstance(opt, tuple) and len(opt) == 2 for opt in session_options)

        # Check specific commands
        option_names = [opt[0] for opt in session_options]
        assert "last" in option_names
        assert "rename" in option_names
        assert "delete-all" in option_names

    def test_command_help(self):
        """Test command help generation."""
        help_text = CommandRegistry.get_command_help("session")

        # Should contain command name and description
        assert "session" in help_text
        assert "Manage sessions" in help_text

        # Should list subcommands
        assert "save" in help_text
        assert "load" in help_text
        assert "last" in help_text
        assert "rename" in help_text
        assert "delete-all" in help_text

        # Should show aliases
        assert "aliases: s" in help_text

    def test_command_help_all(self):
        """Test getting help for all commands."""
        help_text = CommandRegistry.get_command_help()

        # Should list main commands
        assert "/session" in help_text
        assert "/help" in help_text
        assert "/exit" in help_text
        assert "/model" in help_text

    def test_examples_included(self):
        """Test that examples are included in definitions."""
        session_cmd = CommandRegistry.get_command("session")
        last_cmd = session_cmd.get_subcommand("last")

        assert len(last_cmd.examples) > 0
        assert "/session last" in last_cmd.examples

    def test_new_commands_have_all_fields(self):
        """Test that new commands have all required fields."""
        new_commands = ["last", "rename", "delete-all"]

        session_cmd = CommandRegistry.get_command("session")
        for cmd_name in new_commands:
            cmd = session_cmd.get_subcommand(cmd_name)
            assert cmd is not None
            assert cmd.name == cmd_name
            assert cmd.description
            assert cmd.type == CommandType.SUBCOMMAND
