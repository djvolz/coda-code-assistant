"""Comprehensive tests for tool calling functionality."""

from typing import Any
from unittest.mock import Mock, patch

import pytest

from coda.agents import Agent, FunctionTool, tool
from coda.providers.base import ChatCompletion, Message, Role, Tool, ToolCall


# Test tools
@tool(description="Add two numbers")
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@tool(description="Multiply two numbers")
def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b


class ToolCallRecorder:
    """Helper class to record tool calling interactions."""

    def __init__(self):
        self.requests = []
        self.responses = []
        self.tool_executions = []

    def record_request(self, messages: list[Message], tools: list[Tool], **kwargs):
        """Record an API request."""
        self.requests.append(
            {
                "messages": [{"role": m.role.value, "content": m.content} for m in messages],
                "tools": (
                    [{"name": t.name, "description": t.description} for t in tools]
                    if tools
                    else None
                ),
                "kwargs": kwargs,
            }
        )

    def record_response(self, response: ChatCompletion):
        """Record an API response."""
        self.responses.append(
            {
                "content": response.content,
                "tool_calls": (
                    [{"name": tc.name, "arguments": tc.arguments} for tc in response.tool_calls]
                    if response.tool_calls
                    else None
                ),
                "finish_reason": response.finish_reason,
            }
        )

    def record_tool_execution(self, tool_name: str, arguments: dict[str, Any], result: Any):
        """Record a tool execution."""
        self.tool_executions.append({"tool": tool_name, "arguments": arguments, "result": result})

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all recorded interactions."""
        return {
            "total_requests": len(self.requests),
            "total_responses": len(self.responses),
            "total_tool_executions": len(self.tool_executions),
            "requests": self.requests,
            "responses": self.responses,
            "tool_executions": self.tool_executions,
        }


class TestToolCallingFlow:
    """Test the complete tool calling flow with inspection."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock provider with recording capabilities."""
        provider = Mock()
        provider.name = "test_provider"
        provider.list_models.return_value = [Mock(id="test.model", supports_functions=True)]
        return provider

    @pytest.fixture
    def recorder(self):
        """Create a tool call recorder."""
        return ToolCallRecorder()

    def test_single_tool_call_flow(self, mock_provider, recorder):
        """Test a single tool call with full inspection."""
        # Setup mock responses
        tool_call = ToolCall(id="1", name="add", arguments={"a": 5, "b": 3})

        def mock_chat(messages, model, tools=None, **kwargs):
            recorder.record_request(messages, tools, model=model, **kwargs)

            # First call: return tool request
            if len(recorder.requests) == 1:
                response = ChatCompletion(
                    content="I'll add those numbers for you.",
                    model=model,
                    tool_calls=[tool_call],
                    finish_reason="tool_calls",
                )
            # Second call: return final answer
            else:
                response = ChatCompletion(
                    content="The sum of 5 and 3 is 8.", model=model, finish_reason="stop"
                )

            recorder.record_response(response)
            return response

        mock_provider.chat.side_effect = mock_chat

        # Patch tool execution to record it
        original_execute = FunctionTool.execute

        async def mock_execute(self, arguments):
            result = await original_execute(self, arguments)
            recorder.record_tool_execution(self.name, arguments, result)
            return result

        with patch.object(FunctionTool, "execute", mock_execute):
            # Create agent and run
            agent = Agent(
                provider=mock_provider,
                model="test.model",
                tools=[add],
                console=Mock(),  # Mock console to suppress output
            )

            agent.run("What is 5 + 3?")

        # Verify the flow
        summary = recorder.get_summary()

        # Should have 2 requests and 2 responses
        assert summary["total_requests"] == 2
        assert summary["total_responses"] == 2
        assert summary["total_tool_executions"] == 1

        # First request should include tools
        first_request = summary["requests"][0]
        assert first_request["tools"] is not None
        assert len(first_request["tools"]) == 1
        assert first_request["tools"][0]["name"] == "add"

        # First response should have tool calls
        first_response = summary["responses"][0]
        assert first_response["tool_calls"] is not None
        assert len(first_response["tool_calls"]) == 1
        assert first_response["tool_calls"][0]["name"] == "add"
        assert first_response["tool_calls"][0]["arguments"] == {"a": 5, "b": 3}

        # Tool should have been executed
        tool_exec = summary["tool_executions"][0]
        assert tool_exec["tool"] == "add"
        assert tool_exec["arguments"] == {"a": 5, "b": 3}
        assert tool_exec["result"] == 8

        # Second request should include tool result
        second_request = summary["requests"][1]
        messages = second_request["messages"]
        # Should have system, user, assistant (with tool call), and tool result
        assert len(messages) >= 4
        tool_message = next((m for m in messages if m["role"] == "tool"), None)
        assert tool_message is not None
        assert tool_message["content"] == "8"

        # Final response should be the answer
        final_response = summary["responses"][1]
        assert final_response["tool_calls"] is None
        assert "8" in final_response["content"]
        assert final_response["finish_reason"] == "stop"

    def test_multiple_tool_calls_in_sequence(self, mock_provider, recorder):
        """Test multiple tool calls in sequence."""
        # This test would verify that the agent can handle multiple tool calls
        # in a single response and execute them properly
        tool_calls = [
            ToolCall(id="1", name="add", arguments={"a": 10, "b": 20}),
            ToolCall(id="2", name="multiply", arguments={"a": 5, "b": 6}),
        ]

        def mock_chat(messages, model, tools=None, **kwargs):
            recorder.record_request(messages, tools, model=model, **kwargs)

            if len(recorder.requests) == 1:
                response = ChatCompletion(
                    content="I'll calculate both operations.",
                    model=model,
                    tool_calls=tool_calls,
                    finish_reason="tool_calls",
                )
            else:
                response = ChatCompletion(
                    content="The sum is 30 and the product is 30.",
                    model=model,
                    finish_reason="stop",
                )

            recorder.record_response(response)
            return response

        mock_provider.chat.side_effect = mock_chat

        # Patch tool execution to record it
        original_execute = FunctionTool.execute

        async def mock_execute(self, arguments):
            result = await original_execute(self, arguments)
            recorder.record_tool_execution(self.name, arguments, result)
            return result

        with patch.object(FunctionTool, "execute", mock_execute):
            # Create agent with multiple tools
            agent = Agent(
                provider=mock_provider, model="test.model", tools=[add, multiply], console=Mock()
            )

            agent.run("Add 10 and 20, then multiply 5 and 6")

        # Verify both tools were called
        summary = recorder.get_summary()
        assert summary["total_tool_executions"] == 2

        # Verify correct execution order and results
        assert summary["tool_executions"][0]["tool"] == "add"
        assert summary["tool_executions"][0]["result"] == 30
        assert summary["tool_executions"][1]["tool"] == "multiply"
        assert summary["tool_executions"][1]["result"] == 30

    def test_tool_call_error_handling(self, mock_provider, recorder):
        """Test how errors in tool execution are handled."""

        @tool(description="Divide two numbers")
        def divide(a: int, b: int) -> float:
            """Divide a by b."""
            if b == 0:
                raise ValueError("Cannot divide by zero")
            return a / b

        tool_call = ToolCall(id="1", name="divide", arguments={"a": 10, "b": 0})

        def mock_chat(messages, model, tools=None, **kwargs):
            recorder.record_request(messages, tools, model=model, **kwargs)

            if len(recorder.requests) == 1:
                response = ChatCompletion(
                    content="I'll divide those numbers.",
                    model=model,
                    tool_calls=[tool_call],
                    finish_reason="tool_calls",
                )
            else:
                # Check if error was passed back
                tool_msg = next((m for m in messages if m.role == Role.TOOL), None)
                if tool_msg and "Error" in tool_msg.content:
                    response = ChatCompletion(
                        content="I cannot divide by zero. This would result in an error.",
                        model=model,
                        finish_reason="stop",
                    )
                else:
                    response = ChatCompletion(
                        content="The result is calculated.", model=model, finish_reason="stop"
                    )

            recorder.record_response(response)
            return response

        mock_provider.chat.side_effect = mock_chat

        # Patch tool execution to record it (including errors)
        original_execute = FunctionTool.execute

        async def mock_execute(self, arguments):
            try:
                result = await original_execute(self, arguments)
                recorder.record_tool_execution(self.name, arguments, result)
                return result
            except Exception as e:
                recorder.record_tool_execution(self.name, arguments, f"Error: {str(e)}")
                raise

        with patch.object(FunctionTool, "execute", mock_execute):
            agent = Agent(
                provider=mock_provider, model="test.model", tools=[divide], console=Mock()
            )

            agent.run("Divide 10 by 0")

        # Verify error was handled
        summary = recorder.get_summary()
        assert summary["total_requests"] == 2
        assert summary["total_tool_executions"] == 1

        # Tool execution should show the error
        tool_exec = summary["tool_executions"][0]
        assert "Error" in str(tool_exec["result"])

        # Final response should acknowledge the error
        final_response = summary["responses"][1]
        assert (
            "cannot divide" in final_response["content"].lower()
            or "error" in final_response["content"].lower()
        )


class TestProviderToolFormat:
    """Test tool format conversions for different providers."""

    def test_tool_to_provider_format(self):
        """Test converting agent tools to provider format."""
        # Create a function tool
        FunctionTool.from_callable(add)

        # Convert to provider format
        agent = Agent(provider=Mock(), model="test.model", tools=[add], console=Mock())

        provider_tools = agent._get_provider_tools()

        assert len(provider_tools) == 1
        tool = provider_tools[0]
        assert tool.name == "add"
        assert tool.description == "Add two numbers"
        assert "properties" in tool.parameters
        assert "a" in tool.parameters["properties"]
        assert "b" in tool.parameters["properties"]
        assert tool.parameters["required"] == ["a", "b"]

    def test_tool_call_id_handling(self):
        """Test that tool call IDs are properly handled."""
        recorder = ToolCallRecorder()

        # Mock provider that records tool messages
        provider = Mock()
        provider.name = "test"
        provider.list_models.return_value = [Mock(id="test.model", supports_functions=True)]

        tool_call = ToolCall(id="unique-id-123", name="add", arguments={"a": 1, "b": 2})

        def mock_chat(messages, model, tools=None, **kwargs):
            recorder.record_request(messages, tools, model=model, **kwargs)

            if len(recorder.requests) == 1:
                response = ChatCompletion(
                    content="Adding numbers.", model=model, tool_calls=[tool_call]
                )
            else:
                # Verify tool message has correct ID
                tool_msg = next((m for m in messages if m.role == Role.TOOL), None)
                assert tool_msg is not None
                assert tool_msg.tool_call_id == "unique-id-123"

                response = ChatCompletion(content="The result is 3.", model=model)

            recorder.record_response(response)
            return response

        provider.chat.side_effect = mock_chat

        agent = Agent(provider=provider, model="test.model", tools=[add], console=Mock())

        agent.run("Add 1 and 2")

        # Verify the tool call ID was preserved
        summary = recorder.get_summary()
        assert summary["total_requests"] == 2


class TestToolParameterValidation:
    """Test tool parameter extraction and validation."""

    def test_parameter_type_inference(self):
        """Test that parameter types are correctly inferred."""

        @tool(description="Complex function")
        def complex_func(
            text: str, number: int, decimal: float, flag: bool, items: list, mapping: dict
        ) -> str:
            """A function with various parameter types."""
            return "processed"

        func_tool = FunctionTool.from_callable(complex_func)
        params = func_tool.parameters["properties"]

        assert params["text"]["type"] == "string"
        assert params["number"]["type"] == "integer"
        assert params["decimal"]["type"] == "number"
        assert params["flag"]["type"] == "boolean"
        assert params["items"]["type"] == "array"
        assert params["mapping"]["type"] == "object"

    def test_optional_parameters(self):
        """Test handling of optional parameters."""

        @tool(description="Function with optional params")
        def optional_func(required: str, optional: int = 10) -> str:
            """Function with optional parameters."""
            return f"{required}-{optional}"

        func_tool = FunctionTool.from_callable(optional_func)

        assert "required" in func_tool.parameters["required"]
        assert "optional" not in func_tool.parameters["required"]


# Integration test with actual tool execution
@pytest.mark.asyncio
async def test_async_tool_execution():
    """Test async tool execution flow."""
    recorder = ToolCallRecorder()

    @tool(description="Async operation")
    async def async_operation(value: str) -> str:
        """Simulate async operation."""
        import asyncio

        await asyncio.sleep(0.01)  # Simulate async work
        recorder.record_tool_execution("async_operation", {"value": value}, f"async-{value}")
        return f"async-{value}"

    func_tool = FunctionTool.from_callable(async_operation)
    result = await func_tool.execute({"value": "test"})

    assert result == "async-test"
    assert recorder.tool_executions[0]["result"] == "async-test"
