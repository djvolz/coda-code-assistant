"""Integration tests for agent-tool interaction."""

import asyncio
import os
import tempfile
from unittest.mock import Mock

import pytest

from coda.agents.agent import Agent
from coda.agents.builtin_tools import get_builtin_tools
from coda.agents.decorators import tool


# Helper function to create test tools
def create_test_tools():
    """Create test tools for integration testing."""

    @tool
    def test_add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    @tool
    def test_multiply(x: int, y: int) -> int:
        """Multiply two numbers."""
        return x * y

    @tool
    async def test_async_operation(value: str) -> str:
        """Async operation that processes a string."""
        await asyncio.sleep(0.01)
        return f"Processed: {value.upper()}"

    @tool
    def test_error_tool(should_fail: bool = True) -> str:
        """Tool that can raise errors for testing."""
        if should_fail:
            raise ValueError("Intentional test error")
        return "Success"

    @tool
    def test_complex_return() -> dict:
        """Tool that returns complex data structure."""
        return {"status": "ok", "data": [1, 2, 3], "nested": {"key": "value"}}

    return {
        "test_add": test_add,
        "test_multiply": test_multiply,
        "test_async_operation": test_async_operation,
        "test_error_tool": test_error_tool,
        "test_complex_return": test_complex_return,
    }


class MockProvider:
    """Mock provider for testing."""

    def __init__(self):
        self.chat_responses = []
        self.current_response = 0
        self.called_with = []

    def add_response(self, content: str, tool_calls=None):
        """Add a mock response."""
        response = Mock()
        response.content = content
        response.tool_calls = tool_calls or []
        self.chat_responses.append(response)

    def chat(self, messages, tools=None, **kwargs):
        """Mock chat method."""
        self.called_with.append({"messages": messages, "tools": tools, "kwargs": kwargs})

        if self.current_response < len(self.chat_responses):
            response = self.chat_responses[self.current_response]
            self.current_response += 1
            return response

        # Default response
        response = Mock()
        response.content = "No more responses"
        response.tool_calls = []
        return response

    def list_models(self):
        """Mock list_models method."""
        model = Mock()
        model.id = "test-model"
        model.supports_functions = True
        return [model]


class TestAgentToolIntegration:
    """Test agent-tool integration scenarios."""

    def setup_method(self):
        """Set up test tools for each test."""
        self.tools = create_test_tools()

    @pytest.mark.asyncio
    async def test_single_tool_execution(self):
        """Test agent executing a single tool."""
        provider = MockProvider()
        agent = Agent(provider=provider, model="test-model", tools=[self.tools["test_add"]])

        # Mock provider response with tool call
        tool_call = Mock()
        tool_call.name = "test_add"
        tool_call.id = "call_123"
        tool_call.arguments = {"a": 5, "b": 3}
        provider.add_response("I'll add those numbers for you.", [tool_call])
        provider.add_response("The sum of 5 and 3 is 8.")

        # Run agent
        response = await agent.run_async("Add 5 and 3")

        # Check response
        assert response.content == "The sum of 5 and 3 is 8."
        # Verify tool was called through provider
        assert len(provider.called_with) == 2  # Initial call + tool result call
        assert provider.called_with[0]["tools"] is not None

    @pytest.mark.asyncio
    async def test_multiple_tool_calls(self):
        """Test agent executing multiple tools in sequence."""
        provider = MockProvider()
        agent = Agent(
            provider=provider,
            model="test-model",
            tools=[self.tools["test_add"], self.tools["test_multiply"]],
        )

        # Mock provider responses
        tool_call1 = Mock()
        tool_call1.name = "test_add"
        tool_call1.id = "call_1"
        tool_call1.arguments = {"a": 2, "b": 3}

        tool_call2 = Mock()
        tool_call2.name = "test_multiply"
        tool_call2.id = "call_2"
        tool_call2.arguments = {"x": 5, "y": 4}

        provider.add_response("I'll perform both calculations.", [tool_call1, tool_call2])
        provider.add_response("2 + 3 = 5 and 5 × 4 = 20.")

        # Run agent
        response = await agent.run_async("Add 2 and 3, then multiply 5 by 4")

        # Check response
        assert "5" in response.content
        assert "20" in response.content
        # Verify both tools were called
        assert len(provider.called_with) == 2

    @pytest.mark.asyncio
    async def test_async_tool_execution(self):
        """Test agent executing async tools."""
        provider = MockProvider()
        agent = Agent(
            provider=provider, model="test-model", tools=[self.tools["test_async_operation"]]
        )

        # Mock provider response
        tool_call = Mock()
        tool_call.name = "test_async_operation"
        tool_call.id = "async_call"
        tool_call.arguments = {"value": "hello"}
        provider.add_response("Processing your text.", [tool_call])
        provider.add_response("Processed: HELLO")

        # Run agent
        response = await agent.run_async("Process the text 'hello'")

        # Check response
        assert "HELLO" in response.content or "processed" in response.content.lower()

    @pytest.mark.asyncio
    async def test_tool_error_handling(self):
        """Test agent handling tool execution errors."""
        provider = MockProvider()
        agent = Agent(provider=provider, model="test-model", tools=[self.tools["test_error_tool"]])

        # Mock provider response
        tool_call = Mock()
        tool_call.name = "test_error_tool"
        tool_call.id = "error_call"
        tool_call.arguments = {"should_fail": True}
        provider.add_response("Let me try that.", [tool_call])
        provider.add_response("I encountered an error: Intentional test error")

        # Run agent
        response = await agent.run_async("Run the error tool")

        # Check error was handled
        assert "error" in response.content.lower()

    @pytest.mark.asyncio
    async def test_complex_data_handling(self):
        """Test agent handling complex return values."""
        provider = MockProvider()
        agent = Agent(
            provider=provider, model="test-model", tools=[self.tools["test_complex_return"]]
        )

        # Mock provider response
        tool_call = Mock()
        tool_call.name = "test_complex_return"
        tool_call.id = "complex_call"
        tool_call.arguments = {}
        provider.add_response("Getting complex data.", [tool_call])
        provider.add_response("The data shows status: ok with nested values.")

        # Run agent
        response = await agent.run_async("Get complex data")

        # Check response mentions the data
        assert "status" in response.content or "ok" in response.content

    @pytest.mark.asyncio
    async def test_builtin_tools_integration(self):
        """Test integration with built-in tools."""
        provider = MockProvider()
        agent = Agent(provider=provider, model="test-model", tools=get_builtin_tools())

        # Test get_datetime tool
        tool_call = Mock()
        tool_call.name = "get_datetime"
        tool_call.id = "datetime_call"
        tool_call.arguments = {}
        provider.add_response("Getting current time.", [tool_call])
        provider.add_response("The current time has been retrieved.")

        response = await agent.run_async("What time is it?")

        # Check that datetime was retrieved
        assert "time" in response.content.lower() or "retrieved" in response.content

    @pytest.mark.asyncio
    async def test_file_operations_integration(self):
        """Test file operation tools integration."""
        provider = MockProvider()
        # Add file tools
        from coda.agents.builtin_tools import list_files, read_file, write_file

        agent = Agent(
            provider=provider, model="test-model", tools=[read_file, write_file, list_files]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            # Test write operation
            write_call = Mock()
            write_call.name = "write_file"
            write_call.id = "write_1"
            write_call.arguments = {
                "file_path": os.path.join(tmpdir, "test.txt"),
                "content": "Hello, World!",
            }

            # Test read operation
            read_call = Mock()
            read_call.name = "read_file"
            read_call.id = "read_1"
            read_call.arguments = {"file_path": os.path.join(tmpdir, "test.txt")}

            provider.add_response("Writing to file.", [write_call])
            provider.add_response("Reading from file.", [read_call])
            provider.add_response("File operations completed.")

            # Run agent
            response = await agent.run_async(
                f"Write 'Hello, World!' to {tmpdir}/test.txt then read it back"
            )

            # Check operations completed
            assert "completed" in response.content or "file" in response.content.lower()
            # Verify file was actually written
            assert os.path.exists(os.path.join(tmpdir, "test.txt"))

    @pytest.mark.asyncio
    async def test_tool_not_found(self):
        """Test agent handling unknown tool calls."""
        provider = MockProvider()
        agent = Agent(provider=provider, model="test-model")

        # No tools added

        # Mock provider response with unknown tool
        tool_call = Mock()
        tool_call.name = "unknown_tool"
        tool_call.id = "unknown_call"
        tool_call.arguments = {}
        provider.add_response("Using unknown tool.", [tool_call])
        provider.add_response("The tool was not found.")

        # Run agent
        response = await agent.run_async("Use unknown tool")

        # Check error handling
        assert "not found" in response.content.lower() or "error" in response.content.lower()

    @pytest.mark.asyncio
    async def test_invalid_arguments(self):
        """Test agent handling invalid tool arguments."""
        provider = MockProvider()
        agent = Agent(provider=provider, model="test-model", tools=[self.tools["test_add"]])

        # Mock provider response with invalid arguments
        tool_call = Mock()
        tool_call.name = "test_add"
        tool_call.id = "invalid_args"
        tool_call.arguments = {"a": "not_a_number", "b": 5}  # Invalid type
        provider.add_response("Adding values.", [tool_call])
        provider.add_response("There was an error with the arguments.")

        # Run agent
        response = await agent.run_async("Add invalid values")

        # Should handle the error gracefully
        assert "error" in response.content.lower() or "invalid" in response.content.lower()

    @pytest.mark.asyncio
    async def test_conversation_history_with_tools(self):
        """Test that tool results are included in conversation history."""
        provider = MockProvider()
        agent = Agent(provider=provider, model="test-model", tools=[self.tools["test_add"]])

        # First interaction
        tool_call1 = Mock()
        tool_call1.name = "test_add"
        tool_call1.id = "call1"
        tool_call1.arguments = {"a": 1, "b": 2}
        provider.add_response("Adding 1 and 2.", [tool_call1])
        provider.add_response("1 + 2 = 3")

        await agent.run_async("Add 1 and 2")

        # Second interaction should have access to history
        tool_call2 = Mock()
        tool_call2.name = "test_add"
        tool_call2.id = "call2"
        tool_call2.arguments = {"a": 3, "b": 4}
        provider.add_response("Now adding 3 and 4.", [tool_call2])
        provider.add_response("3 + 4 = 7. Previously we calculated 1 + 2 = 3.")

        await agent.run_async("Now add 3 and 4")

        # Check that provider received conversation history
        second_call = provider.called_with[1]
        messages = second_call["messages"]

        # Should include previous user message, assistant response, and tool results
        assert len(messages) > 2
        assert any("1" in str(msg) and "2" in str(msg) for msg in messages)

    @pytest.mark.asyncio
    async def test_parallel_tool_execution(self):
        """Test agent executing multiple tools in parallel."""
        provider = MockProvider()
        agent = Agent(
            provider=provider,
            model="test-model",
            tools=[
                self.tools["test_add"],
                self.tools["test_multiply"],
                self.tools["test_async_operation"],
            ],
        )

        # Mock provider response with multiple tool calls
        calls = [
            Mock(name="test_add", id="c1", arguments={"a": 1, "b": 2}),
            Mock(name="test_multiply", id="c2", arguments={"x": 3, "y": 4}),
            Mock(name="test_async_operation", id="c3", arguments={"value": "test"}),
        ]

        provider.add_response("Executing multiple operations.", calls)
        provider.add_response("All operations completed successfully.")

        # Run agent
        response = await agent.run_async("Do multiple calculations at once")

        # Check all operations completed
        assert "completed" in response.content or "successfully" in response.content.lower()
        # Verify multiple tools were called
        assert len(provider.called_with) == 2
