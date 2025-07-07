"""Comprehensive tests for MockProvider conversation functionality."""

import pytest

from coda.providers import Message, MockProvider, Role


@pytest.mark.unit
class TestMockProviderConversations:
    """Test MockProvider's conversation handling and context awareness."""

    def test_single_turn_conversation(self):
        """Test basic single-turn conversations."""
        provider = MockProvider()

        # Test simple greeting
        messages = [Message(role=Role.USER, content="Hello")]
        response = provider.chat(messages, "mock-echo")
        assert "hello" in response.lower()
        assert len(response) > 5  # Should be more than just "hello"

        # Test question
        messages = [Message(role=Role.USER, content="What is 2+2?")]
        response = provider.chat(messages, "mock-echo")
        assert response  # Should get a response

    def test_multi_turn_conversation_basic(self):
        """Test basic multi-turn conversation flow."""
        provider = MockProvider()

        messages = []

        # First turn
        messages.append(Message(role=Role.USER, content="My name is Alice"))
        response1 = provider.chat(messages, "mock-echo")
        messages.append(Message(role=Role.ASSISTANT, content=response1))

        # Second turn - should remember name
        messages.append(Message(role=Role.USER, content="What's my name?"))
        response2 = provider.chat(messages, "mock-echo")

        assert "alice" in response2.lower(), "MockProvider should remember the name from context"

    def test_python_context_awareness(self):
        """Test MockProvider's Python-specific context awareness."""
        provider = MockProvider()

        messages = []

        # Ask about Python
        messages.append(Message(role=Role.USER, content="What is Python?"))
        response1 = provider.chat(messages, "mock-echo")
        messages.append(Message(role=Role.ASSISTANT, content=response1))

        assert "python" in response1.lower()
        assert any(word in response1.lower() for word in ["programming", "language", "code"])

        # Follow-up about decorators
        messages.append(Message(role=Role.USER, content="Tell me about decorators"))
        response2 = provider.chat(messages, "mock-echo")
        messages.append(Message(role=Role.ASSISTANT, content=response2))

        assert "decorator" in response2.lower()
        assert "python" in response2.lower(), "Should maintain Python context"

        # Ask for example
        messages.append(Message(role=Role.USER, content="Can you show me an example?"))
        response3 = provider.chat(messages, "mock-echo")

        assert (
            "@" in response3 or "decorator" in response3.lower()
        ), "Should provide decorator example"

    def test_conversation_context_switching(self):
        """Test switching between different conversation topics."""
        provider = MockProvider()

        messages = []

        # Start with Python topic
        messages.append(Message(role=Role.USER, content="Tell me about Python"))
        response1 = provider.chat(messages, "mock-echo")
        messages.append(Message(role=Role.ASSISTANT, content=response1))

        assert "python" in response1.lower()

        # Switch to JavaScript topic
        messages.append(Message(role=Role.USER, content="Now tell me about JavaScript"))
        response2 = provider.chat(messages, "mock-echo")
        messages.append(Message(role=Role.ASSISTANT, content=response2))

        # Should mention JavaScript
        assert "javascript" in response2.lower()

        # Ask about what we were discussing
        messages.append(Message(role=Role.USER, content="What were we discussing?"))
        response3 = provider.chat(messages, "mock-echo")

        # Should mention both topics
        assert "python" in response3.lower() and "javascript" in response3.lower()

    def test_system_message_handling(self):
        """Test handling of system messages in conversations."""
        provider = MockProvider()

        messages = [
            Message(role=Role.SYSTEM, content="You are a helpful Python tutor."),
            Message(role=Role.USER, content="Tell me about Python"),
        ]

        response = provider.chat(messages, "mock-echo")

        # Should respond about Python
        assert "python" in response.lower()

    def test_long_conversation_context(self):
        """Test maintaining context over longer conversations."""
        provider = MockProvider()

        messages = []

        # Build up conversation about Python topics
        topics = [
            "Tell me about Python",
            "What about Python decorators?",
            "And Python functions?",
            "What were we discussing?",
        ]

        for i, user_msg in enumerate(topics):
            messages.append(Message(role=Role.USER, content=user_msg))
            response = provider.chat(messages, "mock-echo")
            messages.append(Message(role=Role.ASSISTANT, content=response))

            if i < 3:  # First three should mention Python or decorators
                assert "python" in response.lower() or "decorator" in response.lower()
            else:  # Last one should mention what we were discussing
                assert "python" in response.lower()

    def test_conversation_memory_limits(self):
        """Test how MockProvider handles very long conversations."""
        provider = MockProvider()

        messages = []

        # Add many messages
        for i in range(10):
            messages.append(Message(role=Role.USER, content=f"Message {i}"))
            response = provider.chat(messages, "mock-echo")
            messages.append(Message(role=Role.ASSISTANT, content=response))

        # Should still respond with echo pattern
        messages.append(Message(role=Role.USER, content="Final message"))
        final_response = provider.chat(messages, "mock-echo")

        assert "final message" in final_response.lower()  # Should echo the message
        assert len(final_response) > 10  # Should be a meaningful response

    def test_question_answering_patterns(self):
        """Test different question-answering patterns."""
        provider = MockProvider()

        # Test questions the MockProvider specifically handles
        qa_pairs = [
            ("What is Python?", "python"),
            ("Tell me about decorators", "decorator"),
            ("What is JavaScript?", "javascript"),
        ]

        for question, expected_keyword in qa_pairs:
            messages = [Message(role=Role.USER, content=question)]
            response = provider.chat(messages, "mock-echo")

            # Should mention the expected keyword
            assert (
                expected_keyword in response.lower()
            ), f"Response to '{question}' should mention '{expected_keyword}'"

    def test_code_generation_requests(self):
        """Test handling of code generation requests."""
        provider = MockProvider()

        # Test decorator example request
        messages = [Message(role=Role.USER, content="Show me a decorator example")]
        response = provider.chat(messages, "mock-echo")

        # Should mention decorators or @ symbol
        assert "decorator" in response.lower() or "@" in response

    def test_conversation_branching_scenarios(self):
        """Test different conversation branches from same starting point."""
        provider = MockProvider()

        # Base conversation about Python
        base_messages = [
            Message(role=Role.USER, content="Tell me about Python"),
            Message(role=Role.ASSISTANT, content="Python is a high-level programming language..."),
        ]

        # Branch 1: Ask about decorators
        branch1 = base_messages.copy()
        branch1.append(Message(role=Role.USER, content="Tell me about decorators"))
        response1 = provider.chat(branch1, "mock-echo")
        assert "decorator" in response1.lower()

        # Branch 2: Ask about JavaScript
        branch2 = base_messages.copy()
        branch2.append(Message(role=Role.USER, content="Tell me about JavaScript"))
        response2 = provider.chat(branch2, "mock-echo")
        assert "javascript" in response2.lower()

        # Responses should be different
        assert response1 != response2, "Different branches should yield different responses"
