"""Functional tests for tool chat command workflows."""

import json
from unittest.mock import Mock, patch

import pytest
from rich.console import Console

from coda.agents.decorators import tool
from coda.cli.tool_chat import ToolChatHandler
from coda.providers.base import Message, Role, Tool, ToolCall, ToolResult


# Create test tool at module level to avoid pytest fixture confusion
def _create_test_custom_tool():
    @tool
    def custom_tool_for_testing(input: str) -> str:
        """Custom tool for testing."""
        return f"Custom: {input}"

    return custom_tool_for_testing


custom_tool_for_testing = _create_test_custom_tool()


class MockCLI:
    """Mock CLI for testing."""

    def __init__(self):
        self.messages = []
        self.interrupt_event = Mock()
        self.interrupt_event.is_set.return_value = False


class TestToolChatWorkflow:
    """Test tool chat workflows."""

    def _create_tool_handler(self, cli, provider):
        """Create a ToolChatHandler with the correct signature."""
        console = Console()
        return ToolChatHandler(provider, cli, console)

    @pytest.mark.asyncio
    async def test_tools_basic_workflow(self):
        """Test basic tool chat workflow."""
        cli = MockCLI()
        provider = Mock()

        # Mock response without tools
        response = Mock()
        response.content = "I understand your request."
        response.tool_calls = []
        provider.chat = Mock(return_value=response)

        handler = self._create_tool_handler(cli, provider)

        messages = [Message(role=Role.USER, content="Hello, can you help?")]

        # Test chat
        result, updated_messages = await handler.chat_with_tools(
            messages=messages, model="cohere.command"
        )

        # Verify
        assert result == "I understand your request."
        assert len(updated_messages) == 2  # Should have user + assistant messages

    @pytest.mark.asyncio
    async def test_tools_with_cohere_model(self):
        """Test tools are enabled for Cohere models."""
        cli = MockCLI()
        provider = Mock()

        handler = self._create_tool_handler(cli, provider)

        # Cohere models should support tools
        assert handler.should_use_tools("cohere.command") is True
        assert handler.should_use_tools("cohere.command-r") is True

        # Non-Cohere models should not
        assert handler.should_use_tools("gpt-4") is False
        assert handler.should_use_tools("claude-3") is False

    @pytest.mark.asyncio
    async def test_tools_disabled(self):
        """Test when tools are disabled."""
        cli = MockCLI()
        provider = Mock()

        handler = self._create_tool_handler(cli, provider)
        handler.tools_enabled = False

        # Should not use tools even for Cohere
        assert handler.should_use_tools("cohere.command") is False

    @pytest.mark.asyncio
    async def test_tool_execution_workflow(self):
        """Test tool execution workflow."""
        cli = MockCLI()
        provider = Mock()

        # Mock tool call
        tool_call = ToolCall(
            id="test_call", name="custom_tool_for_testing", arguments={"input": "hello"}
        )

        # Mock provider responses
        response1 = Mock()
        response1.content = "I'll use the custom tool."
        response1.tool_calls = [tool_call]

        response2 = Mock()
        response2.content = "The custom tool returned: Custom: hello"
        response2.tool_calls = []

        provider.chat = Mock(side_effect=[response1, response2])

        handler = self._create_tool_handler(cli, provider)

        # Mock tool executor
        mock_result = ToolResult(tool_call_id="test_call", content="Custom: hello", is_error=False)
        with patch.object(handler.executor, "execute_tool_call", return_value=mock_result):
            with patch.object(
                handler.executor,
                "get_available_tools",
                return_value=[
                    Tool(
                        name="custom_tool_for_testing",
                        description="Custom tool for testing",
                        parameters={"type": "object", "properties": {"input": {"type": "string"}}},
                    )
                ],
            ):
                messages = [Message(role=Role.USER, content="Use the custom tool with 'hello'")]

                result, updated_messages = await handler.chat_with_tools(
                    messages=messages, model="cohere.command"
                )

                assert "Custom: hello" in result

    @pytest.mark.asyncio
    async def test_tool_error_handling(self):
        """Test tool error handling."""
        cli = MockCLI()
        provider = Mock()

        # Mock tool call
        tool_call = ToolCall(id="error_call", name="failing_tool", arguments={})

        response1 = Mock()
        response1.content = "I'll try this tool."
        response1.tool_calls = [tool_call]

        response2 = Mock()
        response2.content = "The tool encountered an error."
        response2.tool_calls = []

        provider.chat = Mock(side_effect=[response1, response2])

        handler = self._create_tool_handler(cli, provider)

        # Mock tool executor to return error
        mock_result = ToolResult(
            tool_call_id="error_call", content="Tool execution failed", is_error=True
        )
        with patch.object(handler.executor, "execute_tool_call", return_value=mock_result):
            with patch.object(handler.executor, "get_available_tools", return_value=[]):
                messages = [Message(role=Role.USER, content="Try the failing tool")]

                result, updated_messages = await handler.chat_with_tools(
                    messages=messages, model="cohere.command"
                )

                # Should handle error gracefully
                assert "error" in result.lower() or "encountered" in result.lower()

    @pytest.mark.asyncio
    async def test_multiple_tool_calls(self):
        """Test handling multiple tool calls."""
        cli = MockCLI()
        provider = Mock()

        # Mock multiple tool calls
        tool_calls = [
            ToolCall(id="call1", name="tool1", arguments={"arg": "value1"}),
            ToolCall(id="call2", name="tool2", arguments={"arg": "value2"}),
        ]

        response1 = Mock()
        response1.content = "I'll use multiple tools."
        response1.tool_calls = tool_calls

        response2 = Mock()
        response2.content = "Both tools completed successfully."
        response2.tool_calls = []

        provider.chat = Mock(side_effect=[response1, response2])

        handler = self._create_tool_handler(cli, provider)

        # Mock tool executor
        results = [
            ToolResult(tool_call_id="call1", content="Result 1", is_error=False),
            ToolResult(tool_call_id="call2", content="Result 2", is_error=False),
        ]
        with patch.object(handler.executor, "execute_tool_call", side_effect=results):
            with patch.object(handler.executor, "get_available_tools", return_value=[]):
                messages = [Message(role=Role.USER, content="Use multiple tools")]

                result, updated_messages = await handler.chat_with_tools(
                    messages=messages, model="cohere.command"
                )

                assert "completed successfully" in result.lower()

    @pytest.mark.asyncio
    async def test_system_prompt_handling(self):
        """Test system prompt is properly handled."""
        cli = MockCLI()
        provider = Mock()

        response = Mock()
        response.content = "Following system instructions."
        response.tool_calls = []
        provider.chat = Mock(return_value=response)

        handler = self._create_tool_handler(cli, provider)

        messages = [Message(role=Role.USER, content="Test with system prompt")]

        result, updated_messages = await handler.chat_with_tools(
            messages=messages, model="cohere.command", system_prompt="You are a helpful assistant."
        )

        # Verify system prompt was added
        assert updated_messages[0].role == Role.SYSTEM
        assert updated_messages[0].content == "You are a helpful assistant."

    @pytest.mark.asyncio
    async def test_streaming_fallback(self):
        """Test fallback to streaming when tools not supported."""
        cli = MockCLI()
        provider = Mock()

        # Mock streaming response
        chunks = []
        for text in ["Streaming", " response", " here"]:
            chunk = Mock()
            chunk.content = text
            chunks.append(chunk)

        provider.chat_stream.return_value = iter(chunks)

        handler = self._create_tool_handler(cli, provider)

        messages = [Message(role=Role.USER, content="Test streaming")]

        # Test with non-Cohere model (no tools)
        result, updated_messages = await handler.chat_with_tools(
            messages=messages,
            model="gpt-4",  # Non-Cohere model
        )

        assert result == "Streaming response here"

    @pytest.mark.asyncio
    async def test_interrupt_handling(self):
        """Test interrupt handling during streaming."""
        cli = MockCLI()
        provider = Mock()

        # Mock streaming that will be interrupted
        def interrupted_stream():
            yield Mock(content="Part 1")
            cli.interrupt_event.is_set.return_value = True
            yield Mock(content="Part 2")  # Should not be processed

        provider.chat_stream.return_value = interrupted_stream()

        handler = self._create_tool_handler(cli, provider)

        messages = [Message(role=Role.USER, content="Test interrupt")]

        result, _ = await handler.chat_with_tools(
            messages=messages,
            model="gpt-4",  # Non-Cohere for streaming test
        )

        # Should only have Part 1
        assert result == "Part 1"

    @pytest.mark.asyncio
    async def test_json_tool_result_formatting(self):
        """Test JSON formatting of tool results."""
        cli = MockCLI()
        provider = Mock()

        # Mock tool call with JSON result
        tool_call = ToolCall(id="json_call", name="json_tool", arguments={})

        response1 = Mock()
        response1.content = ""
        response1.tool_calls = [tool_call]

        response2 = Mock()
        response2.content = "Processed JSON data"
        response2.tool_calls = []

        provider.chat = Mock(side_effect=[response1, response2])

        handler = self._create_tool_handler(cli, provider)

        # Mock tool executor with JSON result
        json_data = {"status": "success", "data": {"value": 42}}
        mock_result = ToolResult(
            tool_call_id="json_call", content=json.dumps(json_data), is_error=False
        )
        with patch.object(handler.executor, "execute_tool_call", return_value=mock_result):
            with patch.object(handler.executor, "get_available_tools", return_value=[]):
                messages = [Message(role=Role.USER, content="Get JSON data")]

                result, updated_messages = await handler.chat_with_tools(
                    messages=messages, model="cohere.command"
                )

                # Check that JSON was properly handled
                tool_result_msg = next(msg for msg in updated_messages if msg.role == Role.TOOL)
                assert json.loads(tool_result_msg.content) == json_data
