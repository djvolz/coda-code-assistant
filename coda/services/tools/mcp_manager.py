"""
MCP server manager that discovers and manages external MCP servers from configuration.

This module integrates with mcp_config to discover servers from mcp.json files
and manages their lifecycle (starting, stopping, connecting).

CLIENT STRATEGY:
The system supports multiple MCP client types using the Strategy pattern:
- SubprocessMCPClient: For local MCP servers using stdio communication
- RemoteMCPClient: For servers accessible via HTTP/WebSocket
- Both clients implement BaseMCPClient interface for consistent behavior

Client selection is automatic based on server configuration:
- If 'url' is specified → RemoteMCPClient (network communication)
- If 'command' is specified → SubprocessMCPClient (subprocess stdio)
"""

import logging
import os
from pathlib import Path
from typing import Any

from coda.base.config.manager import ConfigManager
from coda.base.config.models import MCPServerConfig

from .base import BaseTool, ToolParameter, ToolRegistry, ToolResult, ToolSchema
from .clients.remote_client import RemoteMCPClient
from .clients.subprocess_client import SubprocessMCPClient
from .mcp_utils import extract_tool_content, format_mcp_error

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
        """Execute the external tool via MCP with configurable timeout."""
        # Get timeout from environment or use default
        timeout = float(os.environ.get("MCP_TOOL_TIMEOUT", "30.0"))

        try:
            result = await self.server_process.call_tool(
                self.tool_info["name"], arguments, timeout=timeout
            )

            # Handle MCP response format
            if "error" in result:
                return ToolResult(
                    success=False,
                    error=result["error"],
                    tool=self._schema.name,
                    server=self.server_name,
                )

            # Extract content using utility function
            text_content = extract_tool_content(result)
            return ToolResult(
                success=True,
                result=text_content,
                metadata=result.get("metadata", {}),
                tool=self._schema.name,
                server=self.server_name,
            )

        except Exception as e:
            error_msg = format_mcp_error(e, f"executing external tool {self._schema.name}")
            logger.error(error_msg)
            return ToolResult(
                success=False, error=str(e), tool=self._schema.name, server=self.server_name
            )


class MCPServerProcess:
    """Manages an MCP server using Strategy pattern for different client types."""

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.client = self._create_client()

    def _create_client(self):
        """Create appropriate MCP client based on server configuration.

        Uses the Strategy pattern to select client implementation:
        - RemoteMCPClient for servers with 'url' (HTTP/WebSocket communication)
        - SubprocessMCPClient for servers with 'command' (stdio communication)

        Both client types implement the same BaseMCPClient interface,
        ensuring consistent behavior regardless of connection type.
        """
        if self.config.url:
            # Remote server - use HTTP/WebSocket client
            return RemoteMCPClient(self.config.url, self.config.auth_token)
        else:
            # Local subprocess server - use stdio client
            return SubprocessMCPClient(
                command=self.config.command, args=self.config.args, env=self.config.env
            )

    async def start(self) -> bool:
        """Start the MCP server."""
        try:
            return await self.client.start()
        except Exception as e:
            error_msg = format_mcp_error(e, f"starting MCP server '{self.config.name}'")
            logger.error(error_msg)
            return False

    async def list_tools(self) -> list[dict[str, Any]]:
        """List tools from the server."""
        return await self.client.list_tools()

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any], timeout: float = 30.0
    ) -> dict[str, Any]:
        """Call a tool on the server with timeout."""
        return await self.client.call_tool(tool_name, arguments, timeout=timeout)

    async def stop(self):
        """Stop the MCP server."""
        await self.client.stop()

    @property
    def is_connected(self) -> bool:
        """Check if the server is connected."""
        return self.client.is_connected


class MCPManager:
    """Manages external MCP servers and their tools."""

    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self.servers: dict[str, MCPServerProcess] = {}
        self.external_tools: dict[str, ExternalMCPTool] = {}

    async def discover_and_start_servers(self, project_dir: Path | None = None):
        """Discover MCP servers from configuration and start them."""
        config_manager = ConfigManager(app_name="coda")
        config = config_manager.get_mcp_config(project_dir)

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
                logger.info(
                    f"MCP server '{config.name}' provided no additional tools (using built-in tools)"
                )

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
