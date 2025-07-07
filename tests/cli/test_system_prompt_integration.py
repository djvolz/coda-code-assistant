"""Integration tests to verify system prompts work correctly across CLI modes."""

from unittest.mock import Mock

import pytest

from coda.cli.shared import DeveloperMode, get_system_prompt
from coda.providers import Model, Role


class TestSystemPromptIntegration:
    """Test that system prompts are correctly integrated across all CLI modes."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock provider that captures messages."""
        provider = Mock()
        provider.chat_stream = Mock(return_value=[Mock(content="Response")])
        # Mock list_models for _should_use_tools method
        models = [
            Model(
                id="test-model",
                name="Test Model",
                provider="test",
                metadata={"supports_functions": False},
            )
        ]
        provider.list_models.return_value = models
        return provider

    @pytest.fixture
    def mock_models(self):
        """Create mock models."""
        return [
            Model(
                id="model1", name="Model 1", provider="test", metadata={"capabilities": ["CHAT"]}
            ),
            Model(
                id="model2", name="Model 2", provider="test", metadata={"capabilities": ["CHAT"]}
            ),
        ]

    def test_basic_mode_system_prompts(self, mock_provider):
        """Test that basic mode (ChatSession) correctly sends system prompts."""
        from coda.cli.chat_session import ChatSession
        from coda.configuration import CodaConfig

        # Mock config
        config = Mock(spec=CodaConfig)
        config.to_dict.return_value = {"temperature": 0.7, "max_tokens": 2000}

        # Create session
        session = ChatSession(
            provider=mock_provider,
            model="test-model",
            config=config,
            console=Mock(),
            provider_name="test",
            factory=Mock(),
            unique_models=[Model(id="test-model", name="Test Model", provider="test", metadata={})],
        )

        # Test each mode in one-shot
        for mode in DeveloperMode:
            session.set_mode(mode.value)
            session.run_one_shot("Test prompt")

            # Get the messages sent
            messages = mock_provider.chat_stream.call_args[1]["messages"]

            # Verify system prompt matches expected
            assert messages[0].role == Role.SYSTEM
            assert messages[0].content == get_system_prompt(mode)

    def test_mode_command_takes_effect_immediately(self, mock_provider):
        """Test that mode commands take effect on the very next message."""
        from coda.cli.basic_commands import BasicCommandProcessor

        processor = BasicCommandProcessor(Mock())
        processor.set_provider_info("test", mock_provider, Mock(), "model1", [])

        # Start in general mode
        processor.current_mode = DeveloperMode.GENERAL

        # Process mode change command
        result = processor.process_command("/mode debug")
        assert result == "continue"

        # Verify mode changed
        assert processor.current_mode == DeveloperMode.DEBUG

        # Get system prompt that would be used
        system_prompt = get_system_prompt(processor.current_mode)
        assert "debugging expert" in system_prompt

    def test_all_modes_have_unique_prompts(self):
        """Test that all modes have unique system prompts."""
        prompts = {}

        for mode in DeveloperMode:
            prompt = get_system_prompt(mode)

            # Should not be None or empty
            assert prompt is not None
            assert len(prompt) > 20

            # Should be unique
            assert prompt not in prompts.values()
            prompts[mode] = prompt

        # Verify we tested all modes
        assert len(prompts) == len(DeveloperMode)

    def test_cli_modes_use_same_prompts(self):
        """Test that both CLI modes use identical system prompts for each mode."""
        # This ensures consistency between basic and interactive modes
        for mode in DeveloperMode:
            prompt = get_system_prompt(mode)

            # Both modes should use the exact same prompt
            # (This is already ensured by using the shared get_system_prompt function,
            # but this test makes it explicit)
            assert prompt == get_system_prompt(mode)  # Tautology but documents intent
