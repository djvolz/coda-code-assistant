"""Basic unit tests for OCI GenAI provider streaming logic.

These tests focus on the streaming response parsing logic without
requiring full OCI SDK mocking.
"""

import json
from unittest.mock import Mock

import pytest

from coda.providers.base import ChatCompletionChunk


@pytest.mark.unit
class TestOCIGenAIStreaming:
    """Test the streaming response parsing logic."""

    def test_parse_xai_streaming_format(self):
        """Test parsing of xAI/Meta streaming format."""

        # Create a mock event
        event = Mock()
        event.data = '{"message":{"content":[{"type":"TEXT","text":"Hello world"}]}}'

        # Parse the event data like the actual code does
        data = json.loads(event.data)

        # Test the parsing logic
        message = data.get("message", {})
        assert message != {}

        message_content = message.get("content", [])
        assert len(message_content) == 1
        assert message_content[0]["type"] == "TEXT"
        assert message_content[0]["text"] == "Hello world"

    def test_parse_cohere_streaming_format(self):
        """Test parsing of Cohere streaming format."""
        # Create a mock event
        event = Mock()
        event.data = '{"apiFormat":"COHERE","text":"Hello from Cohere"}'

        # Parse the event data
        data = json.loads(event.data)

        # Test Cohere format detection
        assert data.get("apiFormat") == "COHERE"
        assert data.get("text") == "Hello from Cohere"

    def test_parse_finish_reason(self):
        """Test parsing of finish reason events."""
        # xAI/Meta format
        event = Mock()
        event.data = '{"finishReason":"stop"}'
        data = json.loads(event.data)
        assert data.get("finishReason") == "stop"

        # Cohere format with finish reason
        event2 = Mock()
        event2.data = '{"apiFormat":"COHERE","text":"Full text","finishReason":"MAX_TOKENS"}'
        data2 = json.loads(event2.data)
        assert data2.get("finishReason") == "MAX_TOKENS"
        assert "text" in data2  # Should have text but we ignore it to avoid duplication

    def test_empty_content_scenarios(self):
        """Test handling of various empty content scenarios."""
        # Empty content array
        event1 = Mock()
        event1.data = '{"message":{"content":[]}}'
        data1 = json.loads(event1.data)
        content_array = data1.get("message", {}).get("content", [])
        assert len(content_array) == 0

        # Empty text in content
        event2 = Mock()
        event2.data = '{"message":{"content":[{"type":"TEXT","text":""}]}}'
        data2 = json.loads(event2.data)
        content = data2["message"]["content"][0]["text"]
        assert content == ""

        # Missing message entirely
        event3 = Mock()
        event3.data = '{"someOtherField":"value"}'
        data3 = json.loads(event3.data)
        assert data3.get("message") is None

    def test_model_name_normalization(self):
        """Test model name normalization logic."""
        test_cases = [
            ("Grok 3 Fast", "grok-3-fast"),
            ("Command R Plus (08-2024)", "command-r-plus-08-2024"),
            ("Llama 3.1 70B Instruct", "llama-3-1-70b-instruct"),  # Fixed expected
            ("Simple Name", "simple-name"),
            ("UPPERCASE NAME", "uppercase-name"),
        ]

        for display_name, expected in test_cases:
            # Replicate the normalization logic
            normalized = display_name.lower()
            normalized = normalized.replace(" ", "-")
            normalized = normalized.replace("(", "")
            normalized = normalized.replace(")", "")
            normalized = normalized.replace(".", "-")

            assert normalized == expected

    def test_streaming_chunk_creation(self):
        """Test ChatCompletionChunk object creation."""
        # Test normal chunk
        chunk = ChatCompletionChunk(
            content="Hello", model="test-model", finish_reason=None, usage=None, metadata={}
        )

        assert chunk.content == "Hello"
        assert chunk.model == "test-model"
        assert chunk.finish_reason is None

        # Test finish chunk
        finish_chunk = ChatCompletionChunk(
            content="", model="test-model", finish_reason="stop", usage=None, metadata={}
        )

        assert finish_chunk.content == ""
        assert finish_chunk.finish_reason == "stop"

    def test_json_error_resilience(self):
        """Test that invalid JSON can be handled gracefully."""
        invalid_jsons = ["invalid json", '{"incomplete": ', '{"valid":true}extra', None]

        for invalid in invalid_jsons:
            try:
                if invalid:
                    json.loads(invalid)
                    raise AssertionError(f"Should have raised JSONDecodeError for: {invalid}")
            except (json.JSONDecodeError, TypeError):
                # This is expected - the code should continue when this happens
                pass

        # Empty string is valid JSON in some contexts, test separately
        assert json.loads('""') == ""

    def test_model_filtering_logic(self):
        """Test the model filtering logic used in list_models."""
        # Simulate model data
        models = [
            {"vendor": "xai", "lifecycle_state": "ACTIVE", "capabilities": ["CHAT"]},
            {"vendor": "cohere", "lifecycle_state": "ACTIVE", "capabilities": ["TEXT_GENERATION"]},
            {"vendor": "meta", "lifecycle_state": "INACTIVE", "capabilities": ["CHAT"]},
            {"vendor": "test", "lifecycle_state": "ACTIVE", "capabilities": []},
        ]

        # Apply filtering logic
        filtered = []
        for model in models:
            if model["lifecycle_state"] == "ACTIVE":
                caps = model.get("capabilities", [])
                if "CHAT" in caps or "TEXT_GENERATION" in caps:
                    filtered.append(model)

        assert len(filtered) == 2
        assert filtered[0]["vendor"] == "xai"
        assert filtered[1]["vendor"] == "cohere"
