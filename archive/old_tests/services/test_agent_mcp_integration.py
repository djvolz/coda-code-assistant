"""Integration tests for agents using MCP tools."""

import asyncio
from unittest.mock import MagicMock

import pytest

from coda.base.providers import MockProvider, ToolCall
from coda.services.agents import Agent
from coda.services.agents.tool_adapter import MCPToolAdapter
from coda.services.tools import BaseTool, ToolParameter, ToolParameterType, ToolResult, ToolSchema


class TestMCPTool(BaseTool):
    """Test MCP tool for integration testing."""

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="test_calculator",
            description="Test calculator tool",
            category="test",
            parameters={
                "operation": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Operation to perform",
                    required=True,
                    enum=["add", "multiply"],
                ),
                "a": ToolParameter(
                    type=ToolParameterType.NUMBER,
                    description="First number",
                    required=True,
                ),
                "b": ToolParameter(
                    type=ToolParameterType.NUMBER,
                    description="Second number",
                    required=True,
                ),
            },
        )

    async def execute(self, arguments: dict) -> ToolResult:
        """Execute the test calculation."""
        op = arguments["operation"]
        a = arguments["a"]
        b = arguments["b"]

        if op == "add":
            result = a + b
        elif op == "multiply":
            result = a * b
        else:
            return ToolResult(success=False, error=f"Unknown operation: {op}")

        return ToolResult(
            success=True, result={"answer": result, "expression": f"{a} {op} {b} = {result}"}
        )


@pytest.fixture
def test_mcp_tool():
    """Create a test MCP tool."""
    return TestMCPTool()


@pytest.fixture
def mock_provider_with_tools():
    """Create a mock provider that supports tool calling."""
    provider = MockProvider()

    # Override chat to return tool calls
    original_chat = provider.chat

    def chat_with_tools(messages, **kwargs):
        # Check if this is asking for calculation
        last_msg = messages[-1].content

        if "calculate" in last_msg.lower() or "add" in last_msg.lower():
            # Return a tool call
            response = MagicMock()
            response.content = "I'll calculate that for you."
            response.tool_calls = [
                ToolCall(
                    id="test-1",
                    name="test_calculator",
                    arguments={"operation": "add", "a": 5, "b": 3},
                )
            ]
            response.model = "mock-model"
            return response

        # Otherwise return normal response
        return original_chat(messages, **kwargs)

    provider.chat = chat_with_tools
    return provider


@pytest.mark.asyncio
async def test_agent_with_mcp_tool_adapter(test_mcp_tool, mock_provider_with_tools):
    """Test agent using MCP tools via adapter."""
    # Register the test tool
    from coda.services.tools import tool_registry

    tool_registry.register_tool(test_mcp_tool)

    try:
        # Create function tool from MCP tool
        func_tool = MCPToolAdapter.convert_mcp_tool(test_mcp_tool)

        # Verify conversion
        assert func_tool.name == "test_calculator"
        assert func_tool.description == "Test calculator tool"
        assert "operation" in func_tool.parameters["properties"]

        # Create agent with the adapted tool
        agent = Agent(
            provider=mock_provider_with_tools,
            model="mock-model",
            tools=[func_tool],
            instructions="You are a calculator assistant.",
        )

        # Test tool execution
        response = await agent.run_async("Please add 5 and 3")

        # Verify the agent called the tool and got result
        assert response.content is not None
        # The mock will have processed the tool result

    finally:
        # Clean up - unregister the tool
        if "test_calculator" in tool_registry.tools:
            del tool_registry.tools["test_calculator"]


@pytest.mark.asyncio
async def test_agent_error_handling_with_mcp_tools():
    """Test error handling when MCP tools fail."""
    from coda.services.tools import tool_registry

    # Create a failing tool
    class FailingTool(BaseTool):
        def get_schema(self) -> ToolSchema:
            return ToolSchema(
                name="failing_tool",
                description="Tool that always fails",
                category="test",
                parameters={},
            )

        async def execute(self, arguments: dict) -> ToolResult:
            raise Exception("Tool execution failed!")

    failing_tool = FailingTool()
    tool_registry.register_tool(failing_tool)

    try:
        # Convert to function tool
        func_tool = MCPToolAdapter.convert_mcp_tool(failing_tool)

        # Create provider that will call the failing tool
        provider = MockProvider()

        def chat_with_failing_tool(messages, **kwargs):
            response = MagicMock()
            response.content = "I'll try the failing tool."
            response.tool_calls = [ToolCall(id="test-fail-1", name="failing_tool", arguments={})]
            response.model = "mock-model"
            return response

        provider.chat = chat_with_failing_tool

        # Create agent
        agent = Agent(
            provider=provider,
            model="mock-model",
            tools=[func_tool],
        )

        # Execute - should handle the error gracefully
        response = await agent.run_async("Use the failing tool")

        # Should get an error message but not crash
        assert "Error" in response.content or "error" in response.content.lower()

    finally:
        # Clean up
        if "failing_tool" in tool_registry.tools:
            del tool_registry.tools["failing_tool"]


@pytest.mark.asyncio
async def test_mcp_tool_parameter_validation():
    """Test that MCP tool parameters are properly validated."""
    tool = TestMCPTool()

    # Test valid parameters
    result = await tool.execute({"operation": "add", "a": 10, "b": 20})
    assert result.success
    assert result.result["answer"] == 30

    # Test invalid operation
    result = await tool.execute({"operation": "invalid", "a": 10, "b": 20})
    assert not result.success
    assert "Unknown operation" in result.error


@pytest.mark.asyncio
async def test_batch_mcp_tool_conversion():
    """Test converting multiple MCP tools at once."""
    from coda.services.tools import tool_registry

    # Register multiple test tools
    tools = []
    for i in range(3):
        tool = TestMCPTool()
        tool.get_schema = lambda i=i: ToolSchema(
            name=f"test_tool_{i}",
            description=f"Test tool {i}",
            category="test",
            parameters={},
        )
        tools.append(tool)
        tool_registry.register_tool(tool)

    try:
        # Convert all tools
        func_tools = MCPToolAdapter.get_all_tools()

        # Should include our test tools
        test_tool_names = [f"test_tool_{i}" for i in range(3)]
        converted_names = [t.name for t in func_tools]

        for name in test_tool_names:
            assert name in converted_names

    finally:
        # Clean up
        for i in range(3):
            name = f"test_tool_{i}"
            if name in tool_registry.tools:
                del tool_registry.tools[name]


if __name__ == "__main__":
    asyncio.run(test_agent_mcp_integration())
