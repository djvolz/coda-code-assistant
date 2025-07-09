"""Tests for interactive CLI tab completion integration."""

from unittest.mock import Mock

import pytest
from prompt_toolkit.document import Document

from coda.cli.completers import CodaCompleter
from coda.cli.interactive_cli import InteractiveCLI
from coda.providers.base import Model


class MockCompleteEvent:
    """Mock completion event for testing."""

    pass


class TestInteractiveCLICompletion:
    """Test tab completion in the interactive CLI."""

    @pytest.fixture
    def cli(self):
        """Create an interactive CLI instance for testing."""
        cli = InteractiveCLI()
        # Mock provider that returns models
        mock_provider = Mock()
        mock_provider.list_models.return_value = [
            Model(id="gpt-4", name="GPT-4", provider="openai"),
            Model(id="gpt-3.5-turbo", name="GPT-3.5 Turbo", provider="openai"),
            Model(id="claude-3", name="Claude 3", provider="anthropic"),
        ]
        cli.provider = mock_provider
        return cli

    def test_cli_has_completer(self, cli):
        """Test that CLI initializes with a completer."""
        assert cli.session is not None
        assert cli.session.completer is not None
        assert isinstance(cli.session.completer, CodaCompleter)

    def test_model_completion_with_provider(self, cli):
        """Test /model completion when provider is available."""
        completer = cli.session.completer
        doc = Document("/model ")

        completions = list(completer.get_completions(doc, MockCompleteEvent()))

        # Should get model completions
        assert len(completions) == 3
        model_ids = [c.text for c in completions]
        assert "gpt-4" in model_ids
        assert "gpt-3.5-turbo" in model_ids
        assert "claude-3" in model_ids

    def test_model_completion_without_provider(self):
        """Test /model completion when provider is None."""
        cli = InteractiveCLI()
        cli.provider = None  # No provider

        completer = cli.session.completer
        doc = Document("/model ")

        completions = list(completer.get_completions(doc, MockCompleteEvent()))

        # Should get no completions
        assert len(completions) == 0

    def test_export_subcommand_completion(self, cli):
        """Test /export subcommand completion."""
        completer = cli.session.completer
        doc = Document("/export ")

        completions = list(completer.get_completions(doc, MockCompleteEvent()))

        # Should get export format completions
        assert len(completions) == 4
        formats = [c.text for c in completions]
        assert "json" in formats
        assert "markdown" in formats
        assert "txt" in formats
        assert "html" in formats

    def test_theme_completion(self, cli):
        """Test /theme completion includes theme names."""
        completer = cli.session.completer
        doc = Document("/theme ")

        completions = list(completer.get_completions(doc, MockCompleteEvent()))

        # Should include theme names and commands
        assert len(completions) > 10  # Many themes + list/current/reset
        completion_texts = [c.text for c in completions]

        # Check some themes
        assert "dark" in completion_texts
        assert "light" in completion_texts
        assert "monokai_dark" in completion_texts

        # Check commands
        assert "list" in completion_texts
        assert "current" in completion_texts
        assert "reset" in completion_texts

    def test_session_completion_with_manager(self, cli):
        """Test session name completion with session manager."""
        # Mock session manager
        mock_sessions = [
            {"name": "project-review", "message_count": 10, "updated_at": "2024-01-01"},
            {"name": "bug-fix", "message_count": 5, "updated_at": "2024-01-02"},
        ]
        cli.session_commands.list_sessions = Mock(return_value=mock_sessions)

        completer = cli.session.completer
        doc = Document("/session load ")

        completions = list(completer.get_completions(doc, MockCompleteEvent()))

        # Should get session name completions
        assert len(completions) == 2
        names = [c.text for c in completions]
        assert "project-review" in names
        assert "bug-fix" in names

    def test_fuzzy_command_matching(self, cli):
        """Test fuzzy matching for commands."""
        completer = cli.session.completer

        # Test fuzzy match /mdl -> /model
        doc = Document("/mdl")
        completions = list(completer.get_completions(doc, MockCompleteEvent()))
        assert any(c.text == "/model" for c in completions)

        # Test fuzzy match /ses -> /session
        doc = Document("/ses")
        completions = list(completer.get_completions(doc, MockCompleteEvent()))
        assert any(c.text == "/session" for c in completions)

    def test_empty_input_shows_all_commands(self, cli):
        """Test that empty input shows all commands."""
        completer = cli.session.completer
        doc = Document("")

        completions = list(completer.get_completions(doc, MockCompleteEvent()))

        # Should show all commands
        assert len(completions) >= 10  # At least 10 commands

        # Check some key commands
        command_texts = [c.text for c in completions]
        assert "/help" in command_texts
        assert "/model" in command_texts
        assert "/exit" in command_texts
        assert "/session" in command_texts

    def test_no_completion_for_regular_text(self, cli):
        """Test that regular text gets no completions."""
        completer = cli.session.completer
        doc = Document("hello world")

        completions = list(completer.get_completions(doc, MockCompleteEvent()))

        # Should get no completions
        assert len(completions) == 0

    def test_completion_uses_theme_colors(self, cli):
        """Test that completions use theme colors."""
        completer = cli.session.completer
        doc = Document("/")

        completions = list(completer.get_completions(doc, MockCompleteEvent()))

        # Check that completions have styles
        assert len(completions) > 0
        for completion in completions:
            assert completion.style is not None
            # Style should contain theme color
            assert "bold" in completion.style or "#" in completion.style
