"""
Remote MCP client for HTTP/WebSocket connections.

This client handles MCP servers that are accessed over the network.
"""

import logging
from typing import Any

from ..mcp_server import MCPClient as StdioRemoteClient
from .base import BaseMCPClient

logger = logging.getLogger(__name__)


class RemoteMCPClient(BaseMCPClient):
    """MCP client for remote servers accessed via HTTP/WebSocket."""

    def __init__(self, url: str, auth_token: str | None = None):
        self.url = url
        self.auth_token = auth_token
        self._remote_client: StdioRemoteClient | None = None

    async def start(self) -> bool:
        """Connect to the remote MCP server."""
        try:
            self._remote_client = StdioRemoteClient(self.url, self.auth_token)
            await self._remote_client.connect()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to remote MCP server: {e}")
            return False

    async def list_tools(self) -> list[dict[str, Any]]:
        """List tools from the remote server."""
        if not self._remote_client:
            return []
        return await self._remote_client.list_tools()

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any], timeout: float = 30.0
    ) -> dict[str, Any]:
        """Call a tool on the remote server with timeout."""
        if not self._remote_client:
            return {"error": "Client not connected"}
        return await self._remote_client.call_tool(tool_name, arguments, timeout=timeout)

    async def stop(self):
        """Disconnect from the remote server."""
        if self._remote_client:
            await self._remote_client.disconnect()
            self._remote_client = None

    @property
    def is_connected(self) -> bool:
        """Check if the remote client is connected."""
        return self._remote_client is not None
