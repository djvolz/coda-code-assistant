"""Integration tests for OCI tool support error handling."""

from unittest.mock import MagicMock, patch

import pytest

from coda.base.providers.base import Message, Role, Tool
from coda.base.providers.oci_genai import OCIGenAIProvider


@pytest.mark.integration
class TestOCIToolSupportErrors:
    """Test OCI tool support error scenarios."""

    def test_model_without_tool_support_error(self):
        """Test that models without tool support raise clear errors."""
        # This simulates: coda agent --provider oci_genai --model meta.llama-3.3-70b-instruct --tools "What's the weather?"

        with patch("coda.base.providers.oci_genai.oci.config.load_config"):
            with patch.object(OCIGenAIProvider, "_initialize_models"):
                provider = OCIGenAIProvider()

                # Mock the tool tester to return known result
                with patch.object(provider, "_get_tool_tester") as mock_tester:
                    mock_tool_tester = MagicMock()
                    mock_tool_tester.get_tool_support.return_value = {
                        "tested": True,
                        "tools_work": False,
                        "error": "fine-tuning base model",
                    }
                    mock_tester.return_value = mock_tool_tester

                    messages = [Message(role=Role.USER, content="What's the weather?")]
                    tools = [
                        Tool(
                            name="get_weather",
                            description="Get weather information",
                            parameters={"type": "object", "properties": {}, "required": []},
                        )
                    ]

                    # Should raise ValueError with clear message
                    with pytest.raises(ValueError) as exc_info:
                        provider.chat(
                            messages=messages, model="meta.llama-3.3-70b-instruct", tools=tools
                        )

                    error_msg = str(exc_info.value)
                    assert "does not support tool/function calling" in error_msg
                    assert "fine-tuning base model" in error_msg
                    assert "Please use a model that supports tools" in error_msg

    def test_model_with_partial_support_warning(self, caplog):
        """Test that models with partial support log warnings but still work."""
        # This simulates: coda agent --provider oci_genai --model cohere.command-r-plus --tools "What's the weather?"

        with patch("coda.base.providers.oci_genai.oci.config.load_config"):
            with patch.object(OCIGenAIProvider, "_initialize_models"):
                provider = OCIGenAIProvider()

                # Mock the tool tester to return partial support
                with patch.object(provider, "_get_tool_tester") as mock_tester:
                    mock_tool_tester = MagicMock()
                    mock_tool_tester.get_tool_support.return_value = {
                        "tested": True,
                        "tools_work": True,
                        "streaming_tools": False,
                    }
                    mock_tester.return_value = mock_tool_tester

                    # Mock the inference client for streaming
                    mock_event = MagicMock()
                    mock_event.data = '{"text": "The weather is sunny."}'

                    mock_stream = MagicMock()
                    mock_stream.data.events.return_value = [mock_event]

                    provider.inference_client = MagicMock()
                    provider.inference_client.chat.return_value = mock_stream

                    messages = [Message(role=Role.USER, content="What's the weather?")]
                    tools = [
                        Tool(
                            name="get_weather",
                            description="Get weather information",
                            parameters={"type": "object", "properties": {}, "required": []},
                        )
                    ]

                    # Should work but log warning for streaming
                    list(
                        provider.chat_stream(
                            messages=messages, model="cohere.command-r-plus", tools=tools
                        )
                    )

                    # Check warning was logged
                    warning_found = False
                    for record in caplog.records:
                        if "supports tools but not in streaming mode" in record.message:
                            warning_found = True
                            assert "cohere.command-r-plus" in record.message
                            break

                    assert warning_found, "Expected warning about streaming not found"

    def test_various_error_types(self):
        """Test different types of tool support errors."""
        test_cases = [
            ("xai.grok-3-mini", "not supported", "Model doesn't support tools"),
            ("meta.llama-3.2-11b-vision-instruct", "model not found (404)", "Model not accessible"),
            ("cohere.command", "bad request (400)", "Invalid request"),
        ]

        with patch("coda.base.providers.oci_genai.oci.config.load_config"):
            with patch.object(OCIGenAIProvider, "_initialize_models"):
                provider = OCIGenAIProvider()

                for model_id, error_type, _expected_msg_part in test_cases:
                    with patch.object(provider, "_get_tool_tester") as mock_tester:
                        mock_tool_tester = MagicMock()
                        mock_tool_tester.get_tool_support.return_value = {
                            "tested": True,
                            "tools_work": False,
                            "error": error_type,
                        }
                        mock_tester.return_value = mock_tool_tester

                        messages = [Message(role=Role.USER, content="Test")]
                        tools = [
                            Tool(
                                name="test_tool",
                                description="Test tool",
                                parameters={"type": "object", "properties": {}, "required": []},
                            )
                        ]

                        with pytest.raises(ValueError) as exc_info:
                            provider.chat(messages=messages, model=model_id, tools=tools)

                        error_msg = str(exc_info.value)
                        assert model_id in error_msg
                        assert error_type in error_msg
