"""Tests for basic mode slash commands."""

import pytest
from rich.console import Console

from coda.cli.basic_commands import BasicCommandProcessor
from coda.cli.shared import DeveloperMode


class MockModel:
    """Mock model for testing."""

    def __init__(self, id: str):
        self.id = id
        self.provider = "test"
        self.metadata = {}


@pytest.fixture
def console():
    """Create a test console."""
    return Console()


@pytest.fixture
def cmd_processor(console):
    """Create a command processor for testing."""
    return BasicCommandProcessor(console)


class TestBasicCommands:
    """Test basic command processing."""

    def test_init(self, cmd_processor):
        """Test command processor initialization."""
        assert cmd_processor.current_mode == DeveloperMode.GENERAL
        assert cmd_processor.current_model is None
        assert cmd_processor.available_models == []

    def test_process_non_command(self, cmd_processor):
        """Test that non-commands return None."""
        assert cmd_processor.process_command("hello") is None
        assert cmd_processor.process_command("") is None
        assert cmd_processor.process_command("  ") is None

    def test_help_command(self, cmd_processor):
        """Test help command and aliases."""
        assert cmd_processor.process_command("/help") == "continue"
        assert cmd_processor.process_command("/h") == "continue"
        assert cmd_processor.process_command("/?") == "continue"

    def test_exit_command(self, cmd_processor):
        """Test exit command and aliases."""
        assert cmd_processor.process_command("/exit") == "exit"
        assert cmd_processor.process_command("/quit") == "exit"
        assert cmd_processor.process_command("/q") == "exit"

    def test_clear_command(self, cmd_processor):
        """Test clear command."""
        assert cmd_processor.process_command("/clear") == "clear"
        assert cmd_processor.process_command("/cls") == "clear"

    def test_unknown_command(self, cmd_processor):
        """Test unknown command handling."""
        assert cmd_processor.process_command("/unknown") == "continue"
        assert cmd_processor.process_command("/foo bar") == "continue"

    def test_mode_command_no_args(self, cmd_processor):
        """Test mode command without arguments."""
        assert cmd_processor.process_command("/mode") == "continue"
        assert cmd_processor.current_mode == DeveloperMode.GENERAL

    def test_mode_command_valid(self, cmd_processor):
        """Test mode command with valid mode."""
        assert cmd_processor.process_command("/mode code") == "continue"
        assert cmd_processor.current_mode == DeveloperMode.CODE

        assert cmd_processor.process_command("/mode debug") == "continue"
        assert cmd_processor.current_mode == DeveloperMode.DEBUG

    def test_mode_command_invalid(self, cmd_processor):
        """Test mode command with invalid mode."""
        original_mode = cmd_processor.current_mode
        assert cmd_processor.process_command("/mode invalid") == "continue"
        assert cmd_processor.current_mode == original_mode

    def test_model_command_no_models(self, cmd_processor):
        """Test model command when no models available."""
        assert cmd_processor.process_command("/model") == "continue"
        assert cmd_processor.process_command("/m") == "continue"

    def test_model_command_with_models(self, cmd_processor):
        """Test model command with available models."""
        models = [MockModel("model1"), MockModel("model2"), MockModel("test-model-3")]
        cmd_processor.set_provider_info("test", None, None, "model1", models)

        # List models
        assert cmd_processor.process_command("/model") == "continue"

        # Switch to valid model
        assert cmd_processor.process_command("/model model2") == "continue"
        assert cmd_processor.current_model == "model2"

        # Partial match
        assert cmd_processor.process_command("/model test") == "continue"
        assert cmd_processor.current_model == "test-model-3"

        # Invalid model
        assert cmd_processor.process_command("/model nonexistent") == "continue"
        assert cmd_processor.current_model == "test-model-3"  # Unchanged

    def test_provider_command(self, cmd_processor):
        """Test provider command."""
        cmd_processor.set_provider_info("test_provider", None, None, None, [])

        # Show providers
        assert cmd_processor.process_command("/provider") == "continue"
        assert cmd_processor.process_command("/p") == "continue"

        # Try to switch (not supported in basic mode)
        assert cmd_processor.process_command("/provider other") == "continue"

    def test_get_system_prompt(self, cmd_processor):
        """Test system prompt generation for different modes."""
        from coda.cli.shared.modes import get_system_prompt

        for mode in DeveloperMode:
            cmd_processor.current_mode = mode
            prompt = get_system_prompt(mode)
            assert isinstance(prompt, str)
            assert len(prompt) > 0

    def test_mode_descriptions(self, cmd_processor):
        """Test that all modes have descriptions."""
        from coda.cli.shared import get_mode_description

        for mode in DeveloperMode:
            desc = get_mode_description(mode)
            assert isinstance(desc, str)
            assert len(desc) > 0
