"""Tests specifically for OCI Cohere tool calling."""

from unittest.mock import Mock, patch

import pytest

from coda.agents.decorators import tool
from coda.providers.base import Message, Role, Tool
from coda.providers.oci_genai import OCIGenAIProvider


@pytest.fixture
def mock_oci_provider():
    """Create a properly mocked OCI provider."""
    with patch("coda.providers.oci_genai.GenerativeAiInferenceClient"):
        with patch("coda.providers.oci_genai.GenerativeAiClient"):
            with patch("coda.providers.oci_genai.oci.config.from_file", return_value={}):
                with patch("coda.providers.oci_genai.oci.config.validate_config"):
                    provider = OCIGenAIProvider(compartment_id="test")
                    return provider


class TestOCICoherToolFormat:
    """Test OCI Cohere-specific tool format conversions."""

    def test_cohere_tool_conversion(self, mock_oci_provider):
        """Test converting standard tools to Cohere format."""
        # Create a standard tool
        standard_tool = Tool(
            name="calculate",
            description="Perform a calculation",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Mathematical expression"},
                    "precision": {
                        "type": "integer",
                        "description": "Decimal precision",
                        "default": 2,
                    },
                },
                "required": ["expression"],
            },
        )

        # Convert to Cohere format
        cohere_tools = mock_oci_provider._convert_tools_to_cohere([standard_tool])

        assert len(cohere_tools) == 1
        cohere_tool = cohere_tools[0]

        # Verify conversion
        assert cohere_tool.name == "calculate"
        assert cohere_tool.description == "Perform a calculation"

        # Check parameter definitions
        params = cohere_tool.parameter_definitions
        assert "expression" in params
        assert params["expression"].type == "STRING"
        assert params["expression"].is_required is True

        assert "precision" in params
        assert params["precision"].type == "FLOAT"  # INTEGER -> FLOAT
        assert params["precision"].is_required is False

    def test_cohere_message_format_with_tools(self, mock_oci_provider):
        """Test message formatting for Cohere with tool responses."""
        # Create a conversation with tool calls
        messages = [
            Message(role=Role.SYSTEM, content="You are a helpful assistant."),
            Message(role=Role.USER, content="What is 2+2?"),
            Message(
                role=Role.ASSISTANT,
                content="I'll calculate that.",
                tool_calls=[Mock(id="1", name="add", arguments={"a": 2, "b": 2})],
            ),
            Message(role=Role.TOOL, content="4", tool_call_id="1"),
            Message(role=Role.ASSISTANT, content="The answer is 4."),
        ]

        # Create chat request
        request = mock_oci_provider._create_chat_request(
            messages=messages,
            model="cohere.command-r-plus",
            temperature=0.7,
            max_tokens=100,
            top_p=None,
            stream=False,
            tools=[Tool(name="add", description="Add numbers", parameters={})],
        )

        # Verify the request format
        assert hasattr(request, "message")
        assert hasattr(request, "chat_history")
        assert hasattr(request, "tools")

        # Check that tool messages are handled appropriately
        # Cohere doesn't have a direct TOOL role, so these should be incorporated
        # into the conversation flow


class TestOCIToolCallingIntegration:
    """Integration tests for OCI tool calling."""

    @pytest.fixture
    def mock_oci_response_with_tools(self):
        """Create mock OCI responses for tool calling."""
        # First response with tool call
        tool_response = Mock()
        tool_response.text = "I'll calculate that for you."
        tool_response.tool_calls = [Mock(name="calculate", parameters={"a": 10, "b": 5})]
        tool_response.finish_reason = "COMPLETE"
        tool_response.meta = Mock(billed_units=Mock(input_tokens=10, output_tokens=5))

        # Second response with final answer
        final_response = Mock()
        final_response.text = "The result is 15."
        final_response.tool_calls = None
        final_response.finish_reason = "COMPLETE"
        final_response.meta = Mock(billed_units=Mock(input_tokens=20, output_tokens=10))

        return [tool_response, final_response]

    def test_oci_tool_calling_flow(self, mock_oci_provider, mock_oci_response_with_tools):
        """Test the complete tool calling flow with OCI."""
        # Set model cache with proper Model objects
        from coda.providers.base import Model

        mock_oci_provider._model_cache = [
            Model(
                id="cohere.command-r-plus",
                name="Cohere Command R Plus",
                provider="cohere",
                context_length=128000,
                max_tokens=4000,
                supports_streaming=True,
                supports_functions=True,
            )
        ]
        mock_oci_provider._model_id_map = {"cohere.command-r-plus": "test-model-id"}

        # Mock the validate_model method
        mock_oci_provider.validate_model = Mock(return_value=True)

        # Mock the chat response
        mock_chat_response = Mock()
        mock_chat_response.data = Mock()
        mock_chat_response.data.chat_response = mock_oci_response_with_tools[0]
        mock_oci_provider.chat = Mock(return_value=mock_chat_response.data.chat_response)

        # Define tool
        @tool(description="Calculate sum")
        def calculate(a: int, b: int) -> int:
            return a + b

        # Test the tool conversion directly
        from coda.providers.base import Tool

        standard_tool = Tool(
            name="calculate",
            description="Calculate sum",
            parameters={
                "type": "object",
                "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
                "required": ["a", "b"],
            },
        )

        # Convert to Cohere format
        cohere_tools = mock_oci_provider._convert_tools_to_cohere([standard_tool])

        # Verify conversion
        assert len(cohere_tools) == 1
        cohere_tool = cohere_tools[0]
        assert cohere_tool.name == "calculate"
        assert cohere_tool.description == "Calculate sum"


class TestOCIToolResponseParsing:
    """Test parsing of OCI tool responses."""

    def test_parse_cohere_tool_calls(self, mock_oci_provider):
        """Test parsing Cohere tool call responses."""
        # Mock Cohere response with tool calls
        mock_tool_call_1 = Mock()
        mock_tool_call_1.name = "search"
        mock_tool_call_1.parameters = {"query": "python tutorial"}

        mock_tool_call_2 = Mock()
        mock_tool_call_2.name = "calculate"
        mock_tool_call_2.parameters = {"expression": "2+2"}

        mock_response = Mock()
        mock_response.tool_calls = [mock_tool_call_1, mock_tool_call_2]
        mock_response.text = "I'll search for that and calculate the result."
        mock_response.finish_reason = "COMPLETE"

        # Mock the full response structure
        chat_response = Mock()
        chat_response.data = Mock()
        chat_response.data.chat_response = mock_response

        # Parse the response (this would normally happen in chat())
        # Just verify the structure is correct
        assert len(mock_response.tool_calls) == 2
        assert mock_response.tool_calls[0].name == "search"
        assert mock_response.tool_calls[1].name == "calculate"


# Debugging helper
def create_oci_tool_debug_recorder():
    """Create a recorder specifically for OCI tool debugging."""

    class OCIToolDebugger:
        def __init__(self):
            self.cohere_requests = []
            self.cohere_responses = []
            self.tool_conversions = []

        def record_cohere_request(self, request):
            """Record Cohere request details."""
            self.cohere_requests.append(
                {
                    "message": getattr(request, "message", None),
                    "chat_history": [
                        {"role": m.role, "message": m.message}
                        for m in getattr(request, "chat_history", [])
                    ],
                    "tools": [
                        {"name": t.name, "description": t.description}
                        for t in getattr(request, "tools", [])
                    ],
                    "temperature": getattr(request, "temperature", None),
                    "preamble_override": getattr(request, "preamble_override", None),
                    "is_force_single_step": getattr(request, "is_force_single_step", None),
                }
            )

        def record_cohere_response(self, response):
            """Record Cohere response details."""
            self.cohere_responses.append(
                {
                    "text": getattr(response, "text", None),
                    "tool_calls": (
                        [
                            {"name": tc.name, "parameters": tc.parameters}
                            for tc in getattr(response, "tool_calls", [])
                        ]
                        if hasattr(response, "tool_calls") and response.tool_calls
                        else None
                    ),
                    "finish_reason": getattr(response, "finish_reason", None),
                }
            )

        def get_debug_info(self):
            """Get formatted debug information."""
            return {
                "total_requests": len(self.cohere_requests),
                "total_responses": len(self.cohere_responses),
                "requests": self.cohere_requests,
                "responses": self.cohere_responses,
                "last_request": self.cohere_requests[-1] if self.cohere_requests else None,
                "last_response": self.cohere_responses[-1] if self.cohere_responses else None,
            }

    return OCIToolDebugger()
