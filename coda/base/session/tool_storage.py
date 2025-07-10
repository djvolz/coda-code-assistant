"""Tool call storage utilities for session management."""

from typing import Any


def format_tool_calls_for_storage(tool_calls: list[Any]) -> list[dict]:
    """Format tool calls for database storage.

    Args:
        tool_calls: List of tool call objects from provider

    Returns:
        List of dictionaries suitable for JSON storage
    """
    if not tool_calls:
        return []

    formatted_calls = []
    for call in tool_calls:
        # Handle different tool call formats
        if hasattr(call, "__dict__"):
            # Object with attributes
            formatted_call = {
                "id": getattr(call, "id", None),
                "name": getattr(call, "name", None),
                "arguments": getattr(call, "arguments", {}),
            }
        elif isinstance(call, dict):
            # Already a dictionary
            formatted_call = {
                "id": call.get("id"),
                "name": call.get("name"),
                "arguments": call.get("arguments", {}),
            }
        else:
            # Unknown format, store as string
            formatted_call = {"raw": str(call)}

        formatted_calls.append(formatted_call)

    return formatted_calls


def format_tool_result_for_storage(tool_result: Any) -> dict:
    """Format a tool execution result for storage.

    Args:
        tool_result: Tool execution result

    Returns:
        Dictionary suitable for JSON storage
    """
    if hasattr(tool_result, "__dict__"):
        return {
            "tool_call_id": getattr(tool_result, "tool_call_id", None),
            "content": getattr(tool_result, "content", str(tool_result)),
            "is_error": getattr(tool_result, "is_error", False),
        }
    elif isinstance(tool_result, dict):
        return {
            "tool_call_id": tool_result.get("tool_call_id"),
            "content": tool_result.get("content", str(tool_result)),
            "is_error": tool_result.get("is_error", False),
        }
    else:
        return {"content": str(tool_result)}
