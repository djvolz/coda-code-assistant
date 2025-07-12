"""Adapter to convert existing MCP tools to agent-compatible tools."""

import json
from typing import Any

from ..tools.base import BaseTool, tool_registry
from .decorators import tool
from .function_tool import FunctionTool


class MCPToolAdapter:
    """Adapts MCP tools for use with agents."""

    @staticmethod
    def convert_mcp_tool(mcp_tool: BaseTool) -> FunctionTool:
        """
        Convert an MCP tool to a FunctionTool.

        Args:
            mcp_tool: The MCP tool to convert

        Returns:
            FunctionTool that wraps the MCP tool
        """
        schema = mcp_tool.get_schema()

        # Create wrapper function with @tool decorator
        @tool(name=schema.name, description=schema.description)
        async def mcp_wrapper(**kwargs) -> str:
            """Execute the MCP tool."""
            result = await mcp_tool.execute(kwargs)

            if result.success:
                # Return the result as string
                if isinstance(result.result, dict):
                    return json.dumps(result.result, indent=2)
                elif isinstance(result.result, str):
                    return result.result
                else:
                    return str(result.result)
            else:
                # Return error
                return f"Error: {result.error}"

        # Create FunctionTool from wrapper
        func_tool = FunctionTool.from_callable(mcp_wrapper)

        # Override parameters with MCP schema
        func_tool.parameters = MCPToolAdapter._convert_mcp_parameters(schema.parameters)

        return func_tool

    @staticmethod
    def _convert_mcp_parameters(mcp_params: dict[str, Any]) -> dict[str, Any]:
        """Convert MCP parameter format to JSON Schema."""
        json_schema = {"type": "object", "properties": {}, "required": []}

        for param_name, param_info in mcp_params.items():
            # Convert parameter info
            param_schema = {"type": param_info.type.value, "description": param_info.description}

            # Add constraints
            if param_info.enum:
                param_schema["enum"] = param_info.enum
            if param_info.min_value is not None:
                param_schema["minimum"] = param_info.min_value
            if param_info.max_value is not None:
                param_schema["maximum"] = param_info.max_value
            if param_info.min_length is not None:
                param_schema["minLength"] = param_info.min_length
            if param_info.max_length is not None:
                param_schema["maxLength"] = param_info.max_length

            json_schema["properties"][param_name] = param_schema

            # Add to required if needed
            if param_info.required:
                json_schema["required"].append(param_name)

        return json_schema

    @staticmethod
    def get_all_tools() -> list[FunctionTool]:
        """Get all MCP tools as FunctionTools."""
        function_tools = []

        for tool_name, mcp_tool in tool_registry.tools.items():
            try:
                func_tool = MCPToolAdapter.convert_mcp_tool(mcp_tool)
                function_tools.append(func_tool)
            except Exception as e:
                print(f"Warning: Failed to convert tool {tool_name}: {e}")

        return function_tools
