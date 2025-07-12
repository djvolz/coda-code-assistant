"""Tests for InteractiveCLI input handling functionality."""

from unittest.mock import Mock, patch

import pytest

from coda.cli.interactive_cli import InteractiveCLI


class TestInteractiveCLIInput:
    """Test cases for InteractiveCLI input handling."""

    @pytest.fixture
    def cli(self):
        """Create an InteractiveCLI instance for testing."""
        with patch("coda.cli.interactive_cli.ModelManager"):
            cli = InteractiveCLI()
            cli.session_manager = Mock()
            cli.chat_session = Mock()
            return cli

    @pytest.fixture
    def mock_prompt_session(self):
        """Create a mock prompt session."""
        with patch("coda.cli.interactive_cli.PromptSession") as mock:
            session = Mock()
            mock.return_value = session
            yield session

    def test_get_input_single_line(self, cli, mock_prompt_session):
        """Test single-line input handling."""
        mock_prompt_session.prompt.return_value = "Hello, world!"

        result = cli.get_input()

        assert result == "Hello, world!"
        mock_prompt_session.prompt.assert_called_once()

    def test_get_input_empty_string(self, cli, mock_prompt_session):
        """Test empty input returns empty string."""
        mock_prompt_session.prompt.return_value = ""

        result = cli.get_input()

        assert result == ""

    def test_get_input_with_whitespace(self, cli, mock_prompt_session):
        """Test input with leading/trailing whitespace is preserved."""
        mock_prompt_session.prompt.return_value = "  spaced input  "

        result = cli.get_input()

        assert result == "  spaced input  "

    def test_get_input_multiline_mode_triggered(self, cli, mock_prompt_session):
        """Test multiline mode is triggered by triple backticks."""
        mock_prompt_session.prompt.side_effect = ["```", "line 1", "line 2", "```"]

        result = cli.get_input()

        expected = "```\nline 1\nline 2\n```"
        assert result == expected
        assert mock_prompt_session.prompt.call_count == 4

    def test_get_input_multiline_with_language(self, cli, mock_prompt_session):
        """Test multiline mode with language specification."""
        mock_prompt_session.prompt.side_effect = [
            "```python",
            "def hello():",
            "    print('world')",
            "```",
        ]

        result = cli.get_input()

        expected = "```python\ndef hello():\n    print('world')\n```"
        assert result == expected

    def test_get_input_eof_error(self, cli, mock_prompt_session):
        """Test EOFError returns None."""
        mock_prompt_session.prompt.side_effect = EOFError()

        result = cli.get_input()

        assert result is None

    def test_get_input_keyboard_interrupt(self, cli, mock_prompt_session):
        """Test KeyboardInterrupt returns None."""
        mock_prompt_session.prompt.side_effect = KeyboardInterrupt()

        result = cli.get_input()

        assert result is None

    def test_get_input_with_unicode(self, cli, mock_prompt_session):
        """Test input with Unicode characters."""
        mock_prompt_session.prompt.return_value = "Hello 👋 世界 🌍"

        result = cli.get_input()

        assert result == "Hello 👋 世界 🌍"

    def test_get_input_with_special_characters(self, cli, mock_prompt_session):
        """Test input with special characters."""
        mock_prompt_session.prompt.return_value = "!@#$%^&*()_+-=[]{}|;':\",./<>?"

        result = cli.get_input()

        assert result == "!@#$%^&*()_+-=[]{}|;':\",./<>?"

    def test_get_input_multiline_empty_lines(self, cli, mock_prompt_session):
        """Test multiline mode with empty lines."""
        mock_prompt_session.prompt.side_effect = ["```", "line 1", "", "line 3", "```"]

        result = cli.get_input()

        expected = "```\nline 1\n\nline 3\n```"
        assert result == expected

    def test_get_input_multiline_nested_backticks(self, cli, mock_prompt_session):
        """Test multiline mode with nested backticks."""
        mock_prompt_session.prompt.side_effect = [
            "```markdown",
            "Here's some code:",
            "`inline code`",
            "```",
        ]

        result = cli.get_input()

        expected = "```markdown\nHere's some code:\n`inline code`\n```"
        assert result == expected

    def test_get_input_interrupted_flag_set(self, cli, mock_prompt_session):
        """Test input returns None when interrupted flag is set."""
        cli.interrupted = True
        mock_prompt_session.prompt.return_value = "test"

        result = cli.get_input()

        assert result is None
        assert not cli.interrupted  # Flag should be reset

    def test_get_input_with_prompt_customization(self, cli, mock_prompt_session):
        """Test that prompt includes current mode and model info."""
        cli.mode = "code"
        cli.current_model = "gpt-4"
        cli.current_provider = "openai"

        cli.get_input()

        # Verify prompt was called with appropriate styling
        mock_prompt_session.prompt.assert_called_once()
        call_kwargs = mock_prompt_session.prompt.call_args[1]
        assert "bottom_toolbar" in call_kwargs
        assert "style" in call_kwargs

    def test_get_input_multiline_eof_during_input(self, cli, mock_prompt_session):
        """Test EOFError during multiline input."""
        mock_prompt_session.prompt.side_effect = ["```", "line 1", EOFError()]

        result = cli.get_input()

        # Should return collected input so far
        expected = "```\nline 1"
        assert result == expected

    def test_get_input_multiline_keyboard_interrupt(self, cli, mock_prompt_session):
        """Test KeyboardInterrupt during multiline input."""
        mock_prompt_session.prompt.side_effect = ["```", "line 1", KeyboardInterrupt()]

        result = cli.get_input()

        assert result is None

    @patch("coda.cli.interactive_cli.print")
    def test_get_input_exception_handling(self, mock_print, cli, mock_prompt_session):
        """Test general exception handling during input."""
        mock_prompt_session.prompt.side_effect = Exception("Test error")

        result = cli.get_input()

        assert result is None
        mock_print.assert_called_with("Error: Test error")

    def test_get_input_very_long_input(self, cli, mock_prompt_session):
        """Test handling of very long input lines."""
        long_input = "x" * 10000
        mock_prompt_session.prompt.return_value = long_input

        result = cli.get_input()

        assert result == long_input
        assert len(result) == 10000

    def test_get_input_multiline_with_only_backticks(self, cli, mock_prompt_session):
        """Test multiline mode with only closing backticks."""
        mock_prompt_session.prompt.side_effect = ["```", "```"]

        result = cli.get_input()

        expected = "```\n```"
        assert result == expected

    def test_get_input_slash_command_not_multiline(self, cli, mock_prompt_session):
        """Test slash commands are not treated as multiline."""
        mock_prompt_session.prompt.return_value = "/help"

        result = cli.get_input()

        assert result == "/help"
        assert mock_prompt_session.prompt.call_count == 1

    def test_reset_interrupt_clears_flag(self, cli):
        """Test reset_interrupt clears the interrupted flag."""
        cli.interrupted = True

        cli.reset_interrupt()

        assert cli.interrupted is False

    @patch("coda.cli.interactive_cli.signal")
    def test_start_interrupt_listener_registers_handler(self, mock_signal, cli):
        """Test interrupt listener registers signal handlers."""
        cli.start_interrupt_listener()

        mock_signal.signal.assert_called_with(mock_signal.SIGINT, cli._handle_interrupt)

    @patch("coda.cli.interactive_cli.signal")
    def test_stop_interrupt_listener_restores_handler(self, mock_signal, cli):
        """Test stopping interrupt listener restores default handler."""
        cli.original_sigint_handler = mock_signal.default_int_handler

        cli.stop_interrupt_listener()

        mock_signal.signal.assert_called_with(mock_signal.SIGINT, mock_signal.default_int_handler)

    def test_handle_interrupt_sets_flag(self, cli):
        """Test interrupt handler sets the interrupted flag."""
        cli._handle_interrupt(None, None)

        assert cli.interrupted is True

    def test_get_input_with_completer_enabled(self, cli, mock_prompt_session):
        """Test input with tab completion enabled."""
        mock_prompt_session.prompt.return_value = "test input"

        result = cli.get_input()

        assert result == "test input"
        # Verify completer was passed to prompt
        call_kwargs = mock_prompt_session.prompt.call_args[1]
        assert "completer" in call_kwargs

    def test_get_input_multiline_preserves_indentation(self, cli, mock_prompt_session):
        """Test multiline mode preserves indentation."""
        mock_prompt_session.prompt.side_effect = [
            "```python",
            "def function():",
            "    if True:",
            "        return 42",
            "```",
        ]

        result = cli.get_input()

        expected = "```python\ndef function():\n    if True:\n        return 42\n```"
        assert result == expected
