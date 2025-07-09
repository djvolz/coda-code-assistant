"""
Base tool interface for Coda's tool system.

This module defines the abstract base class for all tools and the tool result format.
Tools can be implemented as built-in Python functions or external MCP servers.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ToolParameterType(str, Enum):
    """Supported parameter types for tools."""

    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class ToolParameter(BaseModel):
    """Schema for a tool parameter."""

    type: ToolParameterType
    description: str
    default: Any | None = None
    required: bool = True
    enum: list[Any] | None = None
    min_value: int | float | None = Field(None, alias="minimum")
    max_value: int | float | None = Field(None, alias="maximum")
    min_length: int | None = Field(None, alias="minLength")
    max_length: int | None = Field(None, alias="maxLength")


class ToolSchema(BaseModel):
    """Schema for a tool definition."""

    name: str
    description: str
    category: str = "general"
    server: str = "builtin"  # "builtin" or external server name
    parameters: dict[str, ToolParameter] = {}
    dangerous: bool = False  # Whether tool requires special permissions


class ToolResult(BaseModel):
    """Standard result format for tool execution."""

    success: bool
    result: Any | None = None
    error: str | None = None
    tool: str
    server: str = "builtin"
    metadata: dict[str, Any] = {}  # Additional metadata (execution time, etc.)


class BaseTool(ABC):
    """Abstract base class for all tools."""

    def __init__(self):
        self.schema = self.get_schema()

    @abstractmethod
    def get_schema(self) -> ToolSchema:
        """Return the tool schema definition."""
        pass

    @abstractmethod
    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        """
        Execute the tool with given arguments.

        Args:
            arguments: Dictionary of arguments matching the tool's parameter schema

        Returns:
            ToolResult with success status and result/error
        """
        pass

    def validate_arguments(self, arguments: dict[str, Any]) -> str | None:
        """
        Validate arguments against the tool's parameter schema.

        Returns:
            None if valid, error message if invalid
        """
        schema = self.get_schema()

        # Check required parameters
        for param_name, param_spec in schema.parameters.items():
            if param_spec.required and param_name not in arguments:
                return f"Missing required parameter: {param_name}"

            if param_name in arguments:
                value = arguments[param_name]

                # Type validation
                if param_spec.type == ToolParameterType.STRING and not isinstance(value, str):
                    return f"Parameter {param_name} must be a string"
                elif param_spec.type == ToolParameterType.INTEGER and not isinstance(value, int):
                    return f"Parameter {param_name} must be an integer"
                elif param_spec.type == ToolParameterType.NUMBER and not isinstance(
                    value, int | float
                ):
                    return f"Parameter {param_name} must be a number"
                elif param_spec.type == ToolParameterType.BOOLEAN and not isinstance(value, bool):
                    return f"Parameter {param_name} must be a boolean"

                # Enum validation
                if param_spec.enum and value not in param_spec.enum:
                    return f"Parameter {param_name} must be one of: {param_spec.enum}"

                # Range validation
                if param_spec.min_value is not None and value < param_spec.min_value:
                    return f"Parameter {param_name} must be >= {param_spec.min_value}"
                if param_spec.max_value is not None and value > param_spec.max_value:
                    return f"Parameter {param_name} must be <= {param_spec.max_value}"

                # String length validation
                if param_spec.type == ToolParameterType.STRING:
                    if param_spec.min_length is not None and len(value) < param_spec.min_length:
                        return f"Parameter {param_name} must be at least {param_spec.min_length} characters"
                    if param_spec.max_length is not None and len(value) > param_spec.max_length:
                        return f"Parameter {param_name} must be at most {param_spec.max_length} characters"

        # Check for unknown parameters
        known_params = set(schema.parameters.keys())
        provided_params = set(arguments.keys())
        unknown_params = provided_params - known_params
        if unknown_params:
            return f"Unknown parameters: {', '.join(unknown_params)}"

        return None


class ToolRegistry:
    """Registry for managing available tools."""

    def __init__(self):
        self.tools: dict[str, BaseTool] = {}
        self.categories: dict[str, list[str]] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool."""
        schema = tool.get_schema()
        self.tools[schema.name] = tool

        # Update category index
        if schema.category not in self.categories:
            self.categories[schema.category] = []
        self.categories[schema.category].append(schema.name)

    def get_tool(self, name: str) -> BaseTool | None:
        """Get a tool by name."""
        return self.tools.get(name)

    def list_tools(self, category: str | None = None) -> list[ToolSchema]:
        """List all available tools, optionally filtered by category."""
        if category:
            tool_names = self.categories.get(category, [])
            return [self.tools[name].get_schema() for name in tool_names]
        else:
            return [tool.get_schema() for tool in self.tools.values()]

    def list_categories(self) -> list[str]:
        """List all tool categories."""
        return list(self.categories.keys())

    async def execute_tool(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        """Execute a tool by name."""
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(
                success=False, error=f"Tool '{name}' not found", tool=name, server="unknown"
            )

        # Validate arguments
        error = tool.validate_arguments(arguments)
        if error:
            return ToolResult(success=False, error=error, tool=name, server=tool.schema.server)

        # Execute tool
        try:
            return await tool.execute(arguments)
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Tool execution failed: {str(e)}",
                tool=name,
                server=tool.schema.server,
            )


# Global tool registry instance
tool_registry = ToolRegistry()
