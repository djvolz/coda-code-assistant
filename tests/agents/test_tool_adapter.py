"""Unit tests for MCP tool adapter."""

import json
from unittest.mock import Mock, patch

import pytest

from coda.agents.function_tool import FunctionTool
from coda.agents.tool_adapter import MCPToolAdapter
from coda.tools.base import BaseTool, ToolParameter, ToolParameterType, ToolResult, ToolSchema


class MockMCPTool(BaseTool):
    """Mock MCP tool for testing."""

    def __init__(self, name="mock_tool", params=None):
        self.name = name
        self._params = params or {}
        self._execute_result = ToolResult(
            success=True, result={"message": "Success"}, tool=name, server="mock"
        )
        super().__init__()

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=f"Mock tool {self.name}",
            category="test",
            server="mock",
            parameters=self._params,
        )

    async def execute(self, arguments: dict) -> ToolResult:
        return self._execute_result

    def set_result(self, result: ToolResult):
        """Set the result for testing."""
        self._execute_result = result


class TestMCPToolAdapter:
    """Test the MCPToolAdapter class."""

    def test_convert_simple_mcp_tool(self):
        """Test converting a simple MCP tool."""
        # Create mock MCP tool
        mcp_tool = MockMCPTool("simple_tool")

        # Convert to FunctionTool
        func_tool = MCPToolAdapter.convert_mcp_tool(mcp_tool)

        assert isinstance(func_tool, FunctionTool)
        assert func_tool.name == "simple_tool"
        assert func_tool.description == "Mock tool simple_tool"
        assert callable(func_tool.callable)

    def test_convert_tool_with_parameters(self):
        """Test converting MCP tool with parameters."""
        # Create MCP tool with parameters
        params = {
            "text": ToolParameter(
                type=ToolParameterType.STRING, description="Input text", required=True
            ),
            "count": ToolParameter(
                type=ToolParameterType.INTEGER, description="Count value", required=False, default=1
            ),
        }
        mcp_tool = MockMCPTool("param_tool", params)

        # Convert
        func_tool = MCPToolAdapter.convert_mcp_tool(mcp_tool)

        # Check parameters conversion
        assert func_tool.parameters["type"] == "object"
        assert "text" in func_tool.parameters["properties"]
        assert "count" in func_tool.parameters["properties"]
        assert func_tool.parameters["properties"]["text"]["type"] == "string"
        assert func_tool.parameters["properties"]["count"]["type"] == "integer"
        assert func_tool.parameters["required"] == ["text"]

    def test_parameter_constraints_conversion(self):
        """Test conversion of parameter constraints."""
        params = {
            "limited_string": ToolParameter(
                type=ToolParameterType.STRING,
                description="Limited string",
                minLength=5,
                maxLength=20,
                required=True,
            ),
            "limited_number": ToolParameter(
                type=ToolParameterType.NUMBER,
                description="Limited number",
                minimum=0,
                maximum=100,
                required=True,
            ),
            "choice": ToolParameter(
                type=ToolParameterType.STRING,
                description="Choice parameter",
                enum=["option1", "option2", "option3"],
                required=True,
            ),
        }
        mcp_tool = MockMCPTool("constrained_tool", params)

        func_tool = MCPToolAdapter.convert_mcp_tool(mcp_tool)
        props = func_tool.parameters["properties"]

        # Check string constraints
        assert props["limited_string"]["minLength"] == 5
        assert props["limited_string"]["maxLength"] == 20

        # Check number constraints
        assert props["limited_number"]["minimum"] == 0
        assert props["limited_number"]["maximum"] == 100

        # Check enum
        assert props["choice"]["enum"] == ["option1", "option2", "option3"]

    @pytest.mark.asyncio
    async def test_wrapper_execution_success(self):
        """Test successful execution through wrapper."""
        mcp_tool = MockMCPTool("exec_tool")
        mcp_tool.set_result(
            ToolResult(success=True, result={"data": "test_value"}, tool="exec_tool", server="mock")
        )

        func_tool = MCPToolAdapter.convert_mcp_tool(mcp_tool)

        # Execute through wrapper
        result = await func_tool.execute({"param": "value"})

        # Should return JSON string
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["data"] == "test_value"

    @pytest.mark.asyncio
    async def test_wrapper_execution_string_result(self):
        """Test execution with string result."""
        mcp_tool = MockMCPTool("string_tool")
        mcp_tool.set_result(
            ToolResult(
                success=True, result="Simple string result", tool="string_tool", server="mock"
            )
        )

        func_tool = MCPToolAdapter.convert_mcp_tool(mcp_tool)
        result = await func_tool.execute({})

        assert result == "Simple string result"

    @pytest.mark.asyncio
    async def test_wrapper_execution_error(self):
        """Test execution with error."""
        mcp_tool = MockMCPTool("error_tool")
        mcp_tool.set_result(
            ToolResult(
                success=False, error="Something went wrong", tool="error_tool", server="mock"
            )
        )

        func_tool = MCPToolAdapter.convert_mcp_tool(mcp_tool)
        result = await func_tool.execute({})

        assert result == "Error: Something went wrong"

    @pytest.mark.asyncio
    async def test_wrapper_execution_non_json_result(self):
        """Test execution with non-JSON-serializable result."""
        mcp_tool = MockMCPTool("object_tool")
        mcp_tool.set_result(
            ToolResult(
                success=True,
                result=12345,  # Integer result
                tool="object_tool",
                server="mock",
            )
        )

        func_tool = MCPToolAdapter.convert_mcp_tool(mcp_tool)
        result = await func_tool.execute({})

        assert result == "12345"

    def test_convert_mcp_parameters_all_types(self):
        """Test conversion of all parameter types."""
        params = {
            "string_param": ToolParameter(type=ToolParameterType.STRING, description="String"),
            "int_param": ToolParameter(type=ToolParameterType.INTEGER, description="Integer"),
            "num_param": ToolParameter(type=ToolParameterType.NUMBER, description="Number"),
            "bool_param": ToolParameter(type=ToolParameterType.BOOLEAN, description="Boolean"),
            "array_param": ToolParameter(type=ToolParameterType.ARRAY, description="Array"),
            "object_param": ToolParameter(type=ToolParameterType.OBJECT, description="Object"),
        }

        result = MCPToolAdapter._convert_mcp_parameters(params)

        assert result["type"] == "object"
        props = result["properties"]
        assert props["string_param"]["type"] == "string"
        assert props["int_param"]["type"] == "integer"
        assert props["num_param"]["type"] == "number"
        assert props["bool_param"]["type"] == "boolean"
        assert props["array_param"]["type"] == "array"
        assert props["object_param"]["type"] == "object"

    def test_get_all_tools_empty_registry(self):
        """Test getting all tools with empty registry."""
        with patch("coda.agents.tool_adapter.tool_registry") as mock_registry:
            mock_registry.tools = {}

            tools = MCPToolAdapter.get_all_tools()
            assert tools == []

    def test_get_all_tools_with_tools(self):
        """Test getting all tools from registry."""
        mock_tools = {
            "tool1": MockMCPTool("tool1"),
            "tool2": MockMCPTool("tool2"),
            "tool3": MockMCPTool("tool3"),
        }

        with patch("coda.agents.tool_adapter.tool_registry") as mock_registry:
            mock_registry.tools = mock_tools

            tools = MCPToolAdapter.get_all_tools()

            assert len(tools) == 3
            assert all(isinstance(tool, FunctionTool) for tool in tools)
            tool_names = {tool.name for tool in tools}
            assert tool_names == {"tool1", "tool2", "tool3"}

    def test_get_all_tools_with_conversion_error(self, capsys):
        """Test handling of conversion errors."""
        # Create a tool that will fail conversion
        bad_tool = Mock(spec=BaseTool)
        bad_tool.get_schema.side_effect = Exception("Schema error")

        mock_tools = {
            "good_tool": MockMCPTool("good_tool"),
            "bad_tool": bad_tool,
            "another_good": MockMCPTool("another_good"),
        }

        with patch("coda.agents.tool_adapter.tool_registry") as mock_registry:
            mock_registry.tools = mock_tools

            tools = MCPToolAdapter.get_all_tools()

            # Should get only the good tools
            assert len(tools) == 2
            tool_names = {tool.name for tool in tools}
            assert tool_names == {"good_tool", "another_good"}

            # Check warning was printed
            captured = capsys.readouterr()
            assert "Warning: Failed to convert tool bad_tool" in captured.out

    def test_wrapper_preserves_tool_metadata(self):
        """Test that wrapper function has correct metadata."""
        mcp_tool = MockMCPTool("metadata_tool")
        func_tool = MCPToolAdapter.convert_mcp_tool(mcp_tool)

        # Check that callable has tool metadata
        assert hasattr(func_tool.callable, "_is_tool")
        assert func_tool.callable._is_tool is True
        assert func_tool.callable._tool_name == "metadata_tool"
        assert func_tool.callable._tool_description == "Mock tool metadata_tool"

    @pytest.mark.asyncio
    async def test_wrapper_passes_arguments_correctly(self):
        """Test that wrapper passes arguments to MCP tool correctly."""

        # Create a custom MCP tool that records arguments
        class ArgumentRecordingTool(MockMCPTool):
            def __init__(self):
                super().__init__("arg_recorder")
                self.received_args = None

            async def execute(self, arguments: dict) -> ToolResult:
                self.received_args = arguments.copy()  # Make a copy
                return self._execute_result

        mcp_tool = ArgumentRecordingTool()

        # Add parameters to the tool so they get passed through
        mcp_tool._params = {
            "key1": ToolParameter(type=ToolParameterType.STRING, description="Key 1"),
            "key2": ToolParameter(type=ToolParameterType.INTEGER, description="Key 2"),
        }

        func_tool = MCPToolAdapter.convert_mcp_tool(mcp_tool)

        test_args = {"key1": "value1", "key2": 42}
        await func_tool.execute(test_args)

        assert mcp_tool.received_args == test_args

    def test_complex_nested_parameters(self):
        """Test conversion of complex nested parameter structures."""
        params = {
            "config": ToolParameter(
                type=ToolParameterType.OBJECT, description="Configuration object", required=True
            ),
            "items": ToolParameter(
                type=ToolParameterType.ARRAY, description="Array of items", required=False
            ),
        }

        mcp_tool = MockMCPTool("complex_tool", params)
        func_tool = MCPToolAdapter.convert_mcp_tool(mcp_tool)

        props = func_tool.parameters["properties"]
        assert props["config"]["type"] == "object"
        assert props["items"]["type"] == "array"
        assert func_tool.parameters["required"] == ["config"]
