"""
Modern MCP client using the official MCP Python SDK.

This provides a robust SDK-based implementation alongside the existing StdioMCPClient.
Both approaches are supported - this SDK client is used internally by SubprocessMCPClient
for improved reliability and error handling, while StdioMCPClient remains available for
direct stdio-based MCP server communication.
"""

import asyncio
import logging
import os
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class MCPClient:
    """Modern MCP client using the official MCP Python SDK."""

    def __init__(self, command: str, args: list[str], env: dict[str, str] | None = None):
        self.command = command
        self.args = args
        self.env = env or {}
        self.session: ClientSession | None = None
        self.exit_stack: AsyncExitStack = AsyncExitStack()
        self._tools_cache: list[dict[str, Any]] = []

    async def start(self) -> bool:
        """Start the MCP server and initialize the session."""
        try:
            # Create server parameters
            server_params = StdioServerParameters(
                command=self.command,
                args=self.args,
                env={**os.environ, **self.env} if self.env else None,
            )

            logger.info(f"Starting MCP server: {self.command} {' '.join(self.args)}")

            # Create the stdio client transport
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            read, write = stdio_transport

            # Create and initialize the client session
            session = await self.exit_stack.enter_async_context(ClientSession(read, write))
            await session.initialize()

            self.session = session
            logger.info("MCP server initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            await self.stop()
            return False

    async def list_tools(self) -> list[dict[str, Any]]:
        """List tools available on the MCP server."""
        if not self.session:
            logger.error("MCP session not initialized")
            return []

        try:
            tools_response = await self.session.list_tools()
            tools = []

            # Extract tools from the response
            for item in tools_response:
                if isinstance(item, tuple) and item[0] == "tools":
                    for tool in item[1]:
                        tools.append(
                            {
                                "name": tool.name,
                                "description": tool.description,
                                "inputSchema": tool.inputSchema,
                            }
                        )

            self._tools_cache = tools
            logger.info(f"Found {len(tools)} tools on MCP server")
            return tools

        except Exception as e:
            logger.warning(f"MCP server tools unavailable: {e}")
            return []

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any], timeout: float = 30.0
    ) -> dict[str, Any]:
        """Call a tool on the MCP server with timeout.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            timeout: Maximum time to wait for response (default: 30 seconds)
        """
        if not self.session:
            return {"error": "MCP session not initialized"}

        try:
            # Use asyncio.wait_for to add timeout
            result = await asyncio.wait_for(
                self.session.call_tool(tool_name, arguments), timeout=timeout
            )

            # Convert result to our expected format
            response = {"content": []}

            if hasattr(result, "content") and result.content:
                for content_item in result.content:
                    if hasattr(content_item, "text"):
                        response["content"].append({"type": "text", "text": content_item.text})
                    elif hasattr(content_item, "data"):
                        response["content"].append(
                            {
                                "type": "image",
                                "data": content_item.data,
                                "mimeType": getattr(content_item, "mimeType", "image/png"),
                            }
                        )

            if hasattr(result, "structuredContent") and result.structuredContent:
                response["structuredContent"] = result.structuredContent

            return response

        except TimeoutError:
            logger.error(f"Tool {tool_name} execution timed out after {timeout} seconds")
            return {"error": f"Tool execution timed out after {timeout} seconds"}
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return {"error": str(e)}

    async def stop(self):
        """Stop the MCP server and clean up resources."""
        try:
            await self.exit_stack.aclose()
            self.session = None
            self._tools_cache.clear()
            logger.info("MCP server stopped")
        except Exception as e:
            logger.error(f"Error stopping MCP server: {e}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
