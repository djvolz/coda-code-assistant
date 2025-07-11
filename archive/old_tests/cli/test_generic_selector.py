"""Tests for generic selector UI components."""

from unittest.mock import Mock, patch

import pytest

from coda.cli.generic_selector import (
    ExportSelector,
    GenericSelector,
    ModeSelector,
    SessionCommandSelector,
)


class TestGenericSelector:
    """Test the generic selector base class."""

    def test_initialization(self):
        """Test selector initialization."""
        options = [("opt1", "Option 1"), ("opt2", "Option 2")]
        selector = GenericSelector("Test Title", options)

        assert selector.title == "Test Title"
        assert selector.options == options
        assert selector.current_index == 0
        assert selector.selected_option is None

    def test_get_formatted_options(self):
        """Test formatting of options."""
        options = [("save", "Save file"), ("load", "Load file")]
        selector = GenericSelector("File Operations", options)

        formatted = selector.get_formatted_options()

        # Should have title, options, and help text
        assert len(formatted) >= 4  # Title + 2 options + help

        # Check title
        assert formatted[0][1] == "\nFile Operations\n"

        # Check first option is selected (has arrow)
        assert "▶ save" in formatted[1][1]
        assert "Save file" in formatted[1][1]

        # Check second option is not selected
        assert "  load" in formatted[2][1]
        assert "Load file" in formatted[2][1]

    def test_key_bindings(self):
        """Test key binding creation."""
        selector = GenericSelector("Test", [("a", "A"), ("b", "B")])
        kb = selector.create_bindings()

        # Should have bindings for navigation and selection
        assert kb is not None
        # Can't easily test the actual bindings without running the app


class TestExportSelector:
    """Test export format selector."""

    def test_export_options(self):
        """Test that export selector has correct options."""
        selector = ExportSelector()

        assert selector.title == "Select Export Format"
        assert len(selector.options) == 4

        # Check all export formats are present
        formats = [opt[0] for opt in selector.options]
        assert "json" in formats
        assert "markdown" in formats
        assert "txt" in formats
        assert "html" in formats


class TestSessionCommandSelector:
    """Test session command selector."""

    def test_session_options(self):
        """Test that session selector has correct options."""
        selector = SessionCommandSelector()

        assert selector.title == "Select Session Command"
        assert len(selector.options) >= 7  # At least 7 session commands

        # Check key commands are present
        commands = [opt[0] for opt in selector.options]
        assert "save" in commands
        assert "load" in commands
        assert "list" in commands
        assert "delete" in commands
        assert "branch" in commands


class TestModeSelector:
    """Test developer mode selector."""

    def test_mode_options(self):
        """Test that mode selector has correct options."""
        selector = ModeSelector()

        assert selector.title == "Select Developer Mode"
        assert len(selector.options) == 7  # 7 developer modes

        # Check all modes are present
        modes = [opt[0] for opt in selector.options]
        assert "general" in modes
        assert "code" in modes
        assert "debug" in modes
        assert "explain" in modes
        assert "review" in modes
        assert "refactor" in modes
        assert "plan" in modes


@pytest.mark.asyncio
class TestSelectorInteraction:
    """Test interactive behavior of selectors."""

    async def test_selection_flow(self):
        """Test the selection flow."""
        selector = GenericSelector("Test", [("a", "A"), ("b", "B")])

        # Mock the application run at the module level
        with patch("coda.cli.generic_selector.Application") as mock_app:
            mock_instance = Mock()
            mock_app.return_value = mock_instance

            # Mock run_async to set selected_option when called
            async def mock_run():
                selector.selected_option = "a"

            mock_instance.run_async = Mock(side_effect=mock_run)

            result = await selector.select_option_interactive()

            # Should create and run the application
            mock_app.assert_called_once()
            mock_instance.run_async.assert_called_once()

            assert result == "a"

    async def test_cancel_selection(self):
        """Test canceling selection."""
        selector = GenericSelector("Test", [("a", "A"), ("b", "B")])

        with patch("coda.cli.generic_selector.Application") as mock_app:
            mock_instance = Mock()
            mock_app.return_value = mock_instance

            # Mock run_async without setting selected_option (simulates cancel)
            async def mock_run():
                pass  # Don't set selected_option

            mock_instance.run_async = Mock(side_effect=mock_run)

            result = await selector.select_option_interactive()

            assert result is None
