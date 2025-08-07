"""
Common utilities for MCP (Model Context Protocol) operations.

This module provides shared functionality used across different MCP client implementations
to reduce code duplication and ensure consistent behavior.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def format_mcp_error(error: Any, context: str = "") -> str:
    """
    Format MCP error messages consistently.

    Args:
        error: The error object or message
        context: Additional context about where the error occurred

    Returns:
        Formatted error message string
    """
    error_msg = str(error) if error else "Unknown error"
    if context:
        return f"{context}: {error_msg}"
    return error_msg


def extract_tool_content(mcp_result: dict[str, Any]) -> str:
    """
    Extract text content from MCP tool execution result.

    Args:
        mcp_result: Raw result from MCP tool execution

    Returns:
        Extracted text content or string representation of result
    """
    # Handle error responses
    if "error" in mcp_result:
        return f"Error: {mcp_result['error']}"

    # Extract content from MCP response format
    content = mcp_result.get("content", [])
    if content and isinstance(content, list) and len(content) > 0:
        first_content = content[0]
        if isinstance(first_content, dict) and "text" in first_content:
            return first_content["text"]

    # Fallback to string representation
    return str(mcp_result)


def validate_tool_arguments(arguments: dict[str, Any], required_params: list[str]) -> list[str]:
    """
    Validate that required parameters are present in tool arguments.

    Args:
        arguments: Tool arguments to validate
        required_params: List of required parameter names

    Returns:
        List of missing parameter names (empty if all present)
    """
    missing_params = []
    for param in required_params:
        if param not in arguments or arguments[param] is None:
            missing_params.append(param)
    return missing_params


def safe_dict_get(
    data: dict[str, Any], key: str, default: Any = None, expected_type: type = None
) -> Any:
    """
    Safely get value from dictionary with optional type checking.

    Args:
        data: Dictionary to get value from
        key: Key to retrieve
        default: Default value if key not found
        expected_type: Expected type for the value

    Returns:
        Value from dictionary or default
    """
    value = data.get(key, default)

    if expected_type and value is not None and not isinstance(value, expected_type):
        logger.warning(
            f"Expected {expected_type.__name__} for key '{key}', got {type(value).__name__}"
        )
        return default

    return value


def normalize_server_name(name: str) -> str:
    """
    Normalize MCP server name for consistent usage.

    Args:
        name: Raw server name

    Returns:
        Normalized server name (lowercase, no special chars)
    """
    if not name:
        return "unnamed"

    # Convert to lowercase and replace invalid characters
    normalized = name.lower().replace(" ", "_").replace("-", "_")

    # Remove any other special characters
    normalized = "".join(c for c in normalized if c.isalnum() or c == "_")

    return normalized or "unnamed"
