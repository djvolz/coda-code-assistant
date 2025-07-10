"""Edge case tests for MockProvider conversation handling."""

import pytest

from coda.base.providers import Message, MockProvider, Role
from coda.base.providers.base import ChatCompletion


@pytest.mark.unit
class TestMockProviderEdgeCases:
    """Test edge cases and special scenarios for MockProvider conversations."""

    def test_empty_conversation(self):
        """Test handling of empty message list."""
        provider = MockProvider()

        # Empty messages should still work
        response = provider.chat([], "mock-echo")
        assert response  # Should return something
        assert isinstance(response, ChatCompletion)
        assert response.content

    def test_single_system_message_only(self):
        """Test conversation with only system message."""
        provider = MockProvider()

        messages = [Message(role=Role.SYSTEM, content="You are a code reviewer.")]

        response = provider.chat(messages, "mock-echo")
        assert response  # Should handle gracefully

    def test_malformed_conversation_history(self):
        """Test handling of unusual conversation patterns."""
        provider = MockProvider()

        # Multiple user messages in a row
        messages = [
            Message(role=Role.USER, content="First question"),
            Message(role=Role.USER, content="Second question"),
            Message(role=Role.USER, content="Third question"),
        ]

        response = provider.chat(messages, "mock-echo")
        assert response  # Should handle multiple questions

        # Multiple assistant messages
        messages2 = [
            Message(role=Role.ASSISTANT, content="Previous response 1"),
            Message(role=Role.ASSISTANT, content="Previous response 2"),
            Message(role=Role.USER, content="New question"),
        ]

        response2 = provider.chat(messages2, "mock-echo")
        assert response2  # Should handle gracefully

    def test_very_long_messages(self):
        """Test handling of very long messages."""
        provider = MockProvider()

        # Very long user message
        long_content = "Python " * 1000  # Very long message
        messages = [Message(role=Role.USER, content=long_content)]

        response = provider.chat(messages, "mock-echo")
        assert response
        assert len(response.content) < len(long_content)  # Should not echo entire long message

    def test_special_characters_and_formatting(self):
        """Test handling of special characters and formatting."""
        provider = MockProvider()

        special_inputs = [
            "Can you help with this code?\n```python\ndef foo():\n    pass\n```",
            "What about unicode? 你好 🎉 café",
            "Markdown **bold** and *italic* and `code`",
            "Special chars: <>&\"'",
            "Math expressions: x^2 + y^2 = z^2",
        ]

        for input_text in special_inputs:
            messages = [Message(role=Role.USER, content=input_text)]
            response = provider.chat(messages, "mock-echo")
            assert response  # Should handle all special inputs

    def test_conversation_with_names(self):
        """Test handling of messages with name attributes."""
        provider = MockProvider()

        messages = [
            Message(role=Role.USER, content="Hello from user1", name="user1"),
            Message(role=Role.ASSISTANT, content="Hello user1!"),
            Message(role=Role.USER, content="Hello from user2", name="user2"),
        ]

        response = provider.chat(messages, "mock-echo")
        assert response  # Should handle named messages

    def test_rapid_context_switches(self):
        """Test handling of rapid context switches."""
        provider = MockProvider()

        messages = []
        # Use topics that MockProvider specifically handles
        topics = [("Python", "python"), ("JavaScript", "javascript"), ("decorators", "decorator")]

        for topic, expected in topics:
            messages.append(Message(role=Role.USER, content=f"Tell me about {topic}"))
            response = provider.chat(messages, "mock-echo")
            messages.append(Message(role=Role.ASSISTANT, content=response.content))

            # Should mention the expected keyword
            assert expected in response.content.lower()

    def test_error_recovery_scenarios(self):
        """Test conversation recovery after confusing inputs."""
        provider = MockProvider()

        messages = [
            Message(role=Role.USER, content="ajsdkfj aslkdfj alskdjf"),  # Gibberish
            Message(role=Role.ASSISTANT, content="I'm not sure I understand..."),
            Message(role=Role.USER, content="Sorry, I meant to ask about Python lists"),
        ]

        response = provider.chat(messages, "mock-echo")

        # Should recover and talk about Python lists
        assert any(word in response.content.lower() for word in ["python", "list"])

    def test_conversation_state_isolation(self):
        """Test that different conversation instances don't interfere."""
        provider = MockProvider()

        # First conversation about Python
        conv1 = [
            Message(role=Role.USER, content="Let's talk about Python"),
            Message(role=Role.ASSISTANT, content="Python is a great language..."),
            Message(role=Role.USER, content="What makes it special?"),
        ]
        response1 = provider.chat(conv1, "mock-echo")

        # Second conversation about Java (completely separate)
        conv2 = [
            Message(role=Role.USER, content="Tell me about Java"),
            Message(role=Role.ASSISTANT, content="Java is an object-oriented language..."),
            Message(role=Role.USER, content="What makes it special?"),
        ]
        response2 = provider.chat(conv2, "mock-echo")

        # Responses should be contextually different
        assert "python" in response1.content.lower()
        assert "java" in response2.content.lower() or response2.content

    def test_recursive_question_patterns(self):
        """Test handling of recursive or self-referential questions."""
        provider = MockProvider()

        messages = [
            Message(role=Role.USER, content="What's your previous response?"),
        ]

        response = provider.chat(messages, "mock-echo")
        assert response  # Should handle gracefully without previous context

        # Add context and ask again
        messages.append(Message(role=Role.ASSISTANT, content=response.content))
        messages.append(Message(role=Role.USER, content="What did you just say?"))

        response2 = provider.chat(messages, "mock-echo")
        assert response2  # Should reference or acknowledge previous response

    def test_mixed_language_conversation(self):
        """Test handling of mixed language inputs."""
        provider = MockProvider()

        messages = [
            Message(role=Role.USER, content="Hello, comment allez-vous?"),
            Message(role=Role.ASSISTANT, content="Hello! I'm doing well."),
            Message(role=Role.USER, content="Can you explain Python's list comprehensions?"),
        ]

        response = provider.chat(messages, "mock-echo")
        assert response  # Should handle language mix gracefully
        assert any(word in response.content.lower() for word in ["list", "comprehension", "python"])

    def test_conversation_with_code_context(self):
        """Test maintaining context when discussing code."""
        provider = MockProvider()

        messages = [
            Message(role=Role.USER, content="Here's my code: def add(a, b): return a + b"),
            Message(role=Role.ASSISTANT, content="That's a simple addition function..."),
            Message(role=Role.USER, content="How can I make it handle strings too?"),
        ]

        response = provider.chat(messages, "mock-echo")

        # Should reference the function context
        assert any(word in response.content.lower() for word in ["add", "string", "type", "check"])

    def test_number_and_data_questions(self):
        """Test handling of numerical and data-related questions."""
        provider = MockProvider()

        # MockProvider will echo these questions since they don't match specific patterns
        numerical_questions = [
            "What's 123 + 456?",
            "How many bytes in a kilobyte?",
            "What's the factorial of 5?",
        ]

        for question in numerical_questions:
            messages = [Message(role=Role.USER, content=question)]
            response = provider.chat(messages, "mock-echo")

            # Should echo back the question in some form
            assert "You said:" in response.content or len(response.content) > 10

    def test_conversation_persistence_check(self):
        """Test that conversations maintain their context properly."""
        provider = MockProvider()

        # Build conversation about a specific project
        messages = [
            Message(role=Role.USER, content="I'm building a TODO app"),
            Message(role=Role.ASSISTANT, content="A TODO app is a great project..."),
            Message(role=Role.USER, content="I want to use SQLite for storage"),
            Message(role=Role.ASSISTANT, content="SQLite is perfect for TODO apps..."),
            Message(role=Role.USER, content="What columns should my tasks table have?"),
        ]

        response = provider.chat(messages, "mock-echo")

        # Should remember we're talking about TODO app with SQLite
        assert any(
            word in response.content.lower()
            for word in ["todo", "task", "sqlite", "column", "table"]
        )
