"""
MCP server manager that discovers and manages external MCP servers from configuration.

This module integrates with mcp_config to discover servers from mcp.json files
and manages their lifecycle (starting, stopping, connecting).
"""

import logging
from pathlib import Path
from typing import Any

from .base import BaseTool, ToolParameter, ToolRegistry, ToolResult, ToolSchema
from .mcp_config import MCPServerConfig, load_mcp_config
from .mcp_server import MCPClient
from .mcp_stdio_client import StdioMCPClient

logger = logging.getLogger(__name__)


class ExternalMCPTool(BaseTool):
    """Wrapper for tools exposed by external MCP servers."""

    def __init__(
        self, server_name: str, tool_info: dict[str, Any], server_process: "MCPServerProcess"
    ):
        self.server_name = server_name
        self.tool_info = tool_info
        self.server_process = server_process
        self._schema = self._create_schema()

    def _create_schema(self) -> ToolSchema:
        """Create ToolSchema from MCP tool info."""
        # Parse parameters from inputSchema
        parameters = {}
        input_schema = self.tool_info.get("inputSchema", {})
        properties = input_schema.get("properties", {})
        required_params = input_schema.get("required", [])

        for param_name, param_info in properties.items():
            param = ToolParameter(
                type=param_info.get("type", "string"),
                description=param_info.get("description", ""),
                required=param_name in required_params,
                default=param_info.get("default"),
                enum=param_info.get("enum"),
            )
            parameters[param_name] = param

        return ToolSchema(
            name=f"{self.server_name}.{self.tool_info['name']}",
            description=self.tool_info.get("description", ""),
            category="external",
            server=self.server_name,
            parameters=parameters,
            dangerous=False,  # External tools are considered safe by default
        )

    def get_schema(self) -> ToolSchema:
        """Get the tool schema."""
        return self._schema

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        """Execute the external tool via MCP."""
        try:
            result = await self.server_process.call_tool(self.tool_info["name"], arguments)

            # Handle MCP response format
            if "error" in result:
                return ToolResult(
                    success=False,
                    error=result["error"],
                    tool=self._schema.name,
                    server=self.server_name,
                )

            # Extract content from MCP response
            content = result.get("content", [])
            if content and isinstance(content, list) and len(content) > 0:
                text_content = content[0].get("text", "")
                return ToolResult(
                    success=True,
                    result=text_content,
                    metadata=result.get("metadata", {}),
                    tool=self._schema.name,
                    server=self.server_name,
                )

            return ToolResult(
                success=True, result=str(result), tool=self._schema.name, server=self.server_name
            )

        except Exception as e:
            logger.error(f"Error executing external tool {self._schema.name}: {e}")
            return ToolResult(
                success=False, error=str(e), tool=self._schema.name, server=self.server_name
            )


class MCPServerProcess:
    """Manages an MCP server (either subprocess or remote)."""

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.client: MCPClient | StdioMCPClient | None = None
        self.is_subprocess = not bool(config.url)

    async def start(self) -> bool:
        """Start the MCP server (subprocess or connect to remote)."""
        try:
            if self.is_subprocess:
                # Create and start stdio client for subprocess
                self.client = StdioMCPClient(
                    command=self.config.command, args=self.config.args, env=self.config.env
                )
                return await self.client.start()
            else:
                # Connect to remote server
                self.client = MCPClient(self.config.url, self.config.auth_token)
                await self.client.connect()
                return True

        except Exception as e:
            logger.error(f"Failed to start MCP server '{self.config.name}': {e}")
            return False

    async def list_tools(self) -> list[dict[str, Any]]:
        """List tools from the server."""
        if self.client:
            return await self.client.list_tools()
        return []

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool on the server."""
        if self.client:
            return await self.client.call_tool(tool_name, arguments)
        return {"error": "Server not connected"}

    async def stop(self):
        """Stop the MCP server."""
        if self.client:
            if isinstance(self.client, StdioMCPClient):
                await self.client.stop()
            else:
                await self.client.disconnect()
            self.client = None


class MCPManager:
    """Manages external MCP servers and their tools."""

    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self.servers: dict[str, MCPServerProcess] = {}
        self.external_tools: dict[str, ExternalMCPTool] = {}

    async def discover_and_start_servers(self, project_dir: Path | None = None):
        """Discover MCP servers from configuration and start them."""
        config = load_mcp_config(project_dir)

        for server_name, server_config in config.servers.items():
            if server_name in self.servers:
                logger.info(f"MCP server '{server_name}' already running")
                continue

            await self.start_server(server_config)

    async def start_server(self, config: MCPServerConfig) -> bool:
        """Start a single MCP server and register its tools."""
        logger.info(f"Starting MCP server: {config.name}")

        server_process = MCPServerProcess(config)

        # Start the server (handles both subprocess and remote)
        if await server_process.start():
            self.servers[config.name] = server_process

            # List and register tools
            tools = await server_process.list_tools()
            if tools:
                await self._register_server_tools(config.name, server_process, tools)
            else:
                logger.warning(f"MCP server '{config.name}' has no tools")

            return True

        return False

    async def _register_server_tools(
        self, server_name: str, server_process: MCPServerProcess, tools: list[dict[str, Any]]
    ):
        """Register tools from an MCP server with the tool registry."""
        for tool_info in tools:
            external_tool = ExternalMCPTool(server_name, tool_info, server_process)
            tool_name = external_tool.get_schema().name

            # Register with the tool registry
            self.tool_registry.register(external_tool)
            self.external_tools[tool_name] = external_tool

            logger.info(f"Registered external tool: {tool_name}")

        logger.info(f"Registered {len(tools)} tools from MCP server '{server_name}'")

    async def stop_server(self, server_name: str):
        """Stop a specific MCP server."""
        if server_name in self.servers:
            # Unregister tools
            tools_to_remove = [
                name
                for name, tool in self.external_tools.items()
                if tool.server_name == server_name
            ]

            for tool_name in tools_to_remove:
                self.tool_registry.unregister(tool_name)
                del self.external_tools[tool_name]

            # Stop server
            await self.servers[server_name].stop()
            del self.servers[server_name]

            logger.info(
                f"Stopped MCP server '{server_name}' and unregistered {len(tools_to_remove)} tools"
            )

    async def stop_all_servers(self):
        """Stop all running MCP servers."""
        server_names = list(self.servers.keys())
        for server_name in server_names:
            await self.stop_server(server_name)

    def list_external_servers(self) -> list[str]:
        """List all running external MCP servers."""
        return list(self.servers.keys())

    def list_external_tools(self) -> list[str]:
        """List all tools from external MCP servers."""
        return list(self.external_tools.keys())


# Global MCP manager instance
_mcp_manager: MCPManager | None = None


def get_mcp_manager() -> MCPManager | None:
    """Get the global MCP manager instance."""
    return _mcp_manager


def init_mcp_manager(tool_registry: ToolRegistry) -> MCPManager:
    """Initialize the global MCP manager."""
    global _mcp_manager
    _mcp_manager = MCPManager(tool_registry)
    return _mcp_manager


async def discover_mcp_servers(project_dir: Path | None = None):
    """Discover and start MCP servers from configuration."""
    if _mcp_manager:
        await _mcp_manager.discover_and_start_servers(project_dir)
    else:
        logger.warning("MCP manager not initialized")


async def stop_all_mcp_servers():
    """Stop all running MCP servers."""
    if _mcp_manager:
        await _mcp_manager.stop_all_servers()
    else:
        logger.warning("MCP manager not initialized")
