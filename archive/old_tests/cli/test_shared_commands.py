"""Tests for shared command handling functionality."""

from unittest.mock import Mock

import pytest

from coda.cli.shared import CommandHandler, CommandResult, DeveloperMode


class MockModel:
    """Mock model for testing."""

    def __init__(self, id: str):
        self.id = id
        self.provider = "test"
        self.metadata = {}


class TestCommandHandler(CommandHandler):
    """Concrete implementation for testing."""

    def show_help(self) -> CommandResult:
        """Test implementation of show_help."""
        return CommandResult.HANDLED


class TestSharedCommands:
    """Test the shared command handler functionality."""

    @pytest.fixture
    def handler(self):
        """Create a command handler for testing."""
        console = Mock()
        return TestCommandHandler(console)

    def test_init(self, handler):
        """Test command handler initialization."""
        assert handler.current_mode == DeveloperMode.GENERAL
        assert handler.current_model is None
        assert handler.available_models == []
        assert handler.provider_name is None
        assert handler.provider_instance is None
        assert handler.factory is None

    def test_set_provider_info(self, handler):
        """Test setting provider information."""
        models = [MockModel("model1"), MockModel("model2")]
        factory = Mock()
        provider = Mock()

        handler.set_provider_info("test_provider", provider, factory, "model1", models)

        assert handler.provider_name == "test_provider"
        assert handler.provider_instance == provider
        assert handler.factory == factory
        assert handler.current_model == "model1"
        assert handler.available_models == models

    def test_switch_mode_no_args(self, handler):
        """Test mode switching without arguments."""
        result = handler.switch_mode("")

        assert result == CommandResult.HANDLED
        calls = [str(call) for call in handler.console.print.call_args_list]
        assert any("Current mode" in str(call) for call in calls)
        assert any("general" in str(call) for call in calls)

    def test_switch_mode_valid(self, handler):
        """Test switching to a valid mode."""
        result = handler.switch_mode("code")

        assert result == CommandResult.HANDLED
        assert handler.current_mode == DeveloperMode.CODE
        calls = [str(call) for call in handler.console.print.call_args_list]
        assert any("Switched to code mode" in str(call) for call in calls)

    def test_switch_mode_invalid(self, handler):
        """Test switching to an invalid mode."""
        original_mode = handler.current_mode
        result = handler.switch_mode("invalid")

        assert result == CommandResult.HANDLED
        assert handler.current_mode == original_mode
        calls = [str(call) for call in handler.console.print.call_args_list]
        assert any("Invalid mode" in str(call) for call in calls)

    def test_switch_model_no_models(self, handler):
        """Test model switching when no models available."""
        result = handler.switch_model("")

        assert result == CommandResult.HANDLED
        calls = [str(call) for call in handler.console.print.call_args_list]
        assert any("No models available" in str(call) for call in calls)

    def test_switch_model_list(self, handler):
        """Test listing models."""
        models = [MockModel(f"model{i}") for i in range(15)]
        handler.available_models = models
        handler.current_model = "model0"

        result = handler.switch_model("")

        assert result == CommandResult.HANDLED
        calls = [str(call) for call in handler.console.print.call_args_list]
        assert any("Current model" in str(call) for call in calls)
        assert any("model0" in str(call) for call in calls)
        # Should show top 10 models
        for i in range(10):
            assert any(f"model{i}" in str(call) for call in calls)
        # Should indicate more models
        assert any("5 more" in str(call) for call in calls)

    def test_switch_model_valid(self, handler):
        """Test switching to a valid model."""
        models = [MockModel("gpt-4"), MockModel("gpt-3.5"), MockModel("claude")]
        handler.available_models = models

        result = handler.switch_model("gpt-4")

        assert result == CommandResult.HANDLED
        assert handler.current_model == "gpt-4"
        calls = [str(call) for call in handler.console.print.call_args_list]
        assert any("Switched to model: gpt-4" in str(call) for call in calls)

    def test_switch_model_partial_match(self, handler):
        """Test model switching with partial match."""
        models = [MockModel("test-model-large"), MockModel("test-model-small")]
        handler.available_models = models

        result = handler.switch_model("large")

        assert result == CommandResult.HANDLED
        assert handler.current_model == "test-model-large"

    def test_switch_model_invalid(self, handler):
        """Test switching to invalid model."""
        models = [MockModel("model1")]
        handler.available_models = models
        handler.current_model = "model1"

        result = handler.switch_model("nonexistent")

        assert result == CommandResult.HANDLED
        assert handler.current_model == "model1"  # Unchanged
        calls = [str(call) for call in handler.console.print.call_args_list]
        assert any("Model not found" in str(call) for call in calls)

    def test_show_provider_info_no_args(self, handler):
        """Test showing provider info without arguments."""
        handler.provider_name = "test_provider"

        result = handler.show_provider_info("")

        assert result == CommandResult.HANDLED
        calls = [str(call) for call in handler.console.print.call_args_list]
        assert any("Provider Management" in str(call) for call in calls)
        assert any("test_provider" in str(call) for call in calls)

    def test_show_provider_info_with_factory(self, handler):
        """Test showing provider info with factory."""
        handler.provider_name = "oci_genai"
        factory = Mock()
        factory.list_available.return_value = ["oci_genai", "ollama", "litellm"]
        handler.factory = factory

        result = handler.show_provider_info("")

        assert result == CommandResult.HANDLED
        calls = [str(call) for call in handler.console.print.call_args_list]
        assert any("oci_genai" in str(call) for call in calls)
        assert any("ollama" in str(call) for call in calls)
        assert any("litellm" in str(call) for call in calls)

    def test_show_provider_info_same_provider(self, handler):
        """Test provider info when trying to switch to same provider."""
        handler.provider_name = "oci_genai"

        result = handler.show_provider_info("oci_genai")

        assert result == CommandResult.HANDLED
        calls = [str(call) for call in handler.console.print.call_args_list]
        assert any("Already using oci_genai" in str(call) for call in calls)

    def test_show_provider_info_different_provider(self, handler):
        """Test provider info when trying to switch to different provider."""
        handler.provider_name = "oci_genai"

        result = handler.show_provider_info("ollama")

        assert result == CommandResult.HANDLED
        calls = [str(call) for call in handler.console.print.call_args_list]
        assert any("not supported in current mode" in str(call) for call in calls)

    def test_clear_conversation(self, handler):
        """Test clear conversation command."""
        result = handler.clear_conversation()
        assert result == CommandResult.CLEAR

    def test_exit_application(self, handler):
        """Test exit application command."""
        result = handler.exit_application()
        assert result == CommandResult.EXIT
