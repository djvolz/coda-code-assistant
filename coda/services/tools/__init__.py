"""
Coda Tools - Comprehensive tool system for AI assistant interactions.

This package provides a collection of tools for file operations, shell commands,
web interactions, Git operations, and diagram rendering, all built on the Model Context Protocol (MCP).
"""

import logging

from .base import (
    BaseTool,
    ToolParameter,
    ToolParameterType,
    ToolRegistry,
    ToolResult,
    ToolSchema,
    tool_registry,
)

# ====================================================================
# Tool Module Registration
# ====================================================================
# Import all tool modules to register them (handle missing dependencies gracefully)

_TOOL_MODULES = [
    "diagram_tools",
    "file_tools",
    "git_tools",
    "intelligence_tools",
    "shell_tools",
    "web_tools",
    "semantic_search_tools",
]

for module_name in _TOOL_MODULES:
    try:
        __import__(f"coda.services.tools.{module_name}")
    except ImportError:
        # Optional dependencies may not be available
        pass

# ====================================================================
# Public API
# ====================================================================

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


# ====================================================================
# Tool Management Functions
# ====================================================================


def get_available_tools(category: str | None = None) -> list[ToolSchema]:
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


def get_tool_categories() -> list[str]:
    """
    Get list of all tool categories.

    Returns:
        List of category names
    """
    return tool_registry.list_categories()


def get_tool_info(name: str) -> dict | None:
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


# ====================================================================
# Tool Statistics and Analysis
# ====================================================================


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


# ====================================================================
# MCP (Model Context Protocol) Integration
# ====================================================================


def _initialize_mcp_system() -> None:
    """Initialize the MCP system with proper error handling."""
    logger = logging.getLogger(__name__)

    try:
        from .mcp_manager import init_mcp_manager

        # Initialize MCP manager with the tool registry
        init_mcp_manager(tool_registry)

        # Discover and start MCP servers synchronously during import
        _discover_mcp_servers_sync()

    except ImportError:
        logger.debug("MCP system not available - optional dependency")
    except Exception as e:
        logger.debug(f"MCP initialization failed: {e}")


def _discover_mcp_servers_sync() -> None:
    """Synchronously discover MCP servers during import."""
    import asyncio

    logger = logging.getLogger(__name__)

    try:
        # Check if we're already in an async context
        try:
            asyncio.get_running_loop()
            logger.debug("Skipping MCP discovery during import - async context detected")
            return
        except RuntimeError:
            # No running loop, safe to create one
            pass

        # Create a new event loop for this discovery
        from .mcp_manager import discover_mcp_servers

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Run the discovery
        loop.run_until_complete(discover_mcp_servers())
        logger.info("MCP servers discovered and started during import")

    except Exception as e:
        logger.debug(f"MCP server discovery failed during import: {e}")
    finally:
        # Don't close the loop - keep it for MCP connections
        pass


# Initialize MCP system
_initialize_mcp_system()


# ====================================================================
# Version and Compatibility Information
# ====================================================================

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
