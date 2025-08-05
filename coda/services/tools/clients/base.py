"""
Abstract base class for MCP clients.

This module defines the common interface that all MCP client implementations must follow,
enabling the Strategy pattern for different client types.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseMCPClient(ABC):
    """Abstract base class for all MCP client implementations."""

    @abstractmethod
    async def start(self) -> bool:
        """
        Start the MCP client connection.

        Returns:
            True if connection was successful, False otherwise
        """
        pass

    @abstractmethod
    async def list_tools(self) -> list[dict[str, Any]]:
        """
        List tools available from the MCP server.

        Returns:
            List of tool information dictionaries
        """
        pass

    @abstractmethod
    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool

        Returns:
            Tool execution result
        """
        pass

    @abstractmethod
    async def stop(self):
        """Stop the MCP client and clean up resources."""
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if the client is currently connected."""
        pass
