"""Tests for the Coda Agent system."""

import asyncio
from unittest.mock import Mock, patch

import pytest

from coda.base.providers.base import ChatCompletion, ToolCall
from coda.services.agents import Agent, FunctionTool, tool


# Test tools
@tool(description="Add two numbers")
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@tool(description="Multiply two numbers")
async def multiply(a: int, b: int) -> int:
    """Multiply two numbers asynchronously."""
    await asyncio.sleep(0.01)  # Simulate async work
    return a * b


@tool(name="custom_name", description="Custom tool")
def custom_tool(message: str) -> str:
    """A tool with custom name."""
    return f"Processed: {message}"


def not_a_tool(x: int) -> int:
    """Function without @tool decorator."""
    return x * 2


class TestToolDecorator:
    """Test the @tool decorator."""

    def test_tool_decorator_basic(self):
        """Test basic @tool decorator functionality."""
        assert hasattr(add, "_is_tool")
        assert add._is_tool is True
        assert add._tool_name == "add"
        assert add._tool_description == "Add two numbers"

    def test_tool_decorator_custom(self):
        """Test @tool decorator with custom name and description."""
        assert custom_tool._tool_name == "custom_name"
        assert custom_tool._tool_description == "Custom tool"

    def test_tool_decorator_async(self):
        """Test @tool decorator on async function."""
        assert hasattr(multiply, "_is_tool")
        assert multiply._is_tool is True
        assert asyncio.iscoroutinefunction(multiply)

    def test_function_without_decorator(self):
        """Test that regular functions don't have tool attributes."""
        assert not hasattr(not_a_tool, "_is_tool")


class TestFunctionTool:
    """Test FunctionTool class."""

    def test_from_callable_with_tool(self):
        """Test creating FunctionTool from decorated callable."""
        func_tool = FunctionTool.from_callable(add)

        assert func_tool.name == "add"
        assert func_tool.description == "Add two numbers"
        assert func_tool.callable == add
        assert "a" in func_tool.parameters["properties"]
        assert "b" in func_tool.parameters["properties"]
        assert func_tool.parameters["required"] == ["a", "b"]

    def test_from_callable_without_tool(self):
        """Test creating FunctionTool from non-decorated callable fails."""
        with pytest.raises(ValueError, match="not marked as a tool"):
            FunctionTool.from_callable(not_a_tool)

    @pytest.mark.asyncio
    async def test_execute_sync_tool(self):
        """Test executing a synchronous tool."""
        func_tool = FunctionTool.from_callable(add)
        result = await func_tool.execute({"a": 5, "b": 3})
        assert result == 8

    @pytest.mark.asyncio
    async def test_execute_async_tool(self):
        """Test executing an asynchronous tool."""
        func_tool = FunctionTool.from_callable(multiply)
        result = await func_tool.execute({"a": 4, "b": 7})
        assert result == 28

    def test_to_dict(self):
        """Test converting FunctionTool to dictionary."""
        func_tool = FunctionTool.from_callable(add)
        tool_dict = func_tool.to_dict()

        assert tool_dict["name"] == "add"
        assert tool_dict["description"] == "Add two numbers"
        assert "parameters" in tool_dict
        assert "callable" not in tool_dict  # Should exclude callable


class TestAgent:
    """Test Agent class."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock provider."""
        provider = Mock()
        provider.name = "mock_provider"
        provider.list_models.return_value = [
            Mock(id="test.model", supports_functions=True),
            Mock(id="no-tools.model", supports_functions=False),
        ]
        return provider

    @pytest.fixture
    def mock_console(self):
        """Create a mock console."""
        return Mock()

    def test_agent_initialization(self, mock_provider, mock_console):
        """Test agent initialization."""
        agent = Agent(
            provider=mock_provider,
            model="test.model",
            instructions="Test instructions",
            tools=[add, multiply],
            name="Test Agent",
            console=mock_console,
        )

        assert agent.provider == mock_provider
        assert agent.model == "test.model"
        assert agent.instructions == "Test instructions"
        assert agent.name == "Test Agent"
        assert len(agent._function_tools) == 2
        assert "add" in agent._tool_map
        assert "multiply" in agent._tool_map

    def test_agent_filters_non_tools(self, mock_provider, mock_console):
        """Test that agent filters out non-tool functions."""
        with patch.object(mock_console, "print") as mock_print:
            agent = Agent(
                provider=mock_provider,
                model="test.model",
                tools=[add, not_a_tool],  # Mix of tool and non-tool
                console=mock_console,
            )

            # Should only have one tool
            assert len(agent._function_tools) == 1
            assert "add" in agent._tool_map

            # Should have warned about non-tool
            mock_print.assert_called_once()
            assert "not decorated with @tool" in str(mock_print.call_args)

    @pytest.mark.asyncio
    async def test_agent_run_without_tools(self, mock_provider, mock_console):
        """Test agent run without tool support."""
        # Setup mock response
        mock_provider.chat.return_value = ChatCompletion(
            content="Hello! I can help you.", model="no-tools.model", finish_reason="stop"
        )

        agent = Agent(
            provider=mock_provider, model="no-tools.model", tools=[add], console=mock_console
        )

        response = await agent.run_async("Hello")

        assert response.content == "Hello! I can help you."
        # Should not have passed tools to provider
        mock_provider.chat.assert_called_once()
        call_kwargs = mock_provider.chat.call_args[1]
        assert "tools" not in call_kwargs or call_kwargs["tools"] is None

    @pytest.mark.asyncio
    async def test_agent_run_with_tools(self, mock_provider, mock_console):
        """Test agent run with tool calling."""
        # First response with tool call
        tool_call = ToolCall(id="1", name="add", arguments={"a": 5, "b": 3})
        mock_provider.chat.side_effect = [
            ChatCompletion(
                content="I'll add those numbers for you.",
                model="test.model",
                tool_calls=[tool_call],
            ),
            ChatCompletion(content="The sum of 5 and 3 is 8.", model="test.model"),
        ]

        agent = Agent(provider=mock_provider, model="test.model", tools=[add], console=mock_console)

        response = await agent.run_async("What is 5 + 3?")

        assert "8" in response.content
        assert mock_provider.chat.call_count == 2

        # Verify tool was passed to provider
        first_call = mock_provider.chat.call_args_list[0]
        assert "tools" in first_call[1]
        assert len(first_call[1]["tools"]) == 1
        assert first_call[1]["tools"][0].name == "add"

    @pytest.mark.asyncio
    async def test_agent_tool_error_handling(self, mock_provider, mock_console):
        """Test agent handles tool execution errors."""
        # Tool call for non-existent tool
        tool_call = ToolCall(id="1", name="unknown_tool", arguments={})
        mock_provider.chat.side_effect = [
            ChatCompletion(content="I'll use a tool.", model="test.model", tool_calls=[tool_call]),
            ChatCompletion(content="I couldn't complete that action.", model="test.model"),
        ]

        agent = Agent(provider=mock_provider, model="test.model", tools=[add], console=mock_console)

        response = await agent.run_async("Do something")

        # Should handle error gracefully
        assert response.content == "I couldn't complete that action."

    def test_agent_as_tool(self, mock_provider, mock_console):
        """Test converting agent to tool."""
        agent = Agent(
            provider=mock_provider,
            model="test.model",
            name="Sub Agent",
            description="A helpful sub-agent",
            console=mock_console,
        )

        agent_tool = agent.as_tool()

        assert isinstance(agent_tool, FunctionTool)
        assert agent_tool.name == "Sub Agent"
        assert agent_tool.description == "A helpful sub-agent"
        assert asyncio.iscoroutinefunction(agent_tool.callable)
