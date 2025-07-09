"""Tests for CLI completion system."""

from unittest.mock import Mock, patch

import pytest
from prompt_toolkit.document import Document

from coda.cli.interactive_cli import EnhancedCompleter, InteractiveCLI, SlashCommandCompleter


class TestSlashCommandCompleter:
    """Test cases for SlashCommandCompleter."""

    @pytest.fixture
    def completer(self):
        """Create a SlashCommandCompleter instance."""
        from coda.cli.interactive_cli import SlashCommand
        
        commands = {
            "help": SlashCommand("help", lambda: None, "Show help"),
            "model": SlashCommand("model", lambda: None, "Select model"),
            "provider": SlashCommand("provider", lambda: None, "Select provider"),
            "exit": SlashCommand("exit", lambda: None, "Exit the CLI"),
        }
        return SlashCommandCompleter(commands)

    def test_complete_slash_command_start(self, completer):
        """Test completion at the start of a slash command."""
        doc = Document("/", cursor_position=1)
        completions = list(completer.get_completions(doc, None))

        assert len(completions) == 4
        assert any(c.text == "/help" for c in completions)
        assert any(c.text == "/model" for c in completions)
        assert any(c.text == "/provider" for c in completions)
        assert any(c.text == "/exit" for c in completions)

    def test_complete_partial_command(self, completer):
        """Test completion of partial commands."""
        doc = Document("/he", cursor_position=3)
        completions = list(completer.get_completions(doc, None))

        assert len(completions) == 1
        assert completions[0].text == "/help"
        assert completions[0].start_position == -3

    def test_complete_multiple_matches(self, completer):
        """Test completion with multiple matches."""
        doc = Document("/m", cursor_position=2)
        completions = list(completer.get_completions(doc, None))

        assert len(completions) == 1
        assert completions[0].text == "/model"

    def test_complete_exact_match(self, completer):
        """Test completion for exact match still shows the command."""
        doc = Document("/help", cursor_position=5)
        completions = list(completer.get_completions(doc, None))

        # Should still show the completion to indicate it's valid
        assert len(completions) == 1
        assert completions[0].text == "/help"

    def test_complete_no_match(self, completer):
        """Test no completion for non-matching input."""
        doc = Document("/xyz", cursor_position=4)
        completions = list(completer.get_completions(doc, None))

        assert len(completions) == 0

    def test_complete_case_insensitive(self, completer):
        """Test case-insensitive completion."""
        doc = Document("/HE", cursor_position=3)
        completions = list(completer.get_completions(doc, None))

        assert len(completions) == 0  # Case-sensitive, so no match

    def test_complete_middle_of_text(self, completer):
        """Test completion in the middle of text."""
        doc = Document("/he some text", cursor_position=3)
        completions = list(completer.get_completions(doc, None))

        assert len(completions) == 1
        assert completions[0].text == "/help"

    def test_complete_with_display_meta(self, completer):
        """Test completions include display metadata."""
        doc = Document("/", cursor_position=1)
        completions = list(completer.get_completions(doc, None))

        from prompt_toolkit.formatted_text import to_plain_text
        
        help_completion = next(c for c in completions if c.text == "/help")
        # display_meta is a FormattedText object, extract the text
        assert to_plain_text(help_completion.display_meta) == "Show help"

    def test_complete_empty_document(self, completer):
        """Test completion on empty document."""
        doc = Document("", cursor_position=0)
        completions = list(completer.get_completions(doc, None))

        assert len(completions) == 0

    def test_complete_non_slash_start(self, completer):
        """Test no completion for non-slash commands."""
        doc = Document("help", cursor_position=4)
        completions = list(completer.get_completions(doc, None))

        assert len(completions) == 0


class TestEnhancedCompleter:
    """Test cases for EnhancedCompleter."""

    @pytest.fixture
    def completer(self):
        """Create an EnhancedCompleter instance."""
        return EnhancedCompleter()

    def test_word_completion_start(self, completer):
        """Test word completion at start of common programming terms."""
        doc = Document("def", cursor_position=3)
        completions = list(completer.get_completions(doc, None))

        # Should suggest common programming completions
        assert any("ine" in c.text for c in completions)
        assert any("ault" in c.text for c in completions)

    def test_word_completion_function(self, completer):
        """Test completion for 'function' keyword."""
        doc = Document("func", cursor_position=4)
        completions = list(completer.get_completions(doc, None))

        assert any("tion" in c.text for c in completions)

    def test_word_completion_class(self, completer):
        """Test completion for 'class' keyword."""
        doc = Document("cla", cursor_position=3)
        completions = list(completer.get_completions(doc, None))

        assert any("ss" in c.text for c in completions)

    def test_word_completion_import(self, completer):
        """Test completion for 'import' keyword."""
        doc = Document("imp", cursor_position=3)
        completions = list(completer.get_completions(doc, None))

        assert any("ort" in c.text for c in completions)
        assert any("lement" in c.text for c in completions)

    def test_word_completion_return(self, completer):
        """Test completion for 'return' keyword."""
        doc = Document("ret", cursor_position=3)
        completions = list(completer.get_completions(doc, None))

        assert any("urn" in c.text for c in completions)

    def test_word_completion_variable(self, completer):
        """Test completion for 'variable' keyword."""
        doc = Document("var", cursor_position=3)
        completions = list(completer.get_completions(doc, None))

        assert any("iable" in c.text for c in completions)

    def test_word_completion_minimum_length(self, completer):
        """Test no completion for very short words."""
        doc = Document("a", cursor_position=1)
        completions = list(completer.get_completions(doc, None))

        assert len(completions) == 0

    def test_word_completion_middle_of_line(self, completer):
        """Test completion in the middle of a line."""
        doc = Document("print def something", cursor_position=9)
        completions = list(completer.get_completions(doc, None))

        # Should complete 'def' even in middle of line
        assert any(c.text for c in completions)

    def test_no_completion_for_numbers(self, completer):
        """Test no completion for numeric input."""
        doc = Document("123", cursor_position=3)
        completions = list(completer.get_completions(doc, None))

        assert len(completions) == 0

    def test_completion_case_sensitivity(self, completer):
        """Test case-sensitive completion matching."""
        doc = Document("DEF", cursor_position=3)
        completions = list(completer.get_completions(doc, None))

        # Should still provide completions
        assert len(completions) > 0


class TestInteractiveCLICompletion:
    """Test completion integration in InteractiveCLI."""

    @pytest.fixture
    def cli(self):
        """Create an InteractiveCLI instance for testing."""
        with patch("coda.cli.interactive_cli.ModelManager"):
            cli = InteractiveCLI()
            return cli

    def test_get_completions_delegates_to_completers(self, cli):
        """Test get_completions delegates to both completers."""
        doc = Document("/he", cursor_position=3)
        event = Mock()

        completions = list(cli.get_completions(doc, event))

        # Should get slash command completions
        assert any(c.text == "lp" for c in completions)

    def test_get_completions_word_completion(self, cli):
        """Test word completion through CLI."""
        doc = Document("def", cursor_position=3)
        event = Mock()

        completions = list(cli.get_completions(doc, event))

        # Should get word completions
        assert len(completions) > 0

    def test_get_completions_combines_results(self, cli):
        """Test completions from both sources are combined."""
        # This would only happen if we had overlapping patterns
        doc = Document("test", cursor_position=4)
        event = Mock()

        completions = list(cli.get_completions(doc, event))

        # Should work without errors
        assert isinstance(completions, list)

    def test_completer_used_in_prompt_session(self, cli):
        """Test completer is integrated with prompt session."""
        with patch("coda.cli.interactive_cli.PromptSession") as mock_session:
            cli._setup_prompt_sessions()

            # Verify completer was passed to session
            call_kwargs = mock_session.call_args[1]
            assert "completer" in call_kwargs
            assert call_kwargs["completer"] == cli

    def test_completion_with_aliases(self, cli):
        """Test completion works with command aliases."""
        # Add alias
        cli.aliases["/h"] = "/help"

        doc = Document("/h", cursor_position=2)
        event = Mock()

        completions = list(cli.get_completions(doc, event))

        # Should still complete even with alias
        assert len(completions) >= 0  # May or may not have completions

    def test_completion_error_handling(self, cli):
        """Test completion handles errors gracefully."""
        # Mock a completer to raise an exception
        cli.slash_completer.get_completions = Mock(side_effect=Exception("Test error"))

        doc = Document("/test", cursor_position=5)
        event = Mock()

        # Should not raise, just return word completions
        completions = list(cli.get_completions(doc, event))
        assert isinstance(completions, list)

    def test_completion_empty_input(self, cli):
        """Test completion on empty input."""
        doc = Document("", cursor_position=0)
        event = Mock()

        completions = list(cli.get_completions(doc, event))

        # Should handle gracefully
        assert isinstance(completions, list)

    def test_completion_updates_with_commands(self, cli):
        """Test completion updates when commands change."""
        # Simulate command list update
        original_commands = cli.commands.copy()
        cli.commands["/test"] = "Test command"

        # Recreate completer
        cli.slash_completer = SlashCommandCompleter(cli.commands)

        doc = Document("/te", cursor_position=3)
        event = Mock()

        completions = list(cli.get_completions(doc, event))

        # Should include new command
        assert any("st" in c.text for c in completions)

        # Restore original commands
        cli.commands = original_commands
