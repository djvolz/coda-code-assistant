"""
MCP (Model Context Protocol) server implementation for tool discovery.

This module provides a basic MCP server that can expose Coda's built-in tools
to external MCP clients and discover external MCP tools.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

import aiohttp
from aiohttp import web

from . import execute_tool
from .base import tool_registry

logger = logging.getLogger(__name__)


class MCPMessageType(str, Enum):
    """MCP message types according to the protocol."""

    INITIALIZE = "initialize"
    INITIALIZED = "initialized"
    LIST_TOOLS = "tools/list"
    CALL_TOOL = "tools/call"
    LIST_RESOURCES = "resources/list"
    READ_RESOURCE = "resources/read"
    LIST_PROMPTS = "prompts/list"
    GET_PROMPT = "prompts/get"
    NOTIFICATION = "notification"
    ERROR = "error"


@dataclass
class MCPMessage:
    """MCP protocol message."""

    id: str | int | None
    method: str
    params: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        msg = {"jsonrpc": "2.0"}

        if self.id is not None:
            msg["id"] = self.id

        if self.method:
            msg["method"] = self.method

        if self.params is not None:
            msg["params"] = self.params

        if self.result is not None:
            msg["result"] = self.result

        if self.error is not None:
            msg["error"] = self.error

        return msg


class MCPServer:
    """Basic MCP server implementation."""

    def __init__(self, host: str = "localhost", port: int = 8080):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.clients: list[web.WebSocketResponse] = []
        self.setup_routes()

    def setup_routes(self) -> None:
        """Setup HTTP routes for the MCP server."""
        self.app.router.add_get("/", self.handle_info)
        self.app.router.add_post("/mcp", self.handle_mcp_http)
        self.app.router.add_get("/mcp/ws", self.handle_mcp_websocket)

    async def handle_info(self, request: web.Request) -> web.Response:
        """Handle info requests about the MCP server."""
        info = {
            "name": "Coda Tools MCP Server",
            "version": "1.0.0",
            "description": "MCP server exposing Coda's built-in tools",
            "tools_count": len(tool_registry.list_tools()),
            "categories": tool_registry.list_categories(),
            "endpoints": {
                "http": f"http://{self.host}:{self.port}/mcp",
                "websocket": f"ws://{self.host}:{self.port}/mcp/ws",
            },
        }
        return web.json_response(info)

    async def handle_mcp_http(self, request: web.Request) -> web.Response:
        """Handle MCP messages via HTTP."""
        try:
            data = await request.json()
            response = await self.process_mcp_message(data)
            return web.json_response(response.to_dict())
        except Exception as e:
            logger.error(f"Error handling MCP HTTP request: {e}")
            error_response = MCPMessage(
                id=None, method="", error={"code": -32600, "message": "Invalid Request"}
            )
            return web.json_response(error_response.to_dict(), status=400)

    async def handle_mcp_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """Handle MCP messages via WebSocket."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        self.clients.append(ws)
        logger.info(f"New MCP WebSocket client connected. Total clients: {len(self.clients)}")

        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        response = await self.process_mcp_message(data)
                        await ws.send_str(json.dumps(response.to_dict()))
                    except Exception as e:
                        logger.error(f"Error processing WebSocket message: {e}")
                        error_response = MCPMessage(
                            id=None, method="", error={"code": -32600, "message": "Invalid Request"}
                        )
                        await ws.send_str(json.dumps(error_response.to_dict()))
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
        finally:
            if ws in self.clients:
                self.clients.remove(ws)
            logger.info(
                f"MCP WebSocket client disconnected. Remaining clients: {len(self.clients)}"
            )

        return ws

    async def process_mcp_message(self, data: dict[str, Any]) -> MCPMessage:
        """Process an MCP protocol message."""
        try:
            method = data.get("method")
            params = data.get("params", {})
            msg_id = data.get("id")

            if method == MCPMessageType.INITIALIZE:
                return await self.handle_initialize(msg_id, params)
            elif method == MCPMessageType.LIST_TOOLS:
                return await self.handle_list_tools(msg_id, params)
            elif method == MCPMessageType.CALL_TOOL:
                return await self.handle_call_tool(msg_id, params)
            elif method == MCPMessageType.LIST_RESOURCES:
                return await self.handle_list_resources(msg_id, params)
            elif method == MCPMessageType.LIST_PROMPTS:
                return await self.handle_list_prompts(msg_id, params)
            else:
                return MCPMessage(
                    id=msg_id,
                    method="",
                    error={"code": -32601, "message": f"Method not found: {method}"},
                )
        except Exception as e:
            logger.error(f"Error processing MCP message: {e}")
            return MCPMessage(
                id=data.get("id"),
                method="",
                error={"code": -32603, "message": f"Internal error: {str(e)}"},
            )

    async def handle_initialize(self, msg_id: Any, params: dict[str, Any]) -> MCPMessage:
        """Handle MCP initialize request."""
        client_info = params.get("clientInfo", {})
        logger.info(f"MCP client initializing: {client_info}")

        result = {
            "protocolVersion": "2025-06-18",
            "serverInfo": {"name": "Coda Tools MCP Server", "version": "1.0.0"},
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
                "prompts": {"listChanged": False},
            },
        }

        return MCPMessage(id=msg_id, method="", result=result)

    async def handle_list_tools(self, msg_id: Any, params: dict[str, Any]) -> MCPMessage:
        """Handle tools/list request."""
        tools = tool_registry.list_tools()

        mcp_tools = []
        for tool_schema in tools:
            mcp_tool = {
                "name": tool_schema.name,
                "description": tool_schema.description,
                "inputSchema": {"type": "object", "properties": {}, "required": []},
            }

            # Convert tool parameters to JSON schema
            for param_name, param in tool_schema.parameters.items():
                mcp_tool["inputSchema"]["properties"][param_name] = {
                    "type": param.type.value,
                    "description": param.description,
                }

                if param.default is not None:
                    mcp_tool["inputSchema"]["properties"][param_name]["default"] = param.default

                if param.enum:
                    mcp_tool["inputSchema"]["properties"][param_name]["enum"] = param.enum

                if param.required:
                    mcp_tool["inputSchema"]["required"].append(param_name)

            mcp_tools.append(mcp_tool)

        result = {"tools": mcp_tools}
        return MCPMessage(id=msg_id, method="", result=result)

    async def handle_call_tool(self, msg_id: Any, params: dict[str, Any]) -> MCPMessage:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not tool_name:
            return MCPMessage(
                id=msg_id, method="", error={"code": -32602, "message": "Missing tool name"}
            )

        try:
            # Execute the tool
            result = await execute_tool(tool_name, arguments)

            # Convert ToolResult to MCP format
            mcp_result = {
                "content": [
                    {
                        "type": "text",
                        "text": (
                            str(result.result) if result.result else (result.error or "No output")
                        ),
                    }
                ],
                "isError": not result.success,
            }

            # Add metadata if available
            if result.metadata:
                mcp_result["metadata"] = result.metadata

            return MCPMessage(id=msg_id, method="", result=mcp_result)

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return MCPMessage(
                id=msg_id,
                method="",
                error={"code": -32603, "message": f"Tool execution failed: {str(e)}"},
            )

    async def handle_list_resources(self, msg_id: Any, params: dict[str, Any]) -> MCPMessage:
        """Handle resources/list request."""
        # For now, we don't expose resources, but this could be extended
        result = {"resources": []}
        return MCPMessage(id=msg_id, method="", result=result)

    async def handle_list_prompts(self, msg_id: Any, params: dict[str, Any]) -> MCPMessage:
        """Handle prompts/list request."""
        # For now, we don't expose prompts, but this could be extended
        result = {"prompts": []}
        return MCPMessage(id=msg_id, method="", result=result)

    async def start(self) -> None:
        """Start the MCP server."""
        runner = web.AppRunner(self.app)
        await runner.setup()

        site = web.TCPSite(runner, self.host, self.port)
        await site.start()

        logger.info(f"MCP server started on http://{self.host}:{self.port}")
        logger.info(f"WebSocket endpoint: ws://{self.host}:{self.port}/mcp/ws")
        logger.info(f"HTTP endpoint: http://{self.host}:{self.port}/mcp")

    async def stop(self) -> None:
        """Stop the MCP server."""
        # Close all WebSocket connections
        for ws in self.clients:
            await ws.close()
        self.clients.clear()

        # Stop the web application
        await self.app.cleanup()
        logger.info("MCP server stopped")


class MCPClient:
    """Basic MCP client for connecting to external MCP servers."""

    def __init__(self, server_url: str, auth_token: str | None = None):
        self.server_url = server_url
        self.auth_token = auth_token
        self.session: aiohttp.ClientSession | None = None
        self.tools: list[dict[str, Any]] = []

    async def connect(self) -> None:
        """Connect to the MCP server."""
        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        self.session = aiohttp.ClientSession(headers=headers)

        # Initialize the connection
        init_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "clientInfo": {"name": "Coda MCP Client", "version": "1.0.0"},
            },
        }

        try:
            if self.server_url.startswith("ws"):
                # WebSocket connection
                self.ws = await self.session.ws_connect(self.server_url)
                await self.ws.send_str(json.dumps(init_message))

                # Wait for initialization response
                msg = await self.ws.receive()
                if msg.type == aiohttp.WSMsgType.TEXT:
                    response = json.loads(msg.data)
                    logger.info(f"Connected to MCP server: {response}")

            else:
                # HTTP connection
                async with self.session.post(self.server_url, json=init_message) as resp:
                    response = await resp.json()
                    logger.info(f"Connected to MCP server: {response}")

            # List available tools
            await self.list_tools()

        except Exception as e:
            logger.error(f"Failed to connect to MCP server {self.server_url}: {e}")
            raise

    async def list_tools(self) -> list[dict[str, Any]]:
        """List tools available on the MCP server."""
        message = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}

        try:
            if hasattr(self, "ws"):
                # WebSocket
                await self.ws.send_str(json.dumps(message))
                msg = await self.ws.receive()
                response = json.loads(msg.data)
            else:
                # HTTP
                async with self.session.post(self.server_url, json=message) as resp:
                    response = await resp.json()

            if "result" in response and "tools" in response["result"]:
                self.tools = response["result"]["tools"]
                logger.info(f"Found {len(self.tools)} tools on MCP server")
                return self.tools
            else:
                logger.error(f"Unexpected response from MCP server: {response}")
                return []

        except Exception as e:
            logger.error(f"Failed to list tools from MCP server: {e}")
            return []

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool on the MCP server."""
        message = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }

        try:
            if hasattr(self, "ws"):
                # WebSocket
                await self.ws.send_str(json.dumps(message))
                msg = await self.ws.receive()
                response = json.loads(msg.data)
            else:
                # HTTP
                async with self.session.post(self.server_url, json=message) as resp:
                    response = await resp.json()

            return response.get("result", {})

        except Exception as e:
            logger.error(f"Failed to call tool {tool_name} on MCP server: {e}")
            return {"error": str(e)}

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        if hasattr(self, "ws"):
            await self.ws.close()

        if self.session:
            await self.session.close()

        logger.info("Disconnected from MCP server")


# Convenience functions for starting/stopping the MCP server
_mcp_server: MCPServer | None = None


async def start_mcp_server(host: str = "localhost", port: int = 8080) -> MCPServer:
    """Start the MCP server."""
    global _mcp_server

    if _mcp_server is not None:
        logger.warning("MCP server is already running")
        return _mcp_server

    _mcp_server = MCPServer(host, port)
    await _mcp_server.start()
    return _mcp_server


async def stop_mcp_server() -> None:
    """Stop the MCP server."""
    global _mcp_server

    if _mcp_server is not None:
        await _mcp_server.stop()
        _mcp_server = None


def get_mcp_server() -> MCPServer | None:
    """Get the running MCP server instance."""
    return _mcp_server


# Example usage and testing
async def main():
    """Example of running the MCP server."""
    await start_mcp_server()

    try:
        # Keep the server running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down MCP server...")
    finally:
        await stop_mcp_server()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
