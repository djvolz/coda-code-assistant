"""Tests for context management functionality."""

import pytest

from coda.session.context import ContextManager


class TestContextManager:
    """Test context management and windowing."""

    @pytest.fixture
    def context_manager(self):
        """Create a context manager instance."""
        return ContextManager()

    def test_token_counting(self, context_manager):
        """Test token counting functionality."""
        # Test basic counting
        text = "Hello world"
        tokens = context_manager.count_tokens(text)
        assert tokens > 0
        assert tokens < 10  # Should be around 2-3 tokens

        # Test longer text
        long_text = "The quick brown fox jumps over the lazy dog " * 10
        long_tokens = context_manager.count_tokens(long_text)
        assert long_tokens > tokens

    def test_message_token_counting(self, context_manager):
        """Test counting tokens in messages."""
        message = {"role": "user", "content": "What is Python?"}

        tokens = context_manager.count_message_tokens(message)
        assert tokens > 4  # Should include overhead + content

    def test_model_context_limits(self, context_manager):
        """Test retrieving model context limits."""
        # Test known models
        assert context_manager.get_model_context_limit("gpt-4") == 8192
        assert context_manager.get_model_context_limit("gpt-4-32k") == 32768
        assert context_manager.get_model_context_limit("cohere.command-r-plus") == 128000
        assert context_manager.get_model_context_limit("meta.llama-3.1-405b") == 128000

        # Test partial matching
        assert context_manager.get_model_context_limit("gpt-4-turbo-preview") == 128000

        # Test unknown model
        assert context_manager.get_model_context_limit("unknown-model") == 4096

    def test_context_optimization(self, context_manager):
        """Test context optimization with token limits."""
        # Create messages
        messages = []
        for i in range(20):
            messages.append(
                {
                    "role": "user" if i % 2 == 0 else "assistant",
                    "content": f"Message {i}: " + "x" * 200,  # Increased from 100 to 200
                }
            )

        # Add system message
        messages.insert(0, {"role": "system", "content": "You are a helpful assistant."})

        # Optimize with tight limit
        optimized, was_truncated = context_manager.optimize_context(
            messages, model="gpt-3.5-turbo", target_tokens=500, preserve_last_n=5
        )

        assert was_truncated
        assert len(optimized) < len(messages)

        # System message should be preserved
        assert any(msg["role"] == "system" for msg in optimized)

        # Recent messages should be preserved
        last_contents = [msg["content"] for msg in messages[-5:] if msg["role"] != "system"]
        optimized_contents = [msg["content"] for msg in optimized]
        for content in last_contents:
            assert content in optimized_contents

    def test_no_truncation_needed(self, context_manager):
        """Test when messages fit within limit."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        optimized, was_truncated = context_manager.optimize_context(
            messages, model="gpt-4", target_tokens=1000
        )

        assert not was_truncated
        assert len(optimized) == len(messages)
        assert optimized == messages

    def test_summary_message_creation(self, context_manager):
        """Test creating summary messages."""
        messages = [
            {"role": "user", "content": "Tell me about functions in Python"},
            {"role": "assistant", "content": "Functions are reusable blocks of code..."},
            {"role": "user", "content": "What about classes?"},
            {"role": "assistant", "content": "Classes are blueprints for objects..."},
            {"role": "user", "content": "How do I handle errors?"},
            {"role": "assistant", "content": "Use try-except blocks for error handling..."},
        ]

        summary = context_manager.create_summary_message(messages)

        assert summary["role"] == "system"
        assert "Previous conversation summary" in summary["content"]
        assert "6 messages" in summary["content"]
        assert "3 user, 3 assistant" in summary["content"]

    def test_key_topic_extraction(self, context_manager):
        """Test extracting key topics from messages."""
        messages = [
            {"role": "user", "content": "How do I create a function in Python?"},
            {"role": "assistant", "content": "To create a function, use the def keyword..."},
            {"role": "user", "content": "What about error handling with functions?"},
            {
                "role": "assistant",
                "content": "You can handle errors in functions using try-except...",
            },
            {"role": "user", "content": "Can functions access database connections?"},
            {
                "role": "assistant",
                "content": "Yes, functions can work with database connections...",
            },
        ]

        topics = context_manager._extract_key_topics(messages)

        assert "function" in topics
        assert "error" in topics
        assert "database" in topics
        assert len(topics) <= 5

    def test_context_window_modes(self, context_manager):
        """Test different context window modes."""
        # Test aggressive mode
        aggressive = context_manager.get_context_window("gpt-4", mode="aggressive")
        assert aggressive.max_tokens == int(8192 * 0.9)
        assert aggressive.max_messages == 100
        assert aggressive.preserve_system

        # Test balanced mode
        balanced = context_manager.get_context_window("gpt-4", mode="balanced")
        assert balanced.max_tokens == int(8192 * 0.75)
        assert balanced.max_messages == 50

        # Test conservative mode
        conservative = context_manager.get_context_window("gpt-4", mode="conservative")
        assert conservative.max_tokens == int(8192 * 0.6)
        assert conservative.max_messages == 30

    def test_empty_messages(self, context_manager):
        """Test handling empty message lists."""
        optimized, was_truncated = context_manager.optimize_context(
            [], model="gpt-4", target_tokens=1000
        )

        assert optimized == []
        assert not was_truncated

    def test_system_message_preservation(self, context_manager):
        """Test that system messages are always preserved."""
        messages = [
            {"role": "system", "content": "Important system prompt"},
            {"role": "user", "content": "x" * 1000},
            {"role": "assistant", "content": "y" * 1000},
            {"role": "system", "content": "Another system message"},
            {"role": "user", "content": "z" * 1000},
        ]

        # Optimize with very tight limit
        optimized, was_truncated = context_manager.optimize_context(
            messages, model="gpt-3.5-turbo", target_tokens=200, preserve_last_n=1
        )

        assert was_truncated

        # All system messages should be preserved
        system_messages = [msg for msg in optimized if msg["role"] == "system"]
        assert len(system_messages) == 2
        assert system_messages[0]["content"] == "Important system prompt"
        assert system_messages[1]["content"] == "Another system message"
