"""Smoke tests for TUI interface that don't require terminal interaction."""

import pytest
from unittest.mock import Mock, patch

# Mark all tests in this module as tui
pytestmark = pytest.mark.tui

from coda.cli.tui_integrated import (
    IntegratedTUICLI, 
    ModeCommands, 
    ProviderCommands, 
    GeneralCommands,
    CompletionHelper,
    TabCompletableInput,
)
from coda.providers import ProviderFactory
from coda.cli.shared import DeveloperMode


class TestTUIComponents:
    """Test individual TUI components without running the full app."""

    def test_app_initialization(self):
        """Test that the app can be initialized."""
        app = IntegratedTUICLI()
        assert app._developer_mode == DeveloperMode.GENERAL
        assert app._messages == []
        assert app._available_models == []

    def test_app_with_provider(self):
        """Test app initialization with provider."""
        mock_factory = Mock(spec=ProviderFactory)
        app = IntegratedTUICLI(
            provider_factory=mock_factory,
            provider_name="test_provider",
            model="test_model"
        )
        assert app._provider_factory == mock_factory
        assert app._provider_name == "test_provider"
        assert app._model == "test_model"

    def test_completion_helper(self):
        """Test the completion helper functionality."""
        helper = CompletionHelper()
        
        # Test command completions
        completions = helper.get_completions("/")
        assert len(completions) > 0
        assert any("/help" in c[0] for c in completions)
        
        # Test command prefix completion
        completions = helper.get_completions("/mo")
        assert any("/mode" in c[0] for c in completions)
        
        # Test mode argument completion
        completions = helper.get_completions("/mode ")
        assert any("general" in c[0] for c in completions)
        assert any("code" in c[0] for c in completions)

    def test_tab_completable_input_init(self):
        """Test TabCompletableInput initialization."""
        input_widget = TabCompletableInput()
        assert input_widget.completion_helper is not None
        assert input_widget.completions == []
        assert input_widget.completion_index == -1

    @pytest.mark.asyncio
    async def test_mode_commands_provider(self):
        """Test ModeCommands provider."""
        mock_app = Mock()
        provider = ModeCommands(mock_app, None)
        
        hits = []
        async for hit in provider.search("mode"):
            hits.append(hit)
        
        assert len(hits) > 0
        # Check that hits have correct structure
        for hit in hits:
            assert hasattr(hit, 'score')
            assert hasattr(hit, 'match_display')
            assert hasattr(hit, 'command')

    @pytest.mark.asyncio
    async def test_provider_commands_provider(self):
        """Test ProviderCommands provider."""
        mock_app = Mock()
        provider = ProviderCommands(mock_app, None)
        
        hits = []
        async for hit in provider.search("provider"):
            hits.append(hit)
        
        # Should have providers registered
        assert len(hits) >= 3  # oci_genai, litellm, ollama

    @pytest.mark.asyncio
    async def test_general_commands_provider(self):
        """Test GeneralCommands provider."""
        mock_app = Mock()
        mock_app.show_help = Mock()
        mock_app.action_clear = Mock()
        mock_app.export = Mock()
        
        provider = GeneralCommands(mock_app, None)
        
        hits = []
        async for hit in provider.search("help"):
            hits.append(hit)
        
        assert len(hits) > 0
        # Test that we found a help command
        help_hits = [h for h in hits if "help" in h.match_display.lower()]
        assert len(help_hits) > 0

    def test_developer_mode_switching(self):
        """Test developer mode switching logic."""
        app = IntegratedTUICLI()
        
        # Test that modes can be set directly without UI
        app._developer_mode = DeveloperMode.CODE
        assert app._developer_mode == DeveloperMode.CODE
        
        app._developer_mode = DeveloperMode.DEBUG
        assert app._developer_mode == DeveloperMode.DEBUG

    def test_status_bar_text(self):
        """Test status bar text generation."""
        app = IntegratedTUICLI()
        status = app.get_status()
        
        assert "Mode: general" in status
        assert "Provider: Not connected" in status
        assert "Model: No model" in status
        
        # Test with provider and model
        app._provider_name = "test_provider"
        app._model = "test_model"
        status = app.get_status()
        
        assert "Provider: test_provider" in status
        assert "Model: test_model" in status


class TestTUIErrorHandling:
    """Test error handling in TUI interface."""

    def test_invalid_command_handling(self):
        """Test handling of invalid commands."""
        app = IntegratedTUICLI()
        
        # Test that invalid modes are caught
        try:
            invalid_mode = DeveloperMode("nonexistent")
        except ValueError:
            # This is expected
            pass
        
        # App should still have default mode
        assert app._developer_mode == DeveloperMode.GENERAL

    @pytest.mark.asyncio
    async def test_provider_error_handling(self):
        """Test provider error handling."""
        mock_app = Mock()
        provider = ModeCommands(mock_app, None)
        
        # Should handle queries gracefully
        hits = []
        async for hit in provider.search("general"):
            hits.append(hit)
        
        # Should return hits for valid queries
        assert isinstance(hits, list)
        assert len(hits) > 0


# Run basic sanity check
def test_imports():
    """Test that all imports work correctly."""
    from coda.cli.tui_integrated import IntegratedTUICLI
    from coda.cli.shared import DeveloperMode
    from coda.providers import ProviderFactory
    
    # Verify classes can be imported
    assert IntegratedTUICLI is not None
    assert DeveloperMode is not None
    assert ProviderFactory is not None