"""Tests for the interactive CLI features."""

import pytest
from unittest.mock import Mock, patch
from coda.cli.interactive_cli import InteractiveCLI, DeveloperMode, SlashCommand


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
        assert DeveloperMode.CODE.value == "code"
        assert DeveloperMode.DEBUG.value == "debug"
        assert DeveloperMode.EXPLAIN.value == "explain"
        assert DeveloperMode.REVIEW.value == "review"
        assert DeveloperMode.REFACTOR.value == "refactor"
    
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
            'help', 'model', 'provider', 'mode', 'session',
            'theme', 'export', 'tools', 'clear', 'exit'
        ]
        
        for cmd in expected_commands:
            assert cmd in cli.commands
            assert isinstance(cli.commands[cmd], SlashCommand)
    
    def test_process_slash_command_valid(self, cli):
        """Test processing a valid slash command."""
        result = cli.process_slash_command("/help")
        assert result is True
        cli.console.print.assert_called()
    
    def test_process_slash_command_with_args(self, cli):
        """Test processing slash command with arguments."""
        result = cli.process_slash_command("/mode debug")
        assert result is True
        assert cli.current_mode == DeveloperMode.DEBUG
    
    def test_process_slash_command_alias(self, cli):
        """Test processing slash command using alias."""
        # Clear the console mock first
        cli.console.reset_mock()
        
        result = cli.process_slash_command("/h")  # alias for help
        assert result is True
        cli.console.print.assert_called()
    
    def test_process_slash_command_invalid(self, cli):
        """Test processing an invalid slash command."""
        result = cli.process_slash_command("/invalid")
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
        assert cli.current_mode == DeveloperMode.CODE  # default mode
        
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
        assert any("Available commands" in str(call) for call in calls)
        
        # Check that all commands are mentioned
        for cmd_name in cli.commands:
            assert any(f"/{cmd_name}" in str(call) for call in calls)
    
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
    
    @patch('coda.cli.interactive_cli.Path')
    def test_session_initialization(self, mock_path_class):
        """Test session initialization creates proper directories."""
        # Setup mock path chain
        mock_home = Mock()
        mock_local = Mock()
        mock_share = Mock()
        mock_coda = Mock()
        mock_history_file = Mock()
        
        # Chain the path operations
        mock_path_class.home.return_value = mock_home
        mock_home.__truediv__ = Mock(return_value=mock_local)
        mock_local.__truediv__ = Mock(return_value=mock_share)
        mock_share.__truediv__ = Mock(return_value=mock_coda)
        mock_coda.__truediv__ = Mock(return_value=mock_history_file)
        
        # Set string representation
        mock_history_file.__str__ = Mock(return_value="/mock/history/path")
        
        console = Mock()
        cli = InteractiveCLI(console)
        
        # Check that history directory is created
        mock_coda.mkdir.assert_called_with(parents=True, exist_ok=True)
        
        # Check session is initialized
        assert cli.session is not None