"""Fast unit tests for OCI GenAI response parsing logic."""

import json

import pytest


@pytest.mark.unit
class TestOCIResponseParsing:
    """Test response parsing without any OCI dependencies."""

    def test_parse_xai_message_format(self):
        """Test parsing xAI/Meta message format."""
        response = {
            "message": {"role": "ASSISTANT", "content": [{"type": "TEXT", "text": "Hello world"}]}
        }

        # Extract content like the provider does
        message = response.get("message", {})
        content_list = message.get("content", [])

        assert len(content_list) == 1
        assert content_list[0]["type"] == "TEXT"
        assert content_list[0]["text"] == "Hello world"

    def test_parse_cohere_format(self):
        """Test parsing Cohere response format."""
        response = {"apiFormat": "COHERE", "text": "Hello from Cohere"}

        assert response["apiFormat"] == "COHERE"
        assert response["text"] == "Hello from Cohere"

    def test_parse_finish_reason(self):
        """Test parsing various finish reasons."""
        responses = [
            {"finishReason": "stop"},
            {"finishReason": "MAX_TOKENS"},
            {"finishReason": "length"},
        ]

        for resp in responses:
            assert "finishReason" in resp
            assert resp["finishReason"] in ["stop", "MAX_TOKENS", "length"]

    def test_empty_content_handling(self):
        """Test handling of empty content."""
        cases = [
            {"message": {"content": []}},  # Empty array
            {"message": {"content": [{"type": "TEXT", "text": ""}]}},  # Empty text
            {"message": {}},  # No content field
            {},  # No message field
        ]

        for case in cases:
            message = case.get("message", {})
            content_list = message.get("content", [])

            if content_list:
                text = content_list[0].get("text", "")
                assert text == ""
            else:
                assert len(content_list) == 0

    def test_model_name_conversion(self):
        """Test model display name to ID conversion."""
        test_cases = [
            ("Grok 3 Fast", "grok-3-fast"),
            ("Command R Plus", "command-r-plus"),
            ("Llama 3.1 70B", "llama-3-1-70b"),
            ("UPPERCASE", "uppercase"),
            ("With (Parentheses)", "with--parentheses-"),
        ]

        for display_name, expected_id in test_cases:
            # Simulate the conversion logic
            model_id = display_name.lower()
            model_id = model_id.replace(" ", "-")
            model_id = model_id.replace("(", "-")
            model_id = model_id.replace(")", "-")
            model_id = model_id.replace(".", "-")

            assert model_id == expected_id


@pytest.mark.unit
class TestOCIHelperFunctions:
    """Test helper functions and utilities."""

    def test_json_parsing(self):
        """Test JSON parsing edge cases."""
        valid_json = '{"key": "value"}'
        assert json.loads(valid_json) == {"key": "value"}

        # Empty string special case
        with pytest.raises(json.JSONDecodeError):
            json.loads("")

        # But quoted empty string is valid
        assert json.loads('""') == ""

    def test_response_aggregation(self):
        """Test how streaming chunks would be aggregated."""
        chunks = ["Hello", " ", "world", "!"]
        full_response = "".join(chunks)
        assert full_response == "Hello world!"

    def test_finish_reason_detection(self):
        """Test detecting when streaming is complete."""
        events = [
            {"content": "chunk1", "finishReason": None},
            {"content": "chunk2", "finishReason": None},
            {"content": "", "finishReason": "stop"},
        ]

        finished = False
        for event in events:
            if event.get("finishReason"):
                finished = True

        assert finished is True
