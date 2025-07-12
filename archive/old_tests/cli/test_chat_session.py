"""Tests for ChatSession to verify system prompts are applied correctly."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from rich.console import Console

from coda.cli.chat_session import ChatSession
from coda.cli.shared import DeveloperMode
from coda.configuration import CodaConfig
from coda.providers import Model, Role


class TestChatSession:
    """Test ChatSession system prompt handling."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock provider."""
        provider = Mock()
        provider.chat_stream = MagicMock()
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
    def mock_config(self):
        """Create a mock config."""
        config = Mock(spec=CodaConfig)
        config.to_dict.return_value = {"temperature": 0.7, "max_tokens": 2000}
        return config

    @pytest.fixture
    def mock_console(self):
        """Create a mock console."""
        return Mock(spec=Console)

    @pytest.fixture
    def chat_session(self, mock_provider, mock_config, mock_console):
        """Create a ChatSession instance."""
        models = [Model(id="test-model", name="Test Model", provider="test", metadata={})]
        return ChatSession(
            provider=mock_provider,
            model="test-model",
            config=mock_config,
            console=mock_console,
            provider_name="test",
            factory=Mock(),
            unique_models=models,
        )

    def test_one_shot_includes_system_prompt(self, chat_session, mock_provider):
        """Test that one-shot mode includes the system prompt."""
        # Set mode to code
        chat_session.set_mode("code")

        # Mock the provider to return a response
        mock_provider.chat_stream.return_value = [
            Mock(content="Hello"),
            Mock(content=" world"),
        ]

        # Run one-shot
        chat_session.run_one_shot("Write a function")

        # Verify the provider was called with messages including system prompt
        mock_provider.chat_stream.assert_called_once()
        messages = mock_provider.chat_stream.call_args[1]["messages"]

        # Should have system prompt as first message
        assert len(messages) == 2
        assert messages[0].role == Role.SYSTEM
        assert "coding assistant" in messages[0].content
        assert messages[1].role == Role.USER
        assert messages[1].content == "Write a function"

    def test_interactive_includes_system_prompt(self, chat_session, mock_provider):
        """Test that interactive mode includes the system prompt."""
        # Set mode to debug
        chat_session.set_mode("debug")

        # Mock the provider to return a response
        mock_provider.chat_stream.return_value = [Mock(content="Debug info")]

        # Mock user input
        with patch("rich.prompt.Prompt.ask", side_effect=["Help me debug", "/exit"]):
            chat_session.run_interactive()

        # Verify the provider was called with messages including system prompt
        mock_provider.chat_stream.assert_called_once()
        messages = mock_provider.chat_stream.call_args[1]["messages"]

        # Should have system prompt as first message
        assert messages[0].role == Role.SYSTEM
        assert "debugging expert" in messages[0].content
        assert messages[1].role == Role.USER
        assert messages[1].content == "Help me debug"

    def test_mode_switching_updates_system_prompt(self, chat_session, mock_provider):
        """Test that switching modes updates the system prompt in subsequent messages."""
        # Start in general mode
        chat_session.set_mode("general")

        # Mock responses
        mock_provider.chat_stream.return_value = [Mock(content="Response")]

        # Mock user inputs - ask question, switch mode, ask another question
        inputs = ["First question", "/mode review", "Review this code", "/exit"]

        with patch("rich.prompt.Prompt.ask", side_effect=inputs):
            chat_session.run_interactive()

        # Should have been called twice (once for each non-command input)
        assert mock_provider.chat_stream.call_count == 2

        # First call should have general mode system prompt
        first_call_messages = mock_provider.chat_stream.call_args_list[0][1]["messages"]
        assert "helpful AI assistant" in first_call_messages[0].content

        # Second call should have review mode system prompt
        second_call_messages = mock_provider.chat_stream.call_args_list[1][1]["messages"]
        assert "code reviewer" in second_call_messages[0].content

    def test_conversation_history_preserves_system_prompt(self, chat_session, mock_provider):
        """Test that conversation history maintains the current system prompt."""
        # Set mode to explain
        chat_session.set_mode("explain")

        # Mock responses
        mock_provider.chat_stream.return_value = [Mock(content="Explanation")]

        # Mock multiple interactions
        inputs = ["Explain X", "Explain Y", "/exit"]

        with patch("rich.prompt.Prompt.ask", side_effect=inputs):
            chat_session.run_interactive()

        # Should have been called twice
        assert mock_provider.chat_stream.call_count == 2

        # Second call should include conversation history AND system prompt
        second_call_messages = mock_provider.chat_stream.call_args_list[1][1]["messages"]

        # Should have: system prompt, first user msg, first assistant msg, second user msg
        assert len(second_call_messages) == 4
        assert second_call_messages[0].role == Role.SYSTEM
        assert "patient teacher" in second_call_messages[0].content
        assert second_call_messages[1].content == "Explain X"
        assert second_call_messages[2].role == Role.ASSISTANT
        assert second_call_messages[3].content == "Explain Y"

    def test_clear_command_resets_conversation_but_keeps_mode(self, chat_session, mock_provider):
        """Test that /clear resets conversation but maintains system prompt."""
        # Set mode to refactor
        chat_session.set_mode("refactor")

        # Mock responses
        mock_provider.chat_stream.return_value = [Mock(content="Refactored")]

        # Mock interactions with clear
        inputs = ["Refactor this", "/clear", "Refactor that", "/exit"]

        with patch("rich.prompt.Prompt.ask", side_effect=inputs):
            chat_session.run_interactive()

        # Both calls should have refactor system prompt
        first_call_messages = mock_provider.chat_stream.call_args_list[0][1]["messages"]
        second_call_messages = mock_provider.chat_stream.call_args_list[1][1]["messages"]

        assert "refactoring specialist" in first_call_messages[0].content
        assert "refactoring specialist" in second_call_messages[0].content

        # Second call should NOT have history from before clear
        assert len(second_call_messages) == 2  # Only system prompt + new message

    def test_model_switching_preserves_mode(self, chat_session, mock_provider):
        """Test that switching models preserves the current mode."""
        # Set mode to plan
        chat_session.set_mode("plan")

        # Mock responses
        mock_provider.chat_stream.return_value = [Mock(content="Architecture plan")]

        # Add another model to the session
        chat_session.cmd_processor.available_models = [
            Model(id="model1", name="Model 1", provider="test", metadata={}),
            Model(id="model2", name="Model 2", provider="test", metadata={}),
        ]

        # Mock interactions with model switch
        inputs = ["Design system", "/model model2", "Design another system", "/exit"]

        with patch("rich.prompt.Prompt.ask", side_effect=inputs):
            chat_session.run_interactive()

        # Both calls should have plan mode system prompt
        assert mock_provider.chat_stream.call_count == 2
        for call in mock_provider.chat_stream.call_args_list:
            messages = call[1]["messages"]
            assert "software architect" in messages[0].content

    def test_all_modes_have_system_prompts(self, chat_session, mock_provider):
        """Test that all developer modes have unique system prompts."""
        # Mock response
        mock_provider.chat_stream.return_value = [Mock(content="Response")]

        seen_prompts = set()

        for mode in DeveloperMode:
            chat_session.set_mode(mode.value)

            with patch("rich.prompt.Prompt.ask", side_effect=["Test", "/exit"]):
                chat_session.run_interactive()

            # Get the system prompt that was used
            messages = mock_provider.chat_stream.call_args[1]["messages"]
            system_prompt = messages[0].content

            # Verify it's unique and not empty
            assert system_prompt not in seen_prompts
            assert len(system_prompt) > 20  # Not just a placeholder
            seen_prompts.add(system_prompt)

            # Verify it contains mode-specific keywords
            if mode == DeveloperMode.CODE:
                assert "coding" in system_prompt.lower()
            elif mode == DeveloperMode.DEBUG:
                assert "debug" in system_prompt.lower()
            elif mode == DeveloperMode.EXPLAIN:
                assert "teach" in system_prompt.lower() or "explain" in system_prompt.lower()
            elif mode == DeveloperMode.REVIEW:
                assert "review" in system_prompt.lower()
            elif mode == DeveloperMode.REFACTOR:
                assert "refactor" in system_prompt.lower()
            elif mode == DeveloperMode.PLAN:
                assert "architect" in system_prompt.lower() or "design" in system_prompt.lower()
