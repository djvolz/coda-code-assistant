"""
Subprocess-based MCP client using the official MCP SDK.

This client handles MCP servers that run as local subprocesses.
"""

import logging
from typing import Any

from ..mcp_sdk_client import MCPClient as SDKMCPClient
from .base import BaseMCPClient

logger = logging.getLogger(__name__)


class SubprocessMCPClient(BaseMCPClient):
    """MCP client for subprocess-based servers using the official SDK."""

    def __init__(self, command: str, args: list[str], env: dict[str, str] | None = None):
        self.command = command
        self.args = args
        self.env = env or {}
        self._sdk_client: SDKMCPClient | None = None

    async def start(self) -> bool:
        """Start the subprocess MCP server."""
        try:
            self._sdk_client = SDKMCPClient(self.command, self.args, self.env)
            return await self._sdk_client.start()
        except Exception as e:
            logger.error(f"Failed to start subprocess MCP server: {e}")
            return False

    async def list_tools(self) -> list[dict[str, Any]]:
        """List tools from the subprocess server."""
        if not self._sdk_client:
            return []
        return await self._sdk_client.list_tools()

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any], timeout: float = 30.0
    ) -> dict[str, Any]:
        """Call a tool on the subprocess server with timeout."""
        if not self._sdk_client:
            return {"error": "Client not initialized"}
        return await self._sdk_client.call_tool(tool_name, arguments, timeout=timeout)

    async def stop(self):
        """Stop the subprocess server."""
        if self._sdk_client:
            await self._sdk_client.stop()
            self._sdk_client = None

    @property
    def is_connected(self) -> bool:
        """Check if the subprocess client is connected."""
        return self._sdk_client is not None and self._sdk_client.session is not None
