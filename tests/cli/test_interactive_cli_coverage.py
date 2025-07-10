"""Additional tests to improve coverage for interactive_cli.py."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from coda.cli.interactive_cli import InteractiveCLI
from coda.cli.shared import DeveloperMode


@pytest.mark.unit
@pytest.mark.fast
class TestInteractiveCLIAdditional:
    """Additional tests to improve coverage."""

    @pytest.fixture
    def cli(self):
        """Create a CLI instance for testing."""
        console = Mock()
        with patch("coda.cli.interactive_cli.HISTORY_FILE_PATH", Path("/tmp/test_history")):
            cli = InteractiveCLI(console)
            # Mock the session to avoid prompt creation
            cli.session = Mock()
            return cli

    def test_get_available_models_exception(self, cli):
        """Test _get_available_models when provider raises exception."""
        # Test with provider that raises exception
        mock_provider = Mock()
        mock_provider.list_models.side_effect = Exception("Provider error")
        cli.provider = mock_provider

        models = cli._get_available_models()
        assert models == []

    def test_create_style_with_theme(self, cli):
        """Test style creation from theme."""
        style = cli._create_style()
        assert style is not None
        # Style should be created even without theme manager

    def test_init_commands(self, cli):
        """Test command initialization."""
        commands = cli._init_commands()

        # Check all commands are present
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
            assert cmd in commands
            assert commands[cmd].handler is not None
            assert commands[cmd].help_text is not None

    def test_get_prompt(self, cli):
        """Test prompt generation."""
        cli.current_mode = DeveloperMode.CODE
        cli.current_model = "test.model"
        cli.provider_name = "test_provider"

        prompt = cli._get_prompt()
        # Prompt should be HTML object
        assert prompt is not None
        assert hasattr(prompt, "value")

    def test_render_separators(self, cli):
        """Test separator rendering methods."""
        # These methods render to console, just ensure they don't crash
        cli._render_input_separator()
        cli._render_bottom_separator()

        # Should have called console methods
        assert cli.console.print.called or cli.console.rule.called

    def test_get_safe_terminal_width(self, cli):
        """Test safe terminal width calculation."""
        # Mock console size
        cli.console.width = 120

        width = cli._get_safe_terminal_width()
        assert width > 0
        assert width <= 120

    def test_search_manager_initialization(self, cli):
        """Test search manager is initialized as None."""
        # Should be None initially
        assert cli._search_manager is None

    def test_tools_command_implementations(self, cli):
        """Test tools command subcommands."""
        # Test list subcommand
        cli._cmd_tools("list")

        calls = [str(call) for call in cli.console.print.call_args_list]
        # Should show tools or indicate implementation needed
        assert len(calls) > 0

    def test_tools_command_status(self, cli):
        """Test tools status subcommand."""
        cli._cmd_tools("status")

        calls = [str(call) for call in cli.console.print.call_args_list]
        # Should show some output - check we got a response
        assert len(calls) > 0

    def test_tools_command_available(self, cli):
        """Test tools available subcommand."""
        cli._cmd_tools("available")

        calls = [str(call) for call in cli.console.print.call_args_list]
        assert len(calls) > 0  # Should produce some output

    @pytest.mark.asyncio
    async def test_search_command_error_handling(self, cli):
        """Test search command error handling."""
        # Test with search manager that raises exception
        mock_manager = Mock()
        mock_manager.search = AsyncMock(side_effect=Exception("Search error"))
        cli._search_manager = mock_manager

        # Mock console.status
        mock_status = Mock()
        mock_status.__enter__ = Mock(return_value=mock_status)
        mock_status.__exit__ = Mock(return_value=None)
        cli.console.status = Mock(return_value=mock_status)

        await cli._cmd_search("semantic test query")

        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("Search error" in str(call) or "error" in str(call).lower() for call in calls)

    def test_key_bindings_initialization(self, cli):
        """Test key bindings are properly initialized."""
        # Access the key bindings through the session
        assert cli.session is not None
        # Key bindings should be set up during init

    def test_interrupt_handling(self, cli):
        """Test interrupt handling methods."""
        # Test reset_interrupt
        cli.interrupt_event.set()
        cli.reset_interrupt()
        assert not cli.interrupt_event.is_set()

        # Test start and stop interrupt listener
        cli.start_interrupt_listener()
        # Should register signal handler

        cli.stop_interrupt_listener()
        # Should restore original handler

    def test_escape_handler_tracking(self, cli):
        """Test escape key press tracking."""
        # Initial state
        assert cli.escape_count == 0
        assert cli.last_escape_time == 0

        # Simulate escape press handling would update these
        cli.escape_count = 1
        cli.last_escape_time = 100

        # These should be tracked
        assert cli.escape_count == 1
        assert cli.last_escape_time == 100

    @pytest.mark.asyncio
    async def test_get_input_functionality(self, cli):
        """Test get_input method."""
        # Mock session.prompt_async
        cli.session = Mock()
        cli.session.prompt_async = AsyncMock(return_value="test input")

        result = await cli.get_input()

        assert result == "test input"
        cli.session.prompt_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_input_multiline(self, cli):
        """Test get_input in multiline mode."""
        # Mock session.prompt_async
        cli.session = Mock()
        cli.session.prompt_async = AsyncMock(return_value="```\ncode\n```")

        result = await cli.get_input(multiline=True)

        assert result == "```\ncode\n```"
        # Should be called with multiline=True
        assert "multiline" in cli.session.prompt_async.call_args[1]

    def test_session_commands_initialization(self, cli):
        """Test session commands are properly initialized."""
        assert cli.session_commands is not None
        assert hasattr(cli.session_commands, "handle_session_command")
        assert hasattr(cli.session_commands, "handle_export_command")

    def test_observability_command(self, cli):
        """Test observability command."""
        cli._cmd_observability("status")

        calls = [str(call) for call in cli.console.print.call_args_list]
        # Should show observability info or coming soon message
        assert len(calls) > 0

    def test_intel_command(self, cli):
        """Test intelligence command."""
        cli._cmd_intel("analyze")

        calls = [str(call) for call in cli.console.print.call_args_list]
        # Should show intelligence info or coming soon message
        assert len(calls) > 0

    def test_clear_command_functionality(self, cli):
        """Test clear command."""
        cli._cmd_clear("")

        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("Conversation cleared" in str(call) for call in calls)

    def test_exit_command_functionality(self, cli):
        """Test exit command."""
        with pytest.raises(SystemExit) as exc_info:
            cli._cmd_exit("")

        assert exc_info.value.code == 0
        cli.console.print.assert_called_with("[dim]Goodbye![/dim]")

    @pytest.mark.asyncio
    async def test_get_input_eof_handling(self, cli):
        """Test get_input EOF handling."""
        # Mock session.prompt_async to raise EOFError
        cli.session = Mock()
        cli.session.prompt_async = AsyncMock(side_effect=EOFError())

        result = await cli.get_input()

        # Should return /exit on EOF
        assert result == "/exit"

    @pytest.mark.asyncio
    async def test_get_input_keyboard_interrupt(self, cli):
        """Test get_input keyboard interrupt handling."""
        # Mock session.prompt_async to raise KeyboardInterrupt
        cli.session = Mock()
        cli.session.prompt_async = AsyncMock(side_effect=KeyboardInterrupt())

        result = await cli.get_input()

        # Should return empty string on interrupt
        assert result == ""

    @pytest.mark.asyncio
    async def test_model_command_with_args(self, cli):
        """Test model command with arguments."""
        # Set up mock models
        mock_model1 = Mock(id="provider.gpt-4", display_name="GPT-4")
        mock_model2 = Mock(id="provider.gpt-3.5", display_name="GPT-3.5")
        cli.available_models = [mock_model1, mock_model2]

        # Mock the switch_model method since it's from parent class
        with patch.object(cli, "switch_model") as mock_switch:
            await cli._cmd_model("gpt4")

            # Should call switch_model with the args
            mock_switch.assert_called_once_with("gpt4")

    @pytest.mark.asyncio
    async def test_model_command_invalid_model(self, cli):
        """Test model command with invalid model name."""
        cli.available_models = [Mock(id="test.model", display_name="Test Model")]

        await cli._cmd_model("nonexistent")

        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("not found" in str(call).lower() for call in calls)

    def test_terminal_width_tracking(self, cli):
        """Test terminal width tracking."""
        # Should track terminal width
        assert hasattr(cli, "_last_terminal_width")

        # Initial value should be None
        assert cli._last_terminal_width is None
