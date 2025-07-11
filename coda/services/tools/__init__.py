"""
Coda Tools - Comprehensive tool system for AI assistant interactions.

This package provides a collection of tools for file operations, shell commands,
web interactions, and Git operations, all built on the Model Context Protocol (MCP).
"""

# Import all tool modules to register them
from . import file_tools as _file_tools  # noqa: F401
from . import git_tools as _git_tools  # noqa: F401
from . import intelligence_tools as _intelligence_tools  # noqa: F401
from . import shell_tools as _shell_tools  # noqa: F401
from . import web_tools as _web_tools  # noqa: F401
from .base import (
    BaseTool,
    ToolParameter,
    ToolParameterType,
    ToolRegistry,
    ToolResult,
    ToolSchema,
    tool_registry,
)

__all__ = [
    "BaseTool",
    "ToolSchema",
    "ToolParameter",
    "ToolParameterType",
    "ToolResult",
    "ToolRegistry",
    "tool_registry",
    "get_available_tools",
    "execute_tool",
    "get_tool_categories",
    "get_tool_info",
    "get_tool_stats",
    "list_tools_by_category",
]


def get_available_tools(category: str = None) -> list:
    """
    Get list of available tools, optionally filtered by category.

    Args:
        category: Optional category filter

    Returns:
        List of tool schemas
    """
    return tool_registry.list_tools(category)


async def execute_tool(name: str, arguments: dict) -> ToolResult:
    """
    Execute a tool by name with given arguments.

    Args:
        name: Tool name
        arguments: Tool arguments

    Returns:
        ToolResult with execution outcome
    """
    return await tool_registry.execute_tool(name, arguments)


def get_tool_categories() -> list:
    """
    Get list of all tool categories.

    Returns:
        List of category names
    """
    return tool_registry.list_categories()


def get_tool_info(name: str) -> dict:
    """
    Get detailed information about a specific tool.

    Args:
        name: Tool name

    Returns:
        Tool information dictionary or None if not found
    """
    tool = tool_registry.get_tool(name)
    if tool:
        schema = tool.get_schema()
        return {
            "name": schema.name,
            "description": schema.description,
            "category": schema.category,
            "server": schema.server,
            "dangerous": schema.dangerous,
            "parameters": {
                param_name: {
                    "type": param.type.value,
                    "description": param.description,
                    "required": param.required,
                    "default": param.default,
                    "enum": param.enum,
                    "min_value": param.min_value,
                    "max_value": param.max_value,
                    "min_length": param.min_length,
                    "max_length": param.max_length,
                }
                for param_name, param in schema.parameters.items()
            },
        }
    return None


def list_tools_by_category() -> dict:
    """
    Get tools organized by category.

    Returns:
        Dictionary with categories as keys and tool lists as values
    """
    categories = {}
    for category in tool_registry.list_categories():
        categories[category] = [tool.name for tool in tool_registry.list_tools(category)]
    return categories


# Tool statistics and management
def get_tool_stats() -> dict:
    """
    Get statistics about available tools.

    Returns:
        Dictionary with tool statistics
    """
    all_tools = tool_registry.list_tools()
    categories = tool_registry.list_categories()

    dangerous_tools = [tool for tool in all_tools if tool.dangerous]

    return {
        "total_tools": len(all_tools),
        "categories": len(categories),
        "dangerous_tools": len(dangerous_tools),
        "tools_by_category": {
            category: len(tool_registry.list_tools(category)) for category in categories
        },
        "category_list": categories,
        "dangerous_tool_names": [tool.name for tool in dangerous_tools],
    }


# Version and compatibility info
__version__ = "1.0.0"
__mcp_version__ = "2025-06-18"  # Supported MCP specification version


def get_version_info() -> dict:
    """Get version and compatibility information."""
    return {
        "tools_version": __version__,
        "mcp_spec_version": __mcp_version__,
        "total_tools": len(tool_registry.list_tools()),
        "categories": tool_registry.list_categories(),
    }
