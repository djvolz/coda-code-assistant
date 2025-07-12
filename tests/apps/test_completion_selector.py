"""Unit tests for the completion-based selector."""

from unittest.mock import Mock, patch

import pytest

from coda.apps.cli.completion_selector import (
    CompletionModelSelector,
    CompletionSelector,
    CompletionThemeSelector,
    OptionCompleter,
)


class TestOptionCompleter:
    """Test the OptionCompleter class."""

    def test_completer_initialization(self):
        """Test completer initialization with options."""
        options = [
            ("opt1", "First option", {"key": "value"}),
            ("opt2", "Second option", None),
            ("opt3", "Third option", {"priority": "high"}),
        ]

        completer = OptionCompleter(options)
        assert completer.options == options

    def test_get_completions_no_filter(self):
        """Test getting all completions with no filter text."""
        options = [
            ("python", "Python language", None),
            ("java", "Java language", None),
        ]

        completer = OptionCompleter(options)

        # Mock document with empty text
        mock_doc = Mock()
        mock_doc.text_before_cursor = ""

        completions = list(completer.get_completions(mock_doc, None))

        # Should return all options
        assert len(completions) == 2
        assert completions[0].text == "python"
        assert completions[1].text == "java"

    def test_get_completions_with_filter(self):
        """Test filtering completions based on input."""
        options = [
            ("python", "Python language", None),
            ("javascript", "JavaScript language", None),
            ("java", "Java language", None),
            ("rust", "Rust language", None),
        ]

        completer = OptionCompleter(options)

        # Mock document with "java" as filter
        mock_doc = Mock()
        mock_doc.text_before_cursor = "java"

        completions = list(completer.get_completions(mock_doc, None))

        # Should return only java-related options
        assert len(completions) == 2
        assert completions[0].text == "javascript"
        assert completions[1].text == "java"

    def test_completions_with_metadata(self):
        """Test that completions include metadata in display."""
        options = [
            ("gpt-4", "OpenAI model", {"context": "8k", "provider": "openai"}),
        ]

        completer = OptionCompleter(options)

        mock_doc = Mock()
        mock_doc.text_before_cursor = ""

        completions = list(completer.get_completions(mock_doc, None))

        assert len(completions) == 1
        completion = completions[0]

        # Check that metadata is in the display
        display_text = str(completion.display)
        assert "context: 8k" in display_text
        assert "provider: openai" in display_text


class TestCompletionSelector:
    """Test the CompletionSelector class."""

    def test_selector_initialization(self):
        """Test selector initialization."""
        options = [
            ("opt1", "First", None),
            ("opt2", "Second", {"meta": "data"}),
        ]

        selector = CompletionSelector(
            title="Test Selector",
            options=options,
            prompt_text="Select: ",
            instruction_text="Custom instructions",
        )

        assert selector.title == "Test Selector"
        assert selector.options == options
        assert selector.prompt_text == "Select: "
        assert selector.instruction_text == "Custom instructions"

    def test_create_prompt_session(self):
        """Test prompt session creation."""
        selector = CompletionSelector(
            title="Test",
            options=[("a", "A", None)],
        )

        session = selector.create_prompt_session()

        assert session is not None
        assert session.completer is not None
        assert session.complete_while_typing is True
        assert session.style is not None

    @pytest.mark.asyncio
    async def test_select_interactive_cancelled(self):
        """Test handling cancellation."""
        selector = CompletionSelector(
            title="Test",
            options=[("a", "A", None)],
        )

        # Mock prompt_async to raise EOFError (Ctrl+D)
        with patch.object(selector, "create_prompt_session") as mock_create:
            mock_session = Mock()
            mock_session.prompt_async.side_effect = EOFError()
            mock_create.return_value = mock_session

            result = await selector.select_interactive()

            assert result is None

    @pytest.mark.asyncio
    async def test_select_interactive_valid_selection(self):
        """Test valid selection."""
        options = [("theme1", "Theme 1", None), ("theme2", "Theme 2", None)]
        selector = CompletionSelector(
            title="Test",
            options=options,
        )

        # Mock prompt_async to return a valid value
        with patch.object(selector, "create_prompt_session") as mock_create:
            mock_session = Mock()

            # Create an async function that returns the value
            async def mock_prompt_async(*args, **kwargs):
                # Check that pre_run was passed when auto_complete is True
                if "pre_run" in kwargs and kwargs["pre_run"] is not None:
                    # Simulate pre_run being called
                    pass
                return "theme1"

            mock_session.prompt_async = mock_prompt_async
            mock_create.return_value = mock_session

            result = await selector.select_interactive()

            assert result == "theme1"

    @pytest.mark.asyncio
    async def test_auto_complete_feature(self):
        """Test that auto_complete parameter works."""
        options = [("opt1", "Option 1", None)]
        selector = CompletionSelector(
            title="Test",
            options=options,
        )

        # Test with auto_complete=True (default)
        with patch.object(selector, "create_prompt_session") as mock_create:
            mock_session = Mock()
            pre_run_called = False

            async def mock_prompt_async(*args, **kwargs):
                nonlocal pre_run_called
                if "pre_run" in kwargs and kwargs["pre_run"] is not None:
                    pre_run_called = True
                return "opt1"

            mock_session.prompt_async = mock_prompt_async
            mock_create.return_value = mock_session

            await selector.select_interactive(auto_complete=True)
            assert pre_run_called  # pre_run should be set

        # Test with auto_complete=False
        with patch.object(selector, "create_prompt_session") as mock_create:
            mock_session = Mock()
            pre_run_called = False

            async def mock_prompt_async(*args, **kwargs):
                nonlocal pre_run_called
                if "pre_run" in kwargs and kwargs["pre_run"] is not None:
                    pre_run_called = True
                return "opt1"

            mock_session.prompt_async = mock_prompt_async
            mock_create.return_value = mock_session

            await selector.select_interactive(auto_complete=False)
            assert not pre_run_called  # pre_run should be None

    @pytest.mark.asyncio
    async def test_select_interactive_case_insensitive(self):
        """Test case-insensitive matching."""
        options = [("Theme1", "Theme 1", None)]
        selector = CompletionSelector(
            title="Test",
            options=options,
        )

        # Mock prompt_async to return lowercase version
        with patch.object(selector, "create_prompt_session") as mock_create:
            mock_session = Mock()

            # Create an async function that returns the value
            async def mock_prompt_async(*args, **kwargs):
                return "theme1"

            mock_session.prompt_async = mock_prompt_async
            mock_create.return_value = mock_session

            result = await selector.select_interactive()

            # Should match the original case
            assert result == "Theme1"


class TestCompletionSubclasses:
    """Test the specialized selector subclasses."""

    def test_model_selector(self):
        """Test CompletionModelSelector."""
        # Create mock models
        mock_models = [
            Mock(id="gpt-4", provider="openai", metadata={"context_window": 8192}),
            Mock(id="claude", provider="anthropic", metadata={}),
        ]

        selector = CompletionModelSelector(mock_models)

        assert selector.title == "Select Model"
        assert len(selector.options) == 2

        # Check first option format
        opt1 = selector.options[0]
        assert opt1[0] == "gpt-4"
        assert opt1[1] == "openai"
        assert opt1[2]["provider"] == "openai"
        assert opt1[2]["context"] == "8,192"

    def test_theme_selector(self):
        """Test CompletionThemeSelector."""
        selector = CompletionThemeSelector()

        assert selector.title == "Select Theme"
        assert len(selector.options) > 0

        # Check that options have the expected format
        for value, description, metadata in selector.options:
            assert isinstance(value, str)
            assert isinstance(description, str)
            assert isinstance(metadata, dict)
            assert "dark" in metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
