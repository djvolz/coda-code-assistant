"""Regression tests for help functionality to prevent issues from reoccurring."""

from unittest.mock import Mock

from coda.cli.basic_commands import BasicCommandProcessor
from coda.cli.interactive_cli import InteractiveCLI
from coda.cli.shared import print_interactive_keyboard_shortcuts


class TestHelpRegressions:
    """Test specific regression cases for help functionality."""

    def test_backslash_display_in_help(self):
        """Regression test: Ensure backslash displays correctly, not as [/cyan]."""
        console = Mock()
        print_interactive_keyboard_shortcuts(console)

        # Check that the backslash line was called correctly
        calls = [str(call) for call in console.print.call_args_list]
        backslash_calls = [call for call in calls if "line end" in str(call)]

        assert len(backslash_calls) > 0
        backslash_call = str(backslash_calls[0])

        # Should contain escaped backslash
        assert "\\\\" in backslash_call
        # The actual output contains the escaped backslash followed by [/cyan]
        # This is correct - it's showing \\[/cyan] which will render as \ in the terminal
        # We just need to ensure it's not showing a literal [/cyan] without the backslash
        assert "\\\\[/cyan] at line end" in backslash_call

    def test_ctrl_c_behavior_documented_correctly(self):
        """Regression test: Ensure Ctrl+C behavior is documented similarly for both modes."""
        # Basic mode
        basic_console = Mock()
        basic = BasicCommandProcessor(basic_console)
        basic.process_command("/help")
        basic_calls = str(basic_console.print.call_args_list)

        # Should say it clears input/interrupts like interactive mode now
        assert "Clear input line" in basic_calls
        assert "Interrupt AI response" in basic_calls

        # Interactive mode
        interactive_console = Mock()
        interactive = InteractiveCLI(interactive_console)
        interactive._cmd_help("")
        interactive_calls = str(interactive_console.print.call_args_list)

        # Should say it clears input/interrupts
        assert "Clear input line" in interactive_calls
        assert "Interrupt AI response" in interactive_calls

    def test_no_history_navigation_in_basic_help(self):
        """Regression test: Basic mode should not claim to have history navigation."""
        console = Mock()
        processor = BasicCommandProcessor(console)
        processor.process_command("/help")

        calls = str(console.print.call_args_list)

        # Should NOT mention arrow keys for history
        assert "Navigate command history" not in calls
        # Should mention limited shortcuts
        assert "limited keyboard shortcuts" in calls

    def test_reverse_search_only_in_interactive(self):
        """Regression test: Only interactive mode should mention Ctrl+R."""
        # Basic mode - should NOT have Ctrl+R
        basic_console = Mock()
        basic = BasicCommandProcessor(basic_console)
        basic.process_command("/help")
        basic_calls = str(basic_console.print.call_args_list)

        assert "Ctrl+R" not in basic_calls
        assert "Reverse search" not in basic_calls

        # Interactive mode - should have Ctrl+R
        interactive_console = Mock()
        interactive = InteractiveCLI(interactive_console)
        interactive._cmd_help("")
        interactive_calls = str(interactive_console.print.call_args_list)

        assert "Ctrl+R" in interactive_calls
        assert "Reverse search" in interactive_calls

    def test_tab_completion_only_in_interactive(self):
        """Regression test: Only interactive mode should mention Tab completion."""
        # Basic mode
        basic_console = Mock()
        basic = BasicCommandProcessor(basic_console)
        basic.process_command("/help")
        basic_calls = str(basic_console.print.call_args_list)

        assert "Tab" not in basic_calls or "Auto-complete" not in basic_calls

        # Interactive mode
        interactive_console = Mock()
        interactive = InteractiveCLI(interactive_console)
        interactive._cmd_help("")
        interactive_calls = str(interactive_console.print.call_args_list)

        assert "Tab" in interactive_calls
        assert "Auto-complete" in interactive_calls

    def test_interactive_only_commands_marked(self):
        """Regression test: Interactive-only commands should be clearly marked."""
        console = Mock()
        cli = InteractiveCLI(console)
        cli._cmd_help("")

        calls = str(console.print.call_args_list)

        # Should mark session/export/tools/theme as interactive only
        assert "Interactive mode only" in calls
        assert "/session" in calls
        assert "/export" in calls
        assert "/tools" in calls
        assert "/theme" in calls

    def test_mode_descriptions_consistent(self):
        """Regression test: Mode descriptions should be identical in both modes."""
        # Get descriptions from basic mode
        basic_console = Mock()
        basic = BasicCommandProcessor(basic_console)
        basic.process_command("/help")
        basic_calls = str(basic_console.print.call_args_list)

        # Get descriptions from interactive mode
        interactive_console = Mock()
        interactive = InteractiveCLI(interactive_console)
        interactive._cmd_help("")
        interactive_calls = str(interactive_console.print.call_args_list)

        # Check that mode descriptions are the same
        mode_descriptions = [
            "General conversation and assistance",
            "Optimized for writing new code with best practices",
            "Focus on error analysis and debugging assistance",
            "Detailed code explanations and documentation",
            "Security and code quality review",
            "Code improvement and optimization suggestions",
            "Architecture planning and system design",
        ]

        for desc in mode_descriptions:
            assert desc in basic_calls
            assert desc in interactive_calls

    def test_command_aliases_shown_consistently(self):
        """Regression test: Command aliases should be shown in both modes."""
        aliases_to_check = [
            ("(/m)", "model"),
            ("(/p)", "provider"),
            ("(/cls)", "clear"),
            ("(/h, /?)", "help"),
            ("(/quit, /q)", "exit"),
        ]

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

        for alias, _ in aliases_to_check:
            assert alias in basic_calls
            assert alias in interactive_calls
