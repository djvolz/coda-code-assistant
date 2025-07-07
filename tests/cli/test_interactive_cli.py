"""Tests for the interactive CLI features."""

from unittest.mock import Mock, patch

import pytest

from coda.cli.interactive_cli import InteractiveCLI, SlashCommand
from coda.cli.shared import DeveloperMode


@pytest.mark.unit
class TestInteractiveCLI:
    """Test the interactive CLI functionality."""

    @pytest.fixture
    def cli(self):
        """Create a CLI instance for testing."""
        console = Mock()
        return InteractiveCLI(console)

    def test_developer_modes(self, cli):
        """Test developer mode enumeration."""
        assert DeveloperMode.GENERAL.value == "general"
        assert DeveloperMode.CODE.value == "code"
        assert DeveloperMode.DEBUG.value == "debug"
        assert DeveloperMode.EXPLAIN.value == "explain"
        assert DeveloperMode.REVIEW.value == "review"
        assert DeveloperMode.REFACTOR.value == "refactor"
        assert DeveloperMode.PLAN.value == "plan"

    def test_slash_command_init(self):
        """Test SlashCommand initialization."""
        handler = Mock()
        cmd = SlashCommand("test", handler, "Test command", ["t"])

        assert cmd.name == "test"
        assert cmd.handler == handler
        assert cmd.help_text == "Test command"
        assert cmd.aliases == ["t"]

    def test_commands_initialization(self, cli):
        """Test that all expected commands are initialized."""
        expected_commands = [
            "help",
            "model",
            "provider",
            "mode",
            "session",
            "theme",
            "export",
            "tools",
            "clear",
            "exit",
        ]

        for cmd in expected_commands:
            assert cmd in cli.commands
            assert isinstance(cli.commands[cmd], SlashCommand)

    @pytest.mark.asyncio
    async def test_process_slash_command_valid(self, cli):
        """Test processing a valid slash command."""
        result = await cli.process_slash_command("/help")
        assert result is True
        cli.console.print.assert_called()

    @pytest.mark.asyncio
    async def test_process_slash_command_with_args(self, cli):
        """Test processing slash command with arguments."""
        result = await cli.process_slash_command("/mode debug")
        assert result is True
        assert cli.current_mode == DeveloperMode.DEBUG

    @pytest.mark.asyncio
    async def test_process_slash_command_alias(self, cli):
        """Test processing slash command using alias."""
        # Clear the console mock first
        cli.console.reset_mock()

        result = await cli.process_slash_command("/h")  # alias for help
        assert result is True
        cli.console.print.assert_called()

    @pytest.mark.asyncio
    async def test_process_slash_command_invalid(self, cli):
        """Test processing an invalid slash command."""
        result = await cli.process_slash_command("/invalid")
        assert result is True

        # Check error message was printed
        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("Unknown command" in str(call) for call in calls)

    def test_mode_switching(self, cli):
        """Test switching between developer modes."""
        # Test each mode
        for mode in DeveloperMode:
            cli._cmd_mode(mode.value)
            assert cli.current_mode == mode
            cli.console.print.assert_called()

    def test_mode_invalid(self, cli):
        """Test switching to invalid mode."""
        cli._cmd_mode("invalid_mode")
        # Mode should not change
        assert cli.current_mode == DeveloperMode.GENERAL  # default mode

        # Check error message
        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("Invalid mode" in str(call) for call in calls)

    def test_mode_no_args(self, cli):
        """Test mode command without arguments."""
        cli._cmd_mode("")

        # Should print current mode and available modes
        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("Current mode" in str(call) for call in calls)
        assert any("Available modes" in str(call) for call in calls)

    def test_help_command(self, cli):
        """Test help command output."""
        cli._cmd_help("")

        # Should print all commands
        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("Available Commands" in str(call) for call in calls)

        # Check that all commands are mentioned (registry format)
        for cmd_name in cli.commands:
            assert any(f"/{cmd_name}" in str(call) for call in calls)

        # Check specific commands are present
        assert any("/help" in str(call) for call in calls)
        assert any("/session" in str(call) for call in calls)
        assert any("/export" in str(call) for call in calls)

    def test_exit_command(self, cli):
        """Test exit command."""
        with pytest.raises(SystemExit) as exc_info:
            cli._cmd_exit("")

        assert exc_info.value.code == 0
        cli.console.print.assert_called_with("[dim]Goodbye![/dim]")

    def test_clear_command(self, cli):
        """Test clear command."""
        cli._cmd_clear("")

        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("Conversation cleared" in str(call) for call in calls)

    @patch("coda.cli.interactive_cli.HISTORY_FILE_PATH")
    def test_session_initialization(self, mock_history_path):
        """Test session initialization creates proper directories."""
        # Setup mock history file path
        mock_parent = Mock()
        mock_history_path.parent = mock_parent
        mock_history_path.__str__ = Mock(return_value="/mock/history/path")

        console = Mock()
        cli = InteractiveCLI(console)

        # Check that history directory is created
        mock_parent.mkdir.assert_called_with(parents=True, exist_ok=True)

        # Check session is initialized
        assert cli.session is not None

    @pytest.mark.asyncio
    async def test_model_command_no_models(self, cli):
        """Test model command when no models are available."""
        cli.available_models = []
        await cli._cmd_model("")

        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("No models available" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_model_command_with_models(self, cli):
        """Test model command with available models."""
        from unittest.mock import AsyncMock, Mock, patch

        # Setup mock models
        mock_model1 = Mock(id="model1", display_name="Model 1")
        mock_model2 = Mock(id="model2", display_name="Model 2")
        cli.available_models = [mock_model1, mock_model2]
        cli.current_model = "model1"

        with patch("coda.cli.model_selector.ModelSelector") as mock_selector_class:
            mock_selector = Mock()
            mock_selector.select_model_interactive = AsyncMock(return_value=None)
            mock_selector_class.return_value = mock_selector

            await cli._cmd_model("")

            # Should create model selector
            mock_selector_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_model_command_with_direct_switch(self, cli):
        """Test model command with direct model name."""
        mock_model = Mock(id="test.model", display_name="Test Model")
        cli.available_models = [mock_model]

        await cli._cmd_model("test")

        assert cli.current_model == "test.model"
        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("Switched to model" in str(call) for call in calls)

    def test_provider_command_no_args(self, cli):
        """Test provider command without arguments."""
        cli._cmd_provider("")

        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("Provider Management" in str(call) for call in calls)
        assert any("oci_genai" in str(call) for call in calls)
        assert any("ollama" in str(call) for call in calls)

    def test_provider_command_with_args(self, cli):
        """Test provider command with provider name."""
        # Set up the provider name
        cli.provider_name = "oci_genai"
        cli._cmd_provider("oci_genai")

        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("Already using oci_genai" in str(call) for call in calls)

        # Test unimplemented provider
        cli.console.reset_mock()
        cli._cmd_provider("ollama")

        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("not supported in current mode" in str(call) for call in calls)

    def test_session_command(self, cli):
        """Test session command."""
        # Mock the session commands to avoid console output issues
        cli.session_commands.handle_session_command = Mock(return_value="Session help shown")

        # Test without args - should call session command handler
        cli._cmd_session("")

        # Verify the session command handler was called with empty args
        cli.session_commands.handle_session_command.assert_called_with([])

        # Should print the result
        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("Session help shown" in str(call) for call in calls)

        # Test with args - should pass to session command handler
        cli.console.reset_mock()
        cli.session_commands.handle_session_command.reset_mock()
        cli._cmd_session("save test")

        # Verify the session command handler was called with the right args
        cli.session_commands.handle_session_command.assert_called_with(["save", "test"])

    def test_theme_command(self, cli):
        """Test theme command (coming soon)."""
        # Test without args
        cli._cmd_theme("")

        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("Theme Settings" in str(call) for call in calls)
        assert any("Coming soon" in str(call) for call in calls)

        # Test with args
        cli.console.reset_mock()
        cli._cmd_theme("dark")

        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("not implemented yet" in str(call) for call in calls)

    def test_export_command(self, cli):
        """Test export command."""
        # Mock the export commands to avoid console output issues
        cli.session_commands.handle_export_command = Mock(return_value="Export help shown")

        # Test without args - should call export command handler
        cli._cmd_export("")

        # Verify the export command handler was called with empty args
        cli.session_commands.handle_export_command.assert_called_with([])

        # Should print the result
        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("Export help shown" in str(call) for call in calls)

        # Test with args - should pass to export command handler
        cli.console.reset_mock()
        cli.session_commands.handle_export_command.reset_mock()
        cli._cmd_export("markdown")

        # Verify the export command handler was called with the right args
        cli.session_commands.handle_export_command.assert_called_with(["markdown"])

    def test_tools_command(self, cli):
        """Test tools command (coming soon)."""
        # Test without args
        cli._cmd_tools("")

        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("MCP Tools Management" in str(call) for call in calls)
        assert any("Coming soon" in str(call) for call in calls)

        # Test with args
        cli.console.reset_mock()
        cli._cmd_tools("list")

        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("not implemented yet" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_slash_command_aliases(self, cli):
        """Test all command aliases work correctly."""
        # Test /h alias for /help
        cli.console.reset_mock()
        cli._cmd_help("")
        help_calls = len(cli.console.print.call_args_list)

        # Test /? alias
        cli.console.reset_mock()
        result = await cli.process_slash_command("/?")
        assert result is True
        assert len(cli.console.print.call_args_list) == help_calls

        # Test /m alias for /model
        cli.available_models = []
        cli.console.reset_mock()
        result = await cli.process_slash_command("/m")
        assert result is True
        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("No models available" in str(call) for call in calls)

        # Test /q alias for /exit
        with pytest.raises(SystemExit):
            await cli.process_slash_command("/q")

    def test_command_options_loading(self, cli):
        """Test that command options are properly loaded."""
        # The command options are loaded in the SlashCommandCompleter
        completer = cli.session.completer.slash_completer
        options = completer.command_options

        # Should have options for various commands
        assert "mode" in options
        assert "provider" in options
        assert "session" in options

        # Check mode options
        mode_options = options["mode"]
        mode_names = [opt[0] for opt in mode_options]
        assert "general" in mode_names
        assert "code" in mode_names
        assert "debug" in mode_names
