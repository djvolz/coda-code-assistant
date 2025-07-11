"""Tool executor for running MCP tools based on AI requests."""

import json

from coda.base.providers.base import Tool, ToolCall, ToolResult

from .base import tool_registry


class ToolExecutor:
    """Executes tools based on AI tool call requests."""

    def __init__(self):
        """Initialize the tool executor."""
        self.tool_registry = tool_registry

    async def execute_tool_call(self, tool_call: ToolCall) -> ToolResult:
        """
        Execute a single tool call.

        Args:
            tool_call: The tool call request from the AI

        Returns:
            ToolResult with the execution result
        """
        try:
            # Get the tool
            tool = self.tool_registry.get_tool(tool_call.name)
            if not tool:
                from ..errors import ToolNotFoundError

                error = ToolNotFoundError(tool_call.name)
                return ToolResult(
                    tool_call_id=tool_call.id,
                    content=error.user_message(),
                    is_error=True,
                )

            # Check if tool requires approval (dangerous tools)
            if hasattr(tool, "dangerous") and tool.dangerous:
                from ..errors import PermissionError

                # For now, we'll reject dangerous tools in automatic mode
                # In the future, we can add user approval flow
                error = PermissionError(
                    message=f"Tool '{tool_call.name}' requires manual approval",
                    operation="execute_dangerous_tool",
                    resource=tool_call.name,
                )
                return ToolResult(
                    tool_call_id=tool_call.id,
                    content=error.user_message(),
                    is_error=True,
                )

            # Execute the tool
            result = await tool.execute(tool_call.arguments)

            # Format the result
            if result.success:
                content = result.output
                if isinstance(content, dict):
                    content = json.dumps(content, indent=2)
                elif not isinstance(content, str):
                    content = str(content)

                return ToolResult(tool_call_id=tool_call.id, content=content, is_error=False)
            else:
                return ToolResult(
                    tool_call_id=tool_call.id, content=f"Error: {result.error}", is_error=True
                )

        except Exception as e:
            from ..errors import ToolExecutionError

            # Create proper error with context
            error = ToolExecutionError(message=str(e), tool_name=tool_call.name, cause=e)

            return ToolResult(
                tool_call_id=tool_call.id, content=error.user_message(), is_error=True
            )

    def get_available_tools(self) -> list[Tool]:
        """
        Get list of available tools in provider format.

        Returns:
            List of Tool objects for the provider
        """
        tools = []

        for tool in self.tool_registry.list_tools():
            # Convert MCP tool to provider Tool format
            parameters = {"type": "object", "properties": {}, "required": []}

            # Convert tool parameters to JSON Schema format
            for param_name, param_info in tool.parameters.items():
                param_schema = {
                    "type": param_info.type.value,  # Get enum value
                    "description": param_info.description,
                }

                # Add additional schema properties if available
                if param_info.enum:
                    param_schema["enum"] = param_info.enum
                if param_info.default is not None:
                    param_schema["default"] = param_info.default

                parameters["properties"][param_name] = param_schema

                if param_info.required:
                    parameters["required"].append(param_name)

            provider_tool = Tool(
                name=tool.name, description=tool.description, parameters=parameters
            )
            tools.append(provider_tool)

        return tools

    def format_tools_for_ai(self) -> str:
        """
        Format available tools as a string for AI context.

        Returns:
            Formatted string describing available tools
        """
        tools = self.tool_registry.list_tools()
        if not tools:
            return "No tools are currently available."

        lines = ["Available tools:"]
        for tool in tools:
            lines.append(f"\n- {tool.name}: {tool.description}")
            if tool.parameters:
                lines.append("  Parameters:")
                for param_name, param_info in tool.parameters.items():
                    required = " (required)" if param_info.get("required", False) else ""
                    lines.append(
                        f"    - {param_name}: {param_info['type']}{required} - {param_info.get('description', '')}"
                    )

        return "\n".join(lines)
