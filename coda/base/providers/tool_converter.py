"""Tool conversion utilities for different provider formats."""

import json
from typing import Any

from .base import Tool, ToolCall

# Mapping of JSON schema types to OCI/Cohere parameter types
JSON_TO_OCI_TYPES = {
    "string": "STRING",
    "number": "FLOAT",
    "boolean": "BOOLEAN",
    "integer": "FLOAT",  # OCI Cohere uses FLOAT for all numbers
    "array": "LIST",
    "object": "DICT",
}


class ToolConverter:
    """Utility class for converting tools between different provider formats."""

    @staticmethod
    def to_openai(tools: list[Tool] | None) -> list[dict] | None:
        """
        Convert standard tools to OpenAI format.

        Args:
            tools: List of Tool objects

        Returns:
            List of tools in OpenAI format, or None if no tools
        """
        if not tools:
            return None

        openai_tools = []
        for tool in tools:
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,  # Already in JSON Schema format
                },
            }
            openai_tools.append(openai_tool)

        return openai_tools

    @staticmethod
    def to_ollama(tools: list[Tool] | None) -> list[dict] | None:
        """
        Convert standard tools to Ollama format.

        Args:
            tools: List of Tool objects

        Returns:
            List of tools in Ollama format, or None if no tools
        """
        # Ollama uses the same generic format as OpenAI
        return ToolConverter.to_generic(tools)

    @staticmethod
    def to_oci_generic(tools: list[Tool] | None) -> list[Any] | None:
        """
        Convert standard tools to OCI generic format (FunctionDefinition objects).

        Used for Meta, XAI, and other non-Cohere models in OCI GenAI.

        Args:
            tools: List of Tool objects

        Returns:
            List of OCI FunctionDefinition objects, or None if no tools

        Raises:
            ValueError: If tool conversion fails
        """
        if not tools:
            return None

        # Import OCI types only when needed
        from oci.generative_ai_inference.models import FunctionDefinition

        oci_tools = []
        seen_names = set()  # Track names to prevent duplicates

        for tool in tools:
            # Skip duplicates
            if tool.name in seen_names:
                continue
            seen_names.add(tool.name)

            try:
                # Convert to OCI FunctionDefinition format using proper JSON schema
                parameters = {
                    "type": "object",
                    "properties": tool.parameters.get("properties", {}),
                    "required": tool.parameters.get("required", []),
                }

                oci_tool = FunctionDefinition(
                    name=tool.name,
                    description=tool.description
                    or f"Tool: {tool.name}",  # Ensure description exists
                    parameters=parameters,
                )
                oci_tools.append(oci_tool)
            except Exception as e:
                raise ValueError(
                    f"Failed to convert tool '{tool.name}' to OCI generic format: {e}"
                ) from e

        return oci_tools

    @staticmethod
    def to_meta(tools: list[Tool] | None) -> list[Any] | None:
        """
        Convert standard tools to Meta format.

        Alias for to_oci_generic for backward compatibility.
        """
        return ToolConverter.to_oci_generic(tools)

    @staticmethod
    def to_cohere(tools: list[Tool] | None) -> tuple[list[Any], dict[str, str]]:
        """
        Convert standard tools to Cohere format.

        Args:
            tools: List of Tool objects

        Returns:
            Tuple of (cohere_tools, name_mapping) where name_mapping maps
            sanitized names back to original names

        Raises:
            ValueError: If tool conversion fails
        """
        if not tools:
            return [], {}

        # Import Cohere types only when needed
        from oci.generative_ai_inference.models import (
            CohereParameterDefinition,
            CohereTool,
        )

        cohere_tools = []
        name_mapping = {}  # Maps sanitized names to original names

        for tool in tools:
            # Convert parameters from JSON Schema to Cohere format
            param_definitions = {}

            if "properties" in tool.parameters:
                properties = tool.parameters["properties"]
                required_params = tool.parameters.get("required", [])

                for param_name, param_schema in properties.items():
                    # Use the mapping for consistent type conversion
                    json_type = param_schema.get("type", "string")
                    param_type = JSON_TO_OCI_TYPES.get(json_type, "STRING")

                    # Handle special cases for better OCI compatibility
                    if json_type == "integer":
                        # OCI Cohere treats all numbers as FLOAT
                        param_type = "FLOAT"

                    param_def = CohereParameterDefinition(
                        description=param_schema.get("description", ""),
                        type=param_type,
                        is_required=param_name in required_params,
                    )
                    param_definitions[param_name] = param_def

            # Sanitize tool name for OCI/Cohere compatibility (dots and hyphens not allowed)
            # Also ensure name is valid identifier
            sanitized_name = tool.name.replace(".", "_").replace("-", "_")
            # Remove any other invalid characters for OCI
            sanitized_name = "".join(c if c.isalnum() or c == "_" else "_" for c in sanitized_name)
            name_mapping[sanitized_name] = tool.name

            try:
                cohere_tool = CohereTool(
                    name=sanitized_name,
                    description=tool.description
                    or f"Tool: {tool.name}",  # Ensure description exists
                    parameter_definitions=param_definitions,
                )
                cohere_tools.append(cohere_tool)
            except Exception as e:
                raise ValueError(
                    f"Failed to convert tool '{tool.name}' to Cohere format: {e}"
                ) from e

        return cohere_tools, name_mapping

    @staticmethod
    def to_generic(tools: list[Tool] | None) -> list[dict] | None:
        """
        Convert standard tools to generic OpenAI-compatible format.

        This works for most providers including Meta, OpenAI, Anthropic, etc.
        Only Cohere needs special handling.

        Args:
            tools: List of Tool objects

        Returns:
            List of tools in generic format, or None if no tools
        """
        # Generic format is same as OpenAI format
        return ToolConverter.to_openai(tools)

    @staticmethod
    def parse_tool_calls_ollama(message: dict) -> list[ToolCall] | None:
        """
        Parse tool calls from Ollama response message.

        Args:
            message: Response message from Ollama

        Returns:
            List of ToolCall objects, or None if no tool calls
        """
        tool_calls = message.get("tool_calls", [])
        if not tool_calls:
            return None

        parsed_calls = []
        for call in tool_calls:
            # Handle different tool call formats
            if isinstance(call, dict):
                function_info = call.get("function", {})
                tool_call = ToolCall(
                    id=call.get("id", f"call_{len(parsed_calls)}"),
                    name=function_info.get("name", ""),
                    arguments=function_info.get("arguments", {}),
                )
                # Handle arguments as string (need to parse JSON)
                if isinstance(tool_call.arguments, str):
                    try:
                        tool_call.arguments = json.loads(tool_call.arguments)
                    except json.JSONDecodeError:
                        tool_call.arguments = {}

                parsed_calls.append(tool_call)

        return parsed_calls if parsed_calls else None

    @staticmethod
    def parse_tool_calls_cohere(
        tool_calls: list, name_mapping: dict[str, str]
    ) -> list[ToolCall] | None:
        """
        Parse tool calls from Cohere response.

        Args:
            tool_calls: Tool calls from Cohere response
            name_mapping: Mapping from sanitized names to original names

        Returns:
            List of ToolCall objects, or None if no tool calls
        """
        if not tool_calls:
            return None

        parsed_calls = []
        for tc in tool_calls:
            # Map sanitized name back to original name
            original_name = name_mapping.get(tc.name, tc.name)
            tool_call = ToolCall(
                id=tc.name,  # Cohere doesn't provide IDs, use name
                name=original_name,
                arguments=tc.parameters if hasattr(tc, "parameters") else {},
            )
            parsed_calls.append(tool_call)

        return parsed_calls
