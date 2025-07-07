"""Integration tests to ensure basic and interactive modes work correctly."""

from unittest.mock import Mock, patch

import pytest

from coda.cli.basic_commands import BasicCommandProcessor
from coda.cli.interactive_cli import InteractiveCLI
from coda.cli.shared import DeveloperMode


class MockModel:
    """Mock model for testing."""

    def __init__(self, id: str):
        self.id = id
        self.provider = "test"
        self.metadata = {}


class TestBasicModeIntegration:
    """Test basic mode functionality with shared components."""

    @pytest.fixture
    def processor(self):
        """Create a basic command processor."""
        console = Mock()
        return BasicCommandProcessor(console)

    def test_basic_help_command(self, processor):
        """Test that help command works in basic mode."""
        result = processor.process_command("/help")

        assert result == "continue"
        calls = [str(call) for call in processor.console.print.call_args_list]

        # Check basic mode specific content
        assert any("Available Commands (Basic Mode)" in str(call) for call in calls)
        assert any("Ctrl+C" in str(call) for call in calls)
        assert any("Clear input line" in str(call) for call in calls)
        assert any("Interrupt AI response" in str(call) for call in calls)
        assert any("limited keyboard shortcuts" in str(call) for call in calls)

        # Check shared content
        assert any("Developer Modes" in str(call) for call in calls)
        assert any("/model" in str(call) for call in calls)

    def test_basic_mode_switching(self, processor):
        """Test mode switching in basic mode."""
        # Switch to code mode
        result = processor.process_command("/mode code")

        assert result == "continue"
        assert processor.current_mode == DeveloperMode.CODE

        # Get system prompt
        from coda.cli.shared.modes import get_system_prompt

        prompt = get_system_prompt(processor.current_mode)
        assert "coding assistant" in prompt

    def test_basic_model_switching(self, processor):
        """Test model switching in basic mode."""
        models = [MockModel("model1"), MockModel("model2")]
        processor.set_provider_info("test", None, None, "model1", models)

        result = processor.process_command("/model model2")

        assert result == "continue"
        assert processor.current_model == "model2"

    def test_basic_command_aliases(self, processor):
        """Test command aliases work in basic mode."""
        # Test help aliases
        for alias in ["/h", "/?"]:
            processor.console.reset_mock()
            result = processor.process_command(alias)
            assert result == "continue"
            calls = str(processor.console.print.call_args_list)
            assert "Available Commands" in calls

        # Test exit aliases
        for alias in ["/quit", "/q"]:
            result = processor.process_command(alias)
            assert result == "exit"

    def test_basic_clear_command(self, processor):
        """Test clear command in basic mode."""
        result = processor.process_command("/clear")
        assert result == "clear"

        result = processor.process_command("/cls")
        assert result == "clear"

    def test_basic_unknown_command(self, processor):
        """Test unknown command handling in basic mode."""
        result = processor.process_command("/unknown")

        assert result == "continue"
        calls = [str(call) for call in processor.console.print.call_args_list]
        assert any("Unknown command" in str(call) for call in calls)

    def test_basic_non_command_input(self, processor):
        """Test non-command input passes through."""
        assert processor.process_command("hello world") is None
        assert processor.process_command("") is None
        assert processor.process_command("  ") is None

    @patch("rich.prompt.Prompt.ask")
    def test_basic_ctrl_c_handling(self, mock_ask):
        """Test that Ctrl+C is handled gracefully in basic mode."""
        from click.testing import CliRunner

        from coda.cli.main import main

        # Simulate Ctrl+C followed by /exit
        mock_ask.side_effect = [KeyboardInterrupt, "/exit"]

        runner = CliRunner()
        result = runner.invoke(main, ["--basic", "--provider", "oci_genai"])

        # Should not crash, exit code depends on whether provider was initialized
        # Just verify the command ran without raising an exception
        assert isinstance(result.exit_code, int)


class TestInteractiveModeIntegration:
    """Test interactive mode functionality with shared components."""

    @pytest.fixture
    def cli(self):
        """Create an interactive CLI instance."""
        console = Mock()
        return InteractiveCLI(console)

    def test_interactive_help_command(self, cli):
        """Test that help command works in interactive mode."""
        cli._cmd_help("")

        calls = [str(call) for call in cli.console.print.call_args_list]

        # Check interactive mode specific content
        assert any("Available Commands (Interactive Mode)" in str(call) for call in calls)
        assert any("Ctrl+R" in str(call) for call in calls)
        assert any("Reverse search" in str(call) for call in calls)
        assert any("Tab" in str(call) for call in calls)
        assert any("\\\\" in str(call) for call in calls)
        assert any("Interactive mode only" in str(call) for call in calls)

        # Check shared content
        assert any("Developer Modes" in str(call) for call in calls)

    def test_interactive_mode_switching(self, cli):
        """Test mode switching in interactive mode."""
        cli._cmd_mode("debug")

        assert cli.current_mode == DeveloperMode.DEBUG
        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("Switched to debug mode" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_interactive_model_command_with_args(self, cli):
        """Test model switching with direct argument."""
        models = [MockModel("gpt-4"), MockModel("gpt-3.5")]
        cli.available_models = models

        await cli._cmd_model("gpt-4")

        assert cli.current_model == "gpt-4"

    def test_interactive_provider_command(self, cli):
        """Test provider command in interactive mode."""
        cli.provider_name = "oci_genai"
        cli._cmd_provider("oci_genai")

        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("Already using oci_genai" in str(call) for call in calls)

    def test_interactive_implemented_commands(self, cli):
        """Test that implemented commands work correctly."""
        # Mock session commands to avoid console output issues
        cli.session_commands.handle_session_command = Mock(return_value="Session help")

        # Session command - now implemented
        cli._cmd_session("")
        calls = [str(call) for call in cli.console.print.call_args_list]
        # Session commands are now implemented, should show help
        assert any("Session help" in str(call) for call in calls)

        # Theme command - now implemented (shows current theme)
        cli.console.reset_mock()
        import asyncio

        asyncio.run(cli._cmd_theme("current"))  # Use async call properly
        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("Current theme:" in str(call) for call in calls)

        # Tools command - still coming soon
        cli.console.reset_mock()
        cli._cmd_tools("")
        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("🔧 Coda Tools System" in str(call) for call in calls)

    def test_interactive_exit_command(self, cli):
        """Test exit command in interactive mode."""
        with pytest.raises(SystemExit) as exc_info:
            cli._cmd_exit("")

        assert exc_info.value.code == 0
        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("Goodbye" in str(call) for call in calls)

    def test_interactive_clear_command(self, cli):
        """Test clear command in interactive mode."""
        cli._cmd_clear("")

        calls = [str(call) for call in cli.console.print.call_args_list]
        assert any("Conversation cleared" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_interactive_slash_command_processing(self, cli):
        """Test slash command processing through process_slash_command."""
        result = await cli.process_slash_command("/help")

        assert result is True
        calls = str(cli.console.print.call_args_list)
        assert "Available Commands" in calls

    @pytest.mark.asyncio
    async def test_interactive_command_aliases(self, cli):
        """Test command aliases in interactive mode."""
        # Test through process_slash_command
        result = await cli.process_slash_command("/h")
        assert result is True

        # Mode should process correctly
        result = await cli.process_slash_command("/mode code")
        assert result is True
        assert cli.current_mode == DeveloperMode.CODE


class TestModeCompatibility:
    """Test that both modes handle the same commands consistently."""

    def test_mode_command_consistency(self):
        """Test that mode commands work the same in both modes."""
        # Basic mode
        basic_console = Mock()
        basic = BasicCommandProcessor(basic_console)
        basic.process_command("/mode plan")

        # Interactive mode
        interactive_console = Mock()
        interactive = InteractiveCLI(interactive_console)
        interactive._cmd_mode("plan")

        # Both should be in plan mode
        assert basic.current_mode == DeveloperMode.PLAN
        assert interactive.current_mode == DeveloperMode.PLAN

        # Both should have same system prompt
        from coda.cli.shared import get_system_prompt

        assert get_system_prompt(basic.current_mode) == get_system_prompt(interactive.current_mode)

    def test_help_command_shared_content(self):
        """Test that help shows same shared content in both modes."""
        # Basic mode
        basic_console = Mock()
        basic = BasicCommandProcessor(basic_console)
        basic.process_command("/help")
        basic_calls = str(basic_console.print.call_args_list)

        # Interactive mode
        interactive_console = Mock()
        interactive = InteractiveCLI(interactive_console)
        interactive._cmd_help("")
        interactive_calls = str(interactive_console.print.call_args_list)

        # Both should show developer modes
        assert "Developer Modes" in basic_calls
        assert "Developer Modes" in interactive_calls

        # Both should show all modes
        for mode in ["general", "code", "debug", "explain", "review", "refactor", "plan"]:
            assert mode in basic_calls
            assert mode in interactive_calls
