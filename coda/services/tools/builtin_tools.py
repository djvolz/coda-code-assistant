"""
Built-in tools that provide reliable functionality without requiring external MCP servers.
These tools are always available and provide essential functionality.
"""

import datetime
import os
from typing import Any

from .base import BaseTool, ToolParameter, ToolParameterType, ToolResult, ToolSchema


class BuiltinCurrentTimeTool(BaseTool):
    """Get current date and time."""

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="builtin_current_time",
            description="Get the current date and time (built-in version)",
            category="system",
            server="builtin",
            parameters={},
        )

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        """Execute time retrieval."""
        now = datetime.datetime.now()
        return ToolResult(
            success=True,
            result=f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}",
            tool="builtin_current_time",
            server="builtin",
        )


class BuiltinListDirectoryTool(BaseTool):
    """List directory contents."""

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="builtin_list_directory",
            description="List files and directories in a given path (built-in version)",
            category="filesystem",
            server="builtin",
            parameters={
                "path": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Directory path to list",
                    default=".",
                    required=False,
                )
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        """Execute directory listing."""
        path = arguments.get("path", ".")

        try:
            items = os.listdir(path)
            # Separate directories and files
            dirs = []
            files = []

            for item in sorted(items):
                if not item.startswith("."):  # Skip hidden files
                    item_path = os.path.join(path, item)
                    if os.path.isdir(item_path):
                        dirs.append(f"📁 {item}/")
                    else:
                        files.append(f"📄 {item}")

            result = f"Contents of {path}:\n"
            result += "\n".join(dirs + files)

            return ToolResult(
                success=True, result=result, tool="builtin_list_directory", server="builtin"
            )

        except FileNotFoundError:
            return ToolResult(
                success=False,
                error=f"Directory not found: {path}",
                tool="builtin_list_directory",
                server="builtin",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error listing directory: {e}",
                tool="builtin_list_directory",
                server="builtin",
            )


class BuiltinQuickReadTool(BaseTool):
    """Quick file reading tool."""

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="builtin_quick_read",
            description="Quickly read a small text file (built-in version)",
            category="filesystem",
            server="builtin",
            parameters={
                "filepath": ToolParameter(
                    type=ToolParameterType.STRING, description="Path to the file to read"
                )
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        """Execute file reading."""
        filepath = arguments["filepath"]

        try:
            with open(filepath, encoding="utf-8") as f:
                content = f.read(5000)  # Read first 5KB
                if len(content) == 5000:
                    content += "\n... (file truncated to first 5KB)"

            return ToolResult(
                success=True,
                result=f"Contents of {filepath}:\n{content}",
                tool="builtin_quick_read",
                server="builtin",
            )
        except FileNotFoundError:
            return ToolResult(
                success=False,
                error=f"File not found: {filepath}",
                tool="builtin_quick_read",
                server="builtin",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error reading file: {e}",
                tool="builtin_quick_read",
                server="builtin",
            )


# Registry of all built-in tools
BUILTIN_TOOLS = [
    BuiltinCurrentTimeTool(),
    BuiltinListDirectoryTool(),
    BuiltinQuickReadTool(),
]


def get_builtin_tools():
    """Get all available built-in tools."""
    return BUILTIN_TOOLS.copy()
