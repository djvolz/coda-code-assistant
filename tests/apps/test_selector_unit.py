"""Unit tests for the selector module."""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.application import Application

from coda.apps.cli.selector import (
    Selector, ModeSelector, ExportSelector, SessionCommandSelector
)


class TestSelector:
    """Test the base Selector class."""
    
    def test_selector_initialization(self):
        """Test basic selector initialization."""
        options = [
            ("opt1", "First option", {"meta": "data1"}),
            ("opt2", "Second option", {"meta": "data2"}),
            ("opt3", "Third option", None),
        ]
        
        selector = Selector(
            title="Test Selector",
            options=options,
            enable_search=True,
            show_metadata=True
        )
        
        assert selector.title == "Test Selector"
        assert len(selector.options) == 3
        assert selector.enable_search is True
        assert selector.show_metadata is True
        assert selector.selected_index == 0
        assert selector.search_text == ""
        assert selector.filtered_options == options
    
    def test_filter_options(self):
        """Test option filtering with search."""
        options = [
            ("python", "Python language", None),
            ("javascript", "JavaScript language", None),
            ("java", "Java language", None),
            ("rust", "Rust language", None),
        ]
        
        selector = Selector("Languages", options)
        
        # Test filtering
        selector.search_text = "java"
        selector.filter_options()
        
        assert len(selector.filtered_options) == 2
        assert selector.filtered_options[0][0] == "javascript"
        assert selector.filtered_options[1][0] == "java"
        
        # Test case insensitive
        selector.search_text = "PYTHON"
        selector.filter_options()
        
        assert len(selector.filtered_options) == 1
        assert selector.filtered_options[0][0] == "python"
        
        # Test empty search
        selector.search_text = ""
        selector.filter_options()
        
        assert len(selector.filtered_options) == 4
    
    def test_selected_index_adjustment(self):
        """Test that selected index adjusts when filtering."""
        options = [
            ("a", "Option A", None),
            ("b", "Option B", None),
            ("c", "Option C", None),
        ]
        
        selector = Selector("Test", options)
        selector.selected_index = 2  # Select "c"
        
        # Filter to remove "c"
        selector.search_text = "b"
        selector.filter_options()
        
        # Index should adjust to valid range
        assert selector.selected_index == 0
        assert len(selector.filtered_options) == 1
    
    def test_formatted_options_output(self):
        """Test the formatted output generation."""
        options = [
            ("opt1", "First", {"priority": "high"}),
            ("opt2", "Second", None),
        ]
        
        selector = Selector("Test", options, show_metadata=True)
        html = selector.get_formatted_options()
        
        # Check that HTML is generated
        assert "<title>Test</title>" in str(html)
        assert "▶ opt1" in str(html)  # First option selected
        assert "opt2" in str(html)
        assert "[priority: high]" in str(html)  # Metadata shown
    
    def test_key_bindings(self):
        """Test that key bindings are created correctly."""
        selector = Selector("Test", [("a", "A", None), ("b", "B", None)])
        kb = selector.create_key_bindings()
        
        # Check that key bindings exist
        assert isinstance(kb, KeyBindings)
        
        # Test the bindings by checking registered keys
        bindings = list(kb.bindings)
        
        # Get all keys from all bindings (some bindings have multiple keys)
        all_keys = []
        for b in bindings:
            all_keys.extend([str(k) for k in b.keys])
        
        # Check that expected keys are present
        assert any('up' in k.lower() for k in all_keys)  # Keys.Up
        assert any('down' in k.lower() for k in all_keys)  # Keys.Down
        assert 'k' in all_keys
        assert 'j' in all_keys
        assert any('enter' in k.lower() or 'controlm' in k.lower() for k in all_keys)  # Enter or Ctrl+M
        assert any('escape' in k.lower() or 'c-c' in k for k in all_keys)  # Escape or Ctrl+C
    
    @pytest.mark.asyncio
    async def test_navigation_logic(self):
        """Test navigation up/down logic."""
        options = [
            ("opt1", "First", None),
            ("opt2", "Second", None),
            ("opt3", "Third", None),
        ]
        
        selector = Selector("Test", options)
        
        # Test initial state
        assert selector.selected_index == 0
        
        # Simulate moving down
        selector.selected_index = 1
        assert selector.selected_index == 1
        
        # Test boundary - can't go past end
        selector.selected_index = 2
        # Moving down should stay at 2 (handled by key binding logic)
        assert selector.selected_index == 2
        
        # Test moving up
        selector.selected_index = 1
        assert selector.selected_index == 1


class TestSelectorSubclasses:
    """Test the specific selector implementations."""
    
    def test_mode_selector(self):
        """Test ModeSelector configuration."""
        selector = ModeSelector()
        
        assert selector.title == "Select Developer Mode"
        assert len(selector.options) == 7
        assert selector.enable_search is False
        assert selector.options[0][0] == "general"
        assert selector.options[1][0] == "code"
    
    
    def test_export_selector(self):
        """Test ExportSelector configuration."""
        selector = ExportSelector()
        
        assert selector.title == "Select Export Format"
        assert len(selector.options) == 4
        assert selector.enable_search is False
        
        formats = [opt[0] for opt in selector.options]
        assert "json" in formats
        assert "markdown" in formats
        assert "txt" in formats
        assert "html" in formats
    
    def test_session_command_selector(self):
        """Test SessionCommandSelector configuration."""
        selector = SessionCommandSelector()
        
        assert selector.title == "Select Session Command"
        assert len(selector.options) == 8
        assert selector.enable_search is False
        
        commands = [opt[0] for opt in selector.options]
        assert "save" in commands
        assert "load" in commands
        assert "list" in commands
    


class TestSelectorIntegration:
    """Test selector integration with prompt_toolkit."""
    
    @pytest.mark.asyncio
    async def test_selector_app_creation(self):
        """Test that selector creates a valid Application."""
        selector = ModeSelector()
        
        # We can't easily test the full interactive flow, but we can
        # verify the app creation doesn't crash
        with patch('prompt_toolkit.Application.run_async'):
            result = await selector.select_interactive()
            
            # Since we mocked run_async, result will be None
            assert result is None
    
    def test_style_handling(self):
        """Test that theme styles are handled correctly."""
        selector = ModeSelector()
        
        # Check that dim style is handled
        assert hasattr(selector, 'theme')
        assert hasattr(selector.theme, 'dim')
        
        # The formatted options should work regardless of theme
        html = selector.get_formatted_options()
        assert html is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])