"""Tests for MockProvider with different modes and models."""

import pytest

from coda.base.providers import Message, MockProvider, Role


@pytest.mark.unit
class TestMockProviderModes:
    """Test MockProvider behavior across all developer modes."""

    # All available developer modes
    DEVELOPER_MODES = ["general", "code", "debug", "explain", "review", "refactor", "plan"]

    def test_all_modes_with_system_prompts(self):
        """Test that MockProvider works with all modes' system prompts."""
        provider = MockProvider()

        for mode in self.DEVELOPER_MODES:
            # Each mode would have its own system prompt in real usage
            system_prompt = f"You are in {mode} mode"
            messages = [
                Message(role=Role.SYSTEM, content=system_prompt),
                Message(role=Role.USER, content="Tell me about Python"),
            ]

            response = provider.chat(messages, "mock-echo")

            # MockProvider should respond about Python regardless of mode
            assert "python" in response.content.lower(), f"Failed for mode: {mode}"
            assert len(response.content) > 10, f"Response too short for mode: {mode}"

    def test_mode_switching_scenarios(self):
        """Test conversation behavior when switching between modes."""
        provider = MockProvider()

        # Start in code mode
        messages = [
            Message(role=Role.SYSTEM, content="You are in code mode"),
            Message(role=Role.USER, content="Write a Python function"),
        ]
        response1 = provider.chat(messages, "mock-echo")

        # Switch to debug mode (simulated by changing system prompt)
        messages[0] = Message(role=Role.SYSTEM, content="You are in debug mode")
        messages.append(Message(role=Role.ASSISTANT, content=response1.content))
        messages.append(Message(role=Role.USER, content="Debug this Python code"))
        response2 = provider.chat(messages, "mock-echo")

        # Both should mention Python
        assert "python" in response1.content.lower()
        assert "python" in response2.content.lower()

    def test_mode_specific_questions(self):
        """Test mode-appropriate questions across all modes."""
        provider = MockProvider()

        mode_questions = {
            "general": "How are you today?",
            "code": "Write a Python decorator",
            "debug": "Why is my Python code failing?",
            "explain": "Explain Python decorators",
            "review": "Review this Python code for security",
            "refactor": "Refactor this Python function",
            "plan": "Plan a Python web application",
        }

        for mode, question in mode_questions.items():
            messages = [
                Message(role=Role.SYSTEM, content=f"You are in {mode} mode"),
                Message(role=Role.USER, content=question),
            ]

            response = provider.chat(messages, "mock-echo")

            # Should get a response for each mode
            assert response, f"No response for mode: {mode}"
            assert len(response.content) > 5, f"Response too short for mode: {mode}"

            # Python-related questions should trigger Python responses
            if "python" in question.lower():
                assert (
                    "python" in response.content.lower() or "decorator" in response.content.lower()
                ), f"Python not mentioned for mode: {mode}"

    def test_conversation_continuity_across_modes(self):
        """Test that conversation context is maintained when mode changes."""
        provider = MockProvider()

        messages = []

        # Start conversation in general mode about Python
        messages.append(Message(role=Role.SYSTEM, content="You are in general mode"))
        messages.append(Message(role=Role.USER, content="I'm learning Python"))
        response1 = provider.chat(messages, "mock-echo")
        messages.append(Message(role=Role.ASSISTANT, content=response1.content))

        # Continue in code mode
        messages[0] = Message(role=Role.SYSTEM, content="You are in code mode")
        messages.append(Message(role=Role.USER, content="Show me a decorator example"))
        response2 = provider.chat(messages, "mock-echo")
        messages.append(Message(role=Role.ASSISTANT, content=response2.content))

        # Switch to explain mode and ask about previous topic
        messages[0] = Message(role=Role.SYSTEM, content="You are in explain mode")
        messages.append(Message(role=Role.USER, content="What were we discussing?"))
        response3 = provider.chat(messages, "mock-echo")

        # Should remember Python and decorators were discussed
        assert "python" in response3.content.lower(), "Should remember Python discussion"
        assert "decorator" in response3.content.lower(), "Should remember decorator discussion"

    def test_edge_cases_with_modes(self):
        """Test edge cases with different modes."""
        provider = MockProvider()

        # Empty user message in different modes
        for mode in self.DEVELOPER_MODES:
            messages = [
                Message(role=Role.SYSTEM, content=f"You are in {mode} mode"),
                Message(role=Role.USER, content=""),
            ]

            response = provider.chat(messages, "mock-echo")
            assert response  # Should handle empty messages gracefully

        # Very long system prompts
        long_prompt = "You are in code mode. " * 100
        messages = [
            Message(role=Role.SYSTEM, content=long_prompt),
            Message(role=Role.USER, content="Hello"),
        ]

        response = provider.chat(messages, "mock-echo")
        assert "hello" in response.content.lower()


@pytest.mark.unit
class TestMockProviderModels:
    """Test both mock-echo and mock-smart models."""

    def test_both_models_basic_functionality(self):
        """Test that both models work for basic conversations."""
        provider = MockProvider()

        models = ["mock-echo", "mock-smart"]

        for model in models:
            messages = [Message(role=Role.USER, content="Hello")]
            response = provider.chat(messages, model)

            assert "hello" in response.content.lower(), f"Failed for model: {model}"
            assert len(response.content) > 5, f"Response too short for model: {model}"

    def test_both_models_python_awareness(self):
        """Test that both models handle Python topics."""
        provider = MockProvider()

        models = ["mock-echo", "mock-smart"]

        for model in models:
            messages = [
                Message(role=Role.USER, content="What is Python?"),
                Message(role=Role.ASSISTANT, content="Python is a programming language..."),
                Message(role=Role.USER, content="Tell me about decorators"),
            ]

            response = provider.chat(messages, model)

            assert "decorator" in response.content.lower(), f"Failed for model: {model}"
            assert "python" in response.content.lower(), f"Failed for model: {model}"

    def test_both_models_conversation_memory(self):
        """Test that both models maintain conversation context."""
        provider = MockProvider()

        models = ["mock-echo", "mock-smart"]

        for model in models:
            messages = [
                Message(role=Role.USER, content="My name is Alice"),
                Message(role=Role.ASSISTANT, content="Nice to meet you, Alice!"),
                Message(role=Role.USER, content="What's my name?"),
            ]

            response = provider.chat(messages, model)

            assert "alice" in response.content.lower(), (
                f"Failed to remember name for model: {model}"
            )

    def test_model_metadata_differences(self):
        """Test that models have different metadata but same behavior."""
        provider = MockProvider()

        # Get model info
        echo_info = provider.get_model_info("mock-echo")
        smart_info = provider.get_model_info("mock-smart")

        # Check metadata differences
        assert echo_info["context_window"] == 4096
        assert smart_info["context_window"] == 8192
        assert echo_info["name"] == "Mock Echo Model"
        assert smart_info["name"] == "Mock Smart Model"

        # But behavior should be identical
        messages = [Message(role=Role.USER, content="Tell me about Python")]

        echo_response = provider.chat(messages, "mock-echo")
        smart_response = provider.chat(messages, "mock-smart")

        # Both should mention Python
        assert "python" in echo_response.content.lower()
        assert "python" in smart_response.content.lower()

    def test_streaming_both_models(self):
        """Test streaming functionality for both models."""
        provider = MockProvider()

        models = ["mock-echo", "mock-smart"]

        for model in models:
            messages = [Message(role=Role.USER, content="Hello world")]

            # Collect streamed chunks
            chunks = []
            for chunk in provider.chat_stream(messages, model):
                chunks.append(chunk.content)

            # Reconstruct full response
            full_response = "".join(chunks)

            assert "hello" in full_response.lower(), f"Streaming failed for model: {model}"
            assert len(chunks) > 1, f"Should stream multiple chunks for model: {model}"

    def test_error_handling_both_models(self):
        """Test error handling for both models."""
        provider = MockProvider()

        # MockProvider accepts any model name without validation
        response = provider.chat([Message(role=Role.USER, content="Test")], "invalid-model")
        assert response  # Should still work

        # Test model info for invalid model
        with pytest.raises(ValueError):
            provider.get_model_info("invalid-model")

        # Both valid models should work
        for model in ["mock-echo", "mock-smart"]:
            response = provider.chat([Message(role=Role.USER, content="Test")], model)
            assert response  # Should not raise error


@pytest.mark.unit
class TestMockProviderModesAndModels:
    """Test combinations of modes and models."""

    def test_all_mode_model_combinations(self):
        """Test all combinations of modes and models."""
        provider = MockProvider()

        modes = ["general", "code", "debug", "explain", "review", "refactor", "plan"]
        models = ["mock-echo", "mock-smart"]

        for mode in modes:
            for model in models:
                messages = [
                    Message(role=Role.SYSTEM, content=f"You are in {mode} mode"),
                    Message(role=Role.USER, content="Tell me about Python"),
                ]

                response = provider.chat(messages, model)

                assert response, f"No response for mode={mode}, model={model}"
                assert "python" in response.content.lower(), (
                    f"Python not mentioned for mode={mode}, model={model}"
                )

    def test_mode_model_conversation_flow(self):
        """Test a complete conversation flow with mode and model changes."""
        provider = MockProvider()

        messages = []

        # Start with general mode and echo model
        messages.append(Message(role=Role.SYSTEM, content="You are in general mode"))
        messages.append(Message(role=Role.USER, content="I want to learn programming"))
        response1 = provider.chat(messages, "mock-echo")
        messages.append(Message(role=Role.ASSISTANT, content=response1.content))

        # Switch to code mode with smart model
        messages[0] = Message(role=Role.SYSTEM, content="You are in code mode")
        messages.append(Message(role=Role.USER, content="Show me Python basics"))
        response2 = provider.chat(messages, "mock-smart")
        messages.append(Message(role=Role.ASSISTANT, content=response2.content))

        # Switch to debug mode with echo model
        messages[0] = Message(role=Role.SYSTEM, content="You are in debug mode")
        messages.append(Message(role=Role.USER, content="What were we discussing?"))
        response3 = provider.chat(messages, "mock-echo")

        # Should maintain context regardless of mode/model switches
        assert any(word in response3.content.lower() for word in ["python", "programming"])

    def test_async_methods_with_modes_and_models(self):
        """Test async methods work with all modes and models."""
        import asyncio

        async def test_async():
            provider = MockProvider()

            # Test a few combinations
            combinations = [
                ("general", "mock-echo"),
                ("code", "mock-smart"),
                ("debug", "mock-echo"),
            ]

            for mode, model in combinations:
                messages = [
                    Message(role=Role.SYSTEM, content=f"You are in {mode} mode"),
                    Message(role=Role.USER, content="Test async"),
                ]

                # Test async chat
                response = await provider.achat(messages, model)
                assert response, f"Async chat failed for mode={mode}, model={model}"

                # Test async streaming
                chunks = []
                async for chunk in provider.achat_stream(messages, model):
                    chunks.append(chunk.content)

                assert len(chunks) > 0, f"Async streaming failed for mode={mode}, model={model}"

        # Run async test
        asyncio.run(test_async())
