"""Tool conversion utilities for different provider formats."""

import json
from typing import Any

from .base import Tool, ToolCall


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
        # Ollama uses the same format as OpenAI
        return ToolConverter.to_openai(tools)

    @staticmethod
    def to_cohere(tools: list[Tool] | None) -> tuple[list[Any], dict[str, str]]:
        """
        Convert standard tools to Cohere format.

        Args:
            tools: List of Tool objects

        Returns:
            Tuple of (cohere_tools, name_mapping) where name_mapping maps
            sanitized names back to original names
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
                for param_name, param_schema in tool.parameters["properties"].items():
                    # Convert type to uppercase as required by Cohere
                    param_type = param_schema.get("type", "string").upper()
                    if param_type == "INTEGER":
                        param_type = "FLOAT"  # Cohere uses FLOAT for numbers
                    elif param_type == "ARRAY":
                        param_type = "LIST"
                    elif param_type == "OBJECT":
                        param_type = "DICT"

                    param_def = CohereParameterDefinition(
                        description=param_schema.get("description", ""),
                        type=param_type,
                        is_required=param_name in tool.parameters.get("required", []),
                    )
                    param_definitions[param_name] = param_def

            # Sanitize tool name for OCI/Cohere compatibility (dots and hyphens not allowed)
            sanitized_name = tool.name.replace(".", "_").replace("-", "_")
            name_mapping[sanitized_name] = tool.name

            cohere_tool = CohereTool(
                name=sanitized_name,
                description=tool.description,
                parameter_definitions=param_definitions,
            )
            cohere_tools.append(cohere_tool)

        return cohere_tools, name_mapping

    @staticmethod
    def to_meta(tools: list[Tool] | None) -> list[Any] | None:
        """
        Convert standard tools to Meta format.

        Args:
            tools: List of Tool objects

        Returns:
            List of tools in Meta format, or None if no tools
        """
        if not tools:
            return None

        # Import Meta types only when needed
        from oci.generative_ai_inference.models import FunctionDefinition

        meta_tools = []

        for tool in tools:
            # Convert to Meta's FunctionDefinition format
            params = {"type": "object", "properties": {}, "required": []}

            if "properties" in tool.parameters:
                params["properties"] = tool.parameters["properties"]
            if "required" in tool.parameters:
                params["required"] = tool.parameters["required"]

            meta_tool = FunctionDefinition(
                name=tool.name, description=tool.description, parameters=params
            )
            meta_tools.append(meta_tool)

        return meta_tools

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
