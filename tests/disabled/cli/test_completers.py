"""Tests for enhanced tab completion system."""

from unittest.mock import Mock, patch

import pytest
from prompt_toolkit.document import Document

from coda.cli.completers import (
    CodaCompleter,
    DynamicValueCompleter,
    FuzzyMatcher,
    SlashCommandCompleter,
)
from coda.cli.interactive_cli import SlashCommand


class MockCompleteEvent:
    """Mock CompleteEvent for testing."""

    pass


class TestFuzzyMatcher:
    """Test fuzzy matching functionality."""

    def test_exact_match(self):
        """Test exact string match."""
        matches, score = FuzzyMatcher.fuzzy_match("help", "help")
        assert matches is True
        assert score == 1.0

    def test_prefix_match(self):
        """Test prefix matching."""
        matches, score = FuzzyMatcher.fuzzy_match("hel", "help")
        assert matches is True
        assert score == 0.9

    def test_fuzzy_match(self):
        """Test fuzzy character matching."""
        matches, score = FuzzyMatcher.fuzzy_match("hp", "help")
        assert matches is True
        assert 0 < score < 0.9

    def test_no_match(self):
        """Test non-matching strings."""
        matches, score = FuzzyMatcher.fuzzy_match("xyz", "help")
        assert matches is False
        assert score == 0.0

    def test_case_insensitive(self):
        """Test case insensitive matching."""
        matches, score = FuzzyMatcher.fuzzy_match("HELP", "help")
        assert matches is True
        assert score == 1.0


class TestSlashCommandCompleter:
    """Test slash command completion."""

    @pytest.fixture
    def commands(self):
        """Create test commands."""
        return {
            "help": SlashCommand("help", lambda: None, "Show help", ["h"]),
            "session": SlashCommand("session", lambda: None, "Session management"),
            "model": SlashCommand("model", lambda: None, "Change model"),
        }

    @pytest.fixture
    def completer(self, commands):
        """Create completer with test commands."""
        return SlashCommandCompleter(commands)

    def test_empty_input_shows_all_commands(self, completer):
        """Test that empty input shows all commands."""
        doc = Document("")
        completions = list(completer.get_completions(doc, MockCompleteEvent()))

        assert len(completions) == 3
        assert any(c.text == "/help" for c in completions)
        assert any(c.text == "/session" for c in completions)
        assert any(c.text == "/model" for c in completions)

    def test_slash_only_shows_all_commands(self, completer):
        """Test that / alone shows all commands."""
        doc = Document("/")
        completions = list(completer.get_completions(doc, MockCompleteEvent()))

        assert len(completions) >= 3

    def test_prefix_completion(self, completer):
        """Test command prefix completion."""
        doc = Document("/hel")
        completions = list(completer.get_completions(doc, MockCompleteEvent()))

        assert len(completions) == 1
        assert completions[0].text == "/help"

    def test_alias_completion(self, completer):
        """Test command alias completion."""
        doc = Document("/h")
        completions = list(completer.get_completions(doc, MockCompleteEvent()))

        # Should find help command (aliases are not shown in completions)
        assert any(c.text == "/help" for c in completions)
        # Aliases are not shown as separate completions anymore
        assert not any(c.text == "/h" for c in completions)

    def test_fuzzy_completion(self, completer):
        """Test fuzzy command completion."""
        doc = Document("/mdl")
        completions = list(completer.get_completions(doc, MockCompleteEvent()))

        assert len(completions) == 1
        assert completions[0].text == "/model"

    def test_no_slash_no_completion(self, completer):
        """Test that text without / gets no completions."""
        doc = Document("help")
        completions = list(completer.get_completions(doc, MockCompleteEvent()))

        assert len(completions) == 0


class TestDynamicValueCompleter:
    """Test model name completion."""

    class MockProvider:
        """Mock provider for testing."""

        def list_models(self):
            from unittest.mock import Mock

            # Return mock Model objects with id attributes
            models = []
            for model_id in ["gpt-4", "gpt-3.5-turbo", "claude-3-opus"]:
                model = Mock()
                model.id = model_id
                models.append(model)
            return models

    def test_model_completion(self):
        """Test model name completion."""
        provider = self.MockProvider()
        completer = DynamicValueCompleter(get_provider_func=lambda: provider)

        # Need to mock the command registry
        with patch("coda.cli.command_registry.CommandRegistry") as mock_registry:
            mock_cmd = Mock()
            mock_cmd.name = "model"
            mock_cmd.completion_type = "model_name"
            mock_cmd.subcommands = []
            mock_registry.get_command.return_value = mock_cmd

            doc = Document("/model gpt")
            completions = list(completer.get_completions(doc, MockCompleteEvent()))

            assert len(completions) == 2
            assert any(c.text == "gpt-4" for c in completions)
            assert any(c.text == "gpt-3.5-turbo" for c in completions)

    def test_no_provider_no_completion(self):
        """Test no completions when provider is None."""
        completer = DynamicValueCompleter(get_provider_func=lambda: None)

        with patch("coda.cli.command_registry.CommandRegistry") as mock_registry:
            mock_cmd = Mock()
            mock_cmd.name = "model"
            mock_cmd.completion_type = "model_name"
            mock_cmd.subcommands = []
            mock_registry.get_command.return_value = mock_cmd

            doc = Document("/model gpt")
            completions = list(completer.get_completions(doc, MockCompleteEvent()))

            assert len(completions) == 0

    def test_fuzzy_model_completion(self):
        """Test fuzzy model name matching."""
        provider = self.MockProvider()
        completer = DynamicValueCompleter(get_provider_func=lambda: provider)

        with patch("coda.cli.command_registry.CommandRegistry") as mock_registry:
            mock_cmd = Mock()
            mock_cmd.name = "model"
            mock_cmd.completion_type = "model_name"
            mock_cmd.subcommands = []
            mock_registry.get_command.return_value = mock_cmd

            doc = Document("/model cld")
            completions = list(completer.get_completions(doc, MockCompleteEvent()))

            assert len(completions) == 1
            assert completions[0].text == "claude-3-opus"


class TestSessionCompletion:
    """Test session name completion through dynamic completer."""

    class MockSessionCommands:
        """Mock session commands for testing."""

        def list_sessions(self):
            return [
                {"name": "project-review", "message_count": 10, "updated_at": "2024-01-01"},
                {"name": "bug-fix", "message_count": 5, "updated_at": "2024-01-02"},
                {"name": "feature-planning", "message_count": 20, "updated_at": "2024-01-03"},
            ]

    def test_session_load_completion(self):
        """Test session name completion for load command."""
        session_cmds = self.MockSessionCommands()
        completer = DynamicValueCompleter(session_commands=session_cmds)

        with patch("coda.cli.command_registry.CommandRegistry") as mock_registry:
            # Mock main command
            mock_cmd = Mock()
            mock_cmd.completion_type = None
            mock_cmd.subcommands = []

            # Mock subcommand
            mock_sub = Mock()
            mock_sub.completion_type = "session_name"
            mock_sub.get_all_names.return_value = ["load", "l"]
            mock_cmd.subcommands = [mock_sub]

            mock_registry.get_command.return_value = mock_cmd

            doc = Document("/session load proj")
            completions = list(completer.get_completions(doc, MockCompleteEvent()))

            assert len(completions) == 1
            assert completions[0].text == "project-review"
            assert "10 msgs" in str(completions[0].display_meta)

    def test_session_delete_completion(self):
        """Test session name completion for delete command."""
        session_cmds = self.MockSessionCommands()
        completer = DynamicValueCompleter(session_commands=session_cmds)

        with patch("coda.cli.command_registry.CommandRegistry") as mock_registry:
            mock_cmd = Mock()
            mock_cmd.completion_type = None

            mock_sub = Mock()
            mock_sub.completion_type = "session_name"
            mock_sub.get_all_names.return_value = ["delete", "d", "rm"]
            mock_cmd.subcommands = [mock_sub]

            mock_registry.get_command.return_value = mock_cmd

            doc = Document("/session delete bug")
            completions = list(completer.get_completions(doc, MockCompleteEvent()))

            assert len(completions) == 1
            assert completions[0].text == "bug-fix"

    def test_fuzzy_session_completion(self):
        """Test fuzzy session name matching."""
        session_cmds = self.MockSessionCommands()
        completer = DynamicValueCompleter(session_commands=session_cmds)

        with patch("coda.cli.command_registry.CommandRegistry") as mock_registry:
            mock_cmd = Mock()
            mock_cmd.completion_type = None

            mock_sub = Mock()
            mock_sub.completion_type = "session_name"
            mock_sub.get_all_names.return_value = ["load", "l"]
            mock_cmd.subcommands = [mock_sub]

            mock_registry.get_command.return_value = mock_cmd

            doc = Document("/session load ftr")
            completions = list(completer.get_completions(doc, MockCompleteEvent()))

            assert len(completions) == 1
            assert completions[0].text == "feature-planning"


class TestCodaCompleter:
    """Test the main enhanced completer."""

    @pytest.fixture
    def commands(self):
        """Create test commands."""
        return {
            "help": SlashCommand("help", lambda: None, "Show help"),
            "exit": SlashCommand("exit", lambda: None, "Exit the program"),
        }

    def test_slash_command_priority(self, commands):
        """Test that slash commands take priority."""
        completer = CodaCompleter(commands)

        doc = Document("/hel")
        completions = list(completer.get_completions(doc, MockCompleteEvent()))

        assert len(completions) == 1
        assert completions[0].text == "/help"

    def test_empty_shows_commands(self, commands):
        """Test empty input shows available commands."""
        completer = CodaCompleter(commands)

        doc = Document("")
        completions = list(completer.get_completions(doc, MockCompleteEvent()))

        assert len(completions) == 2
        assert any(c.text == "/help" for c in completions)
        assert any(c.text == "/exit" for c in completions)

    def test_path_completion(self, commands):
        """Test path completion for file paths."""
        completer = CodaCompleter(commands)

        # Path completion is delegated to PathCompleter
        # Just verify it doesn't crash
        doc = Document("~/test")
        list(completer.get_completions(doc, MockCompleteEvent()))
        # Results depend on filesystem

    def test_no_regular_text_completion(self, commands):
        """Test that regular text gets no completions."""
        completer = CodaCompleter(commands)

        doc = Document("hello world")
        completions = list(completer.get_completions(doc, MockCompleteEvent()))

        assert len(completions) == 0
