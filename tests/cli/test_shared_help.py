"""Tests for shared help functionality."""

from unittest.mock import Mock

import pytest

from coda.cli.shared import (
    print_basic_keyboard_shortcuts,
    print_command_help,
    print_developer_modes,
    print_interactive_keyboard_shortcuts,
    print_interactive_only_commands,
)


class TestSharedHelp:
    """Test the shared help display functions."""

    @pytest.fixture
    def mock_console(self):
        """Create a mock console for testing."""
        return Mock()

    def test_print_command_help_no_mode(self, mock_console):
        """Test command help without mode suffix."""
        print_command_help(mock_console)

        # Check that it was called with expected content
        calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Available Commands" in str(call) for call in calls)
        assert any("/model" in str(call) for call in calls)
        assert any("/provider" in str(call) for call in calls)
        assert any("/mode" in str(call) for call in calls)
        assert any("/clear" in str(call) for call in calls)
        assert any("/help" in str(call) for call in calls)
        assert any("/exit" in str(call) for call in calls)

    def test_print_command_help_with_mode(self, mock_console):
        """Test command help with mode suffix."""
        print_command_help(mock_console, "Test Mode")

        calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Available Commands (Test Mode)" in str(call) for call in calls)

    def test_print_developer_modes(self, mock_console):
        """Test developer modes display."""
        print_developer_modes(mock_console)

        calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Developer Modes" in str(call) for call in calls)
        # Check all modes are shown
        for mode in ["general", "code", "debug", "explain", "review", "refactor", "plan"]:
            assert any(mode in str(call) for call in calls)

    def test_print_basic_keyboard_shortcuts(self, mock_console):
        """Test basic keyboard shortcuts display."""
        print_basic_keyboard_shortcuts(mock_console)

        calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Keyboard Shortcuts" in str(call) for call in calls)
        assert any("Ctrl+C" in str(call) for call in calls)
        assert any("Clear input line" in str(call) for call in calls)
        assert any("Interrupt AI response" in str(call) for call in calls)
        assert any("Ctrl+D" in str(call) for call in calls)
        assert any("limited keyboard shortcuts" in str(call) for call in calls)

    def test_print_interactive_keyboard_shortcuts(self, mock_console):
        """Test interactive keyboard shortcuts display."""
        print_interactive_keyboard_shortcuts(mock_console)

        calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Keyboard Shortcuts" in str(call) for call in calls)
        assert any("Ctrl+C" in str(call) for call in calls)
        assert any("Clear input line" in str(call) for call in calls)
        assert any("Ctrl+R" in str(call) for call in calls)
        assert any("Reverse search" in str(call) for call in calls)
        assert any("Tab" in str(call) for call in calls)
        assert any("Auto-complete" in str(call) for call in calls)
        assert any("\\\\" in str(call) for call in calls)  # Escaped backslash

    def test_print_interactive_only_commands(self, mock_console):
        """Test interactive-only commands display."""
        print_interactive_only_commands(mock_console)

        calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Session" in str(call) for call in calls)
        assert any("/session" in str(call) for call in calls)
        assert any("/export" in str(call) for call in calls)
        assert any("Advanced" in str(call) for call in calls)
        assert any("/theme" in str(call) for call in calls)
        assert any("Interactive mode only" in str(call) for call in calls)
        # /tools is NOT in interactive-only commands - it's a global command

    def test_command_aliases_shown(self, mock_console):
        """Test that command aliases are shown in help."""
        print_command_help(mock_console)

        calls = [str(call) for call in mock_console.print.call_args_list]
        # Check for aliases
        assert any("(/m)" in str(call) for call in calls)  # model alias
        assert any("(/p)" in str(call) for call in calls)  # provider alias
        assert any("(/cls)" in str(call) for call in calls)  # clear alias
        assert any("(/h, /?)" in str(call) for call in calls)  # help aliases
        assert any("(/quit, /q)" in str(call) for call in calls)  # exit aliases

    def test_no_duplicate_content(self, mock_console):
        """Test that help content is not duplicated."""
        print_command_help(mock_console)

        # Count occurrences of unique strings in registry format
        calls_str = str(mock_console.print.call_args_list)
        assert calls_str.count("Available Commands:") == 1
        assert calls_str.count("/model") == 1
        assert calls_str.count("/help") == 1
