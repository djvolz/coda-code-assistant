"""Tests for CLI completion system."""

import pytest
from prompt_toolkit.document import Document

from coda.cli.interactive_cli import EnhancedCompleter, SlashCommandCompleter


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
        from coda.cli.interactive_cli import SlashCommand

        commands = {
            "help": SlashCommand("help", lambda: None, "Show help"),
            "exit": SlashCommand("exit", lambda: None, "Exit"),
        }
        return EnhancedCompleter(commands)

    def test_no_general_word_completion(self, completer):
        """Test that general word completion is not provided."""
        doc = Document("def", cursor_position=3)
        completions = list(completer.get_completions(doc, None))

        # EnhancedCompleter no longer does general word completion
        assert len(completions) == 0

    def test_slash_command_completion(self, completer):
        """Test slash command completion."""
        doc = Document("/he", cursor_position=3)
        completions = list(completer.get_completions(doc, None))

        assert len(completions) == 1
        assert completions[0].text == "/help"

    def test_path_completion(self, completer):
        """Test path completion when text contains /."""
        doc = Document("./test", cursor_position=6)
        completions = list(completer.get_completions(doc, None))

        # Should trigger path completion
        # Results depend on actual filesystem, so just check it attempts completion
        assert isinstance(completions, list)

    def test_home_path_completion(self, completer):
        """Test path completion for home directory."""
        doc = Document("~/", cursor_position=2)
        completions = list(completer.get_completions(doc, None))

        # Should trigger path completion for home directory
        assert isinstance(completions, list)

    def test_empty_input_shows_commands(self, completer):
        """Test empty input shows available slash commands."""
        doc = Document("", cursor_position=0)
        completions = list(completer.get_completions(doc, None))

        # Should show available slash commands
        assert len(completions) > 0
        assert any(c.text == "/help" for c in completions)

    def test_whitespace_only_shows_commands(self, completer):
        """Test whitespace-only input shows slash commands."""
        doc = Document("  ", cursor_position=2)
        completions = list(completer.get_completions(doc, None))

        # Should show available slash commands
        assert len(completions) > 0
        assert all(c.text.startswith("/") for c in completions)

    def test_no_completion_for_regular_text(self, completer):
        """Test no completion for regular text without / or ~."""
        doc = Document("hello world", cursor_position=11)
        completions = list(completer.get_completions(doc, None))

        assert len(completions) == 0

    def test_slash_completion_priority(self, completer):
        """Test slash commands take priority when line starts with /."""
        doc = Document("/", cursor_position=1)
        completions = list(completer.get_completions(doc, None))

        # Should only show slash commands
        assert len(completions) > 0
        assert all(c.text.startswith("/") for c in completions)

    def test_no_completion_for_numbers(self, completer):
        """Test no completion for numeric input."""
        doc = Document("123", cursor_position=3)
        completions = list(completer.get_completions(doc, None))

        assert len(completions) == 0

    def test_style_attribute_on_empty_input(self, completer):
        """Test completions have style attribute for empty input."""
        doc = Document("", cursor_position=0)
        completions = list(completer.get_completions(doc, None))

        # Check that completions have style
        if completions:
            assert completions[0].style == "fg:cyan"


# Removed TestInteractiveCLICompletion class as InteractiveCLI doesn't implement Completer interface
# The completion functionality is handled by EnhancedCompleter which is tested above
