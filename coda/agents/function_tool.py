"""Function tool implementation for agents."""

import asyncio
from collections.abc import Callable
from inspect import Parameter, getdoc, signature
from typing import Any, get_type_hints

from pydantic import BaseModel, Field


class FunctionTool(BaseModel):
    """Represents a callable function with metadata for agent execution."""

    name: str = Field(description="The tool name")
    description: str = Field(description="Tool description")
    parameters: dict[str, Any] = Field(
        default_factory=lambda: {"type": "object", "properties": {}, "required": []},
        description="JSON Schema for parameters",
    )
    callable: Callable = Field(description="The actual function")

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def from_callable(cls, callable_func: Callable) -> "FunctionTool":
        """
        Create a FunctionTool from a callable function.

        Args:
            callable_func: The function to convert (must be decorated with @tool)

        Returns:
            FunctionTool instance

        Raises:
            ValueError: If function is not marked as a tool
        """
        if not hasattr(callable_func, "_is_tool"):
            raise ValueError(
                f"Function {callable_func.__name__} is not marked as a tool. Use @tool decorator."
            )

        # Extract metadata
        name = getattr(callable_func, "_tool_name", callable_func.__name__)
        description = getattr(callable_func, "_tool_description", getdoc(callable_func) or "")

        # Build parameter schema
        parameters = cls._build_parameter_schema(callable_func)

        return cls(
            name=name, description=description, parameters=parameters, callable=callable_func
        )

    async def execute(self, arguments: dict[str, Any]) -> Any:
        """
        Execute the function with given arguments.

        Args:
            arguments: Arguments to pass to the function

        Returns:
            Function result
        """
        # Filter valid arguments
        filtered_args = self._prepare_arguments(arguments)

        # Execute based on function type
        if asyncio.iscoroutinefunction(self.callable):
            result = await self.callable(**filtered_args)
        else:
            result = self.callable(**filtered_args)

        return result

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (excluding callable)."""
        return {"name": self.name, "description": self.description, "parameters": self.parameters}

    def _prepare_arguments(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Clean and filter arguments."""
        # Remove any extra colons or whitespace from keys
        cleaned_args = {key.rstrip(":").strip(): value for key, value in arguments.items()}

        # Only include valid parameters
        valid_params = self.parameters.get("properties", {}).keys()
        return {k: v for k, v in cleaned_args.items() if k in valid_params}

    @staticmethod
    def _build_parameter_schema(callable_func: Callable) -> dict[str, Any]:
        """Build JSON Schema for function parameters."""
        schema = {"type": "object", "properties": {}, "required": []}

        try:
            sig = signature(callable_func)
            type_hints = get_type_hints(callable_func)

            for param_name, param in sig.parameters.items():
                # Skip self, agent parameters
                if param_name in ["self", "agent"]:
                    continue

                # Get type hint
                param_type = type_hints.get(param_name, Any)

                # Convert to JSON Schema type
                json_type = "string"  # default
                if param_type is int:
                    json_type = "integer"
                elif param_type is float:
                    json_type = "number"
                elif param_type is bool:
                    json_type = "boolean"
                elif param_type is list:
                    json_type = "array"
                elif param_type is dict:
                    json_type = "object"

                # Add to properties
                schema["properties"][param_name] = {
                    "type": json_type,
                    "description": f"Parameter {param_name}",
                }

                # Check if required (no default value)
                if param.default == Parameter.empty:
                    schema["required"].append(param_name)

        except Exception:
            pass  # Return basic schema on error

        return schema

    def __eq__(self, other: object) -> bool:
        """Check equality based on name, description, and parameters."""
        if not isinstance(other, FunctionTool):
            return NotImplemented
        return (
            self.name == other.name
            and self.description == other.description
            and self.parameters == other.parameters
        )
