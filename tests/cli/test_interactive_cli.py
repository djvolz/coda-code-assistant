"""Tests for the interactive CLI features."""

from unittest.mock import AsyncMock, Mock, patch

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
            "search",
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

    @patch("coda.cli.theme_selector.ThemeSelector")
    @patch("coda.themes.get_theme_manager")
    @patch("coda.configuration.save_config")
    @patch("coda.themes.get_themed_console")
    @pytest.mark.asyncio
    async def test_theme_command(
        self, mock_get_console, mock_save_config, mock_theme_manager, mock_theme_selector, cli
    ):
        """Test theme command uses interactive selector when no args."""
        # Mock theme manager
        mock_manager = Mock()
        mock_manager.current_theme_name = "default"
        mock_manager.current_theme.description = "Default Coda theme"
        mock_theme_manager.return_value = mock_manager

        # Mock theme selector
        mock_selector_instance = Mock()
        # Mock async method
        mock_selector_instance.select_theme_interactive = AsyncMock(
            return_value=None
        )  # User cancelled
        mock_theme_selector.return_value = mock_selector_instance

        # Test without args - should use interactive selector
        await cli._cmd_theme("")

        # Check that ThemeSelector was created and used
        mock_theme_selector.assert_called_once()  # Don't check exact console object
        mock_selector_instance.select_theme_interactive.assert_called_once()

        # Check that current theme was shown when no selection made
        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("Current theme:" in str(call) for call in calls)

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
        """Test tools command implementation."""
        # Test without args (should show main help)
        cli._cmd_tools("")

        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("🔧 Coda Tools System" in str(call) for call in calls)

        # Test with args
        cli.console.reset_mock()
        cli._cmd_tools("list")

        calls = [str(call) for call in cli.console.print.call_args_list]
        # Should show tools list, not "not implemented yet" since it's fully implemented
        assert len(calls) > 0  # Should have some output from tools list

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
        # Test that commands have proper autocomplete options
        mode_command = cli.commands.get("mode")
        assert mode_command is not None
        mode_options = mode_command.get_autocomplete_options()
        assert len(mode_options) > 0  # Should have mode options
        assert "general" in mode_options
        assert "code" in mode_options

        session_command = cli.commands.get("session")
        assert session_command is not None
        session_options = session_command.get_autocomplete_options()
        assert len(session_options) > 0  # Should have session subcommands
        assert "save" in session_options
        assert "load" in session_options

    @patch("coda.cli.theme_selector.ThemeSelector")
    @patch("coda.themes.get_theme_manager")
    @patch("coda.configuration.save_config")
    @patch("coda.themes.get_themed_console")
    @pytest.mark.asyncio
    async def test_theme_command_interactive_selection(
        self, mock_get_console, mock_save_config, mock_theme_manager, mock_theme_selector, cli
    ):
        """Test theme command with interactive selection that selects a theme."""
        # Mock theme manager
        mock_manager = Mock()
        mock_manager.current_theme_name = "default"
        mock_theme_manager.return_value = mock_manager

        # Mock the current_theme.prompt.to_prompt_toolkit_style() method
        mock_style = Mock()
        mock_style.style_dict = {}  # Empty dict to avoid TypeError
        mock_manager.current_theme.prompt.to_prompt_toolkit_style.return_value = mock_style

        # Mock theme selector
        mock_selector_instance = Mock()
        mock_selector_instance.select_theme_interactive = AsyncMock(
            return_value="dark"
        )  # User selected dark
        mock_theme_selector.return_value = mock_selector_instance

        # Mock config
        cli.config = Mock()
        cli.config.ui = {"theme": "default"}

        # Mock session
        cli.session = Mock()

        # Test without args - should use interactive selector and set theme
        await cli._cmd_theme("")

        # Check that ThemeSelector was created and used
        mock_theme_selector.assert_called_once()  # Don't check exact console object
        mock_selector_instance.select_theme_interactive.assert_called_once()

        # Check theme was set
        mock_manager.set_theme.assert_called_once_with("dark")

        # Check config was updated and saved
        assert cli.config.ui["theme"] == "dark"
        mock_save_config.assert_called_once()

        # Check success message was printed
        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("Theme changed to" in str(call) for call in calls)
        assert any("dark" in str(call) for call in calls)

    @patch("coda.themes.get_theme_manager")
    @patch("coda.configuration.save_config")
    @patch("coda.themes.get_themed_console")
    @pytest.mark.asyncio
    async def test_theme_command_list(
        self, mock_get_console, mock_save_config, mock_theme_manager, cli
    ):
        """Test theme list subcommand."""
        # Mock theme manager
        mock_manager = Mock()
        mock_manager.current_theme_name = "default"
        mock_theme_manager.return_value = mock_manager

        # Mock THEMES
        with patch(
            "coda.themes.THEMES",
            {
                "default": Mock(description="Default Coda theme"),
                "dark": Mock(description="Dark theme with high contrast"),
            },
        ):
            await cli._cmd_theme("list")

        # Check output shows available themes
        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("Available themes:" in str(call) for call in calls)
        assert any("default" in str(call) for call in calls)
        assert any("dark" in str(call) for call in calls)

    @patch("coda.themes.get_theme_manager")
    @patch("coda.configuration.save_config")
    @patch("coda.themes.get_themed_console")
    @pytest.mark.asyncio
    async def test_theme_command_current(
        self, mock_get_console, mock_save_config, mock_theme_manager, cli
    ):
        """Test theme current subcommand."""
        # Mock theme manager
        mock_manager = Mock()
        mock_manager.current_theme_name = "dark"
        mock_manager.current_theme.description = "Dark theme with high contrast"
        mock_theme_manager.return_value = mock_manager

        await cli._cmd_theme("current")

        # Check output shows current theme
        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("Current theme:" in str(call) for call in calls)
        assert any("dark" in str(call) for call in calls)
        assert any("Dark theme with high contrast" in str(call) for call in calls)

    @patch("coda.themes.get_theme_manager")
    @patch("coda.configuration.save_config")
    @patch("coda.themes.get_themed_console")
    @pytest.mark.asyncio
    async def test_theme_command_set_valid_theme(
        self, mock_get_console, mock_save_config, mock_theme_manager, cli
    ):
        """Test setting a valid theme."""
        # Mock theme manager
        mock_manager = Mock()
        mock_theme_manager.return_value = mock_manager

        # Mock the current_theme.prompt.to_prompt_toolkit_style() method
        mock_style = Mock()
        mock_style.style_dict = {}  # Empty dict to avoid TypeError
        mock_manager.current_theme.prompt.to_prompt_toolkit_style.return_value = mock_style

        # Mock config
        cli.config = Mock()
        cli.config.ui = {"theme": "default"}

        # Mock session
        cli.session = Mock()

        await cli._cmd_theme("dark")

        # Check theme manager was called
        mock_manager.set_theme.assert_called_once_with("dark")

        # Check config was updated and saved
        assert cli.config.ui["theme"] == "dark"
        mock_save_config.assert_called_once()

        # Check success message was printed
        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("Theme changed to" in str(call) for call in calls)
        assert any("dark" in str(call) for call in calls)

    @patch("coda.themes.get_theme_manager")
    @patch("coda.configuration.save_config")
    @patch("coda.themes.get_themed_console")
    @pytest.mark.asyncio
    async def test_theme_command_reset(
        self, mock_get_console, mock_save_config, mock_theme_manager, cli
    ):
        """Test theme reset subcommand."""
        # Mock theme manager
        mock_manager = Mock()
        mock_theme_manager.return_value = mock_manager

        # Mock the current_theme.prompt.to_prompt_toolkit_style() method
        mock_style = Mock()
        mock_style.style_dict = {}  # Empty dict to avoid TypeError
        mock_manager.current_theme.prompt.to_prompt_toolkit_style.return_value = mock_style

        # Mock config
        cli.config = Mock()
        cli.config.ui = {"theme": "dark"}

        # Mock session
        cli.session = Mock()

        with patch("coda.constants.THEME_DEFAULT", "default"):
            await cli._cmd_theme("reset")

        # Check theme manager was called with default theme
        mock_manager.set_theme.assert_called_once_with("default")

        # Check config was updated
        assert cli.config.ui["theme"] == "default"
        mock_save_config.assert_called_once()

    @patch("coda.themes.get_theme_manager")
    @patch("coda.configuration.save_config")
    @patch("coda.themes.get_themed_console")
    @pytest.mark.asyncio
    async def test_theme_command_invalid_theme(
        self, mock_get_console, mock_save_config, mock_theme_manager, cli
    ):
        """Test setting an invalid theme."""
        # Mock theme manager to raise ValueError
        mock_manager = Mock()
        mock_manager.set_theme.side_effect = ValueError("Unknown theme: invalid_theme")
        mock_theme_manager.return_value = mock_manager

        await cli._cmd_theme("invalid_theme")

        # Check error message was printed
        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("Error:" in str(call) for call in calls)
        assert any("Unknown theme" in str(call) for call in calls)

        # Check config was not saved
        mock_save_config.assert_not_called()

    @patch("coda.themes.get_theme_manager")
    @patch("coda.configuration.save_config")
    @patch("coda.themes.get_themed_console")
    @pytest.mark.asyncio
    async def test_theme_command_no_config(
        self, mock_get_console, mock_save_config, mock_theme_manager, cli
    ):
        """Test theme command when config is not available."""
        # Mock theme manager
        mock_manager = Mock()
        mock_theme_manager.return_value = mock_manager

        # Mock the current_theme.prompt.to_prompt_toolkit_style() method
        mock_style = Mock()
        mock_style.style_dict = {}  # Empty dict to avoid TypeError
        mock_manager.current_theme.prompt.to_prompt_toolkit_style.return_value = mock_style

        # Set config to None
        cli.config = None

        await cli._cmd_theme("dark")

        # Check theme manager was still called
        mock_manager.set_theme.assert_called_once_with("dark")

        # Check config was not saved
        mock_save_config.assert_not_called()

        # Check success message was printed but no save message
        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("Theme changed to" in str(call) for call in calls)
        assert not any("preference saved" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_search_command(self, cli):
        """Test search command basic functionality."""
        # Test without args (should show help)
        await cli._cmd_search("")

        # The table object is printed, so we need to check call count and content
        assert cli.console.print.call_count >= 2  # Empty line + table + tip

        # Check that a table was printed (second call)
        assert any("Table object" in str(call) for call in cli.console.print.call_args_list)

        # Check tip was printed
        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("search index demo" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_search_command_with_subcommand(self, cli):
        """Test search command with subcommand handling."""
        # Mock the semantic search manager
        mock_manager = Mock()
        mock_manager.search = AsyncMock(return_value=[])
        mock_manager.embedding_provider = Mock()
        mock_manager.embedding_provider.get_model_info = Mock(
            return_value={"model": "mock", "dimension": 384}
        )

        # Mock console.status to support context manager
        mock_status = Mock()
        mock_status.__enter__ = Mock(return_value=mock_status)
        mock_status.__exit__ = Mock(return_value=None)
        cli.console.status = Mock(return_value=mock_status)

        # Set the mock manager directly
        cli._search_manager = mock_manager

        # Test semantic search without query (should show error)
        await cli._cmd_search("semantic")

        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("Please provide a search query" in str(call) for call in calls)

        # Clear previous calls
        cli.console.print.reset_mock()

        # Test with query
        await cli._cmd_search("semantic test query")

        # Should have called search
        mock_manager.search.assert_called_with("test query", k=5)
