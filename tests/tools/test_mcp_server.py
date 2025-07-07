"""
Tests for the MCP (Model Context Protocol) server implementation.

This module tests the MCP server and client functionality for tool discovery
and execution through the MCP protocol.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
import pytest_asyncio

from coda.providers import MockProvider
from coda.tools import execute_tool, tool_registry
from coda.tools.mcp_server import (
    MCPClient,
    MCPMessage,
    MCPServer,
    get_mcp_server,
    start_mcp_server,
    stop_mcp_server,
)


class TestMCPMessage:
    """Test MCP message handling."""

    def test_mcp_message_creation(self):
        """Test creating MCP messages."""
        # Request message
        msg = MCPMessage(id=1, method="tools/list", params={"filter": "filesystem"})

        data = msg.to_dict()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 1
        assert data["method"] == "tools/list"
        assert data["params"]["filter"] == "filesystem"

        # Response message
        resp = MCPMessage(id=1, method="", result={"tools": []})

        data = resp.to_dict()
        assert data["id"] == 1
        assert "result" in data
        assert "error" not in data

        # Error message
        err = MCPMessage(id=1, method="", error={"code": -32601, "message": "Method not found"})

        data = err.to_dict()
        assert data["id"] == 1
        assert "error" in data
        assert data["error"]["code"] == -32601


class TestMCPServer:
    """Test MCP server functionality."""

    @pytest_asyncio.fixture
    async def mcp_server(self):
        """Create an MCP server instance."""
        server = MCPServer(host="localhost", port=0)  # Port 0 for random port
        yield server

    @pytest.mark.asyncio
    async def test_server_initialization(self, mcp_server):
        """Test MCP server initialization."""
        assert mcp_server.host == "localhost"
        assert mcp_server.port == 0
        assert len(mcp_server.clients) == 0

    @pytest.mark.asyncio
    async def test_handle_initialize(self, mcp_server):
        """Test handling initialize request."""
        response = await mcp_server.handle_initialize(
            msg_id=1,
            params={
                "protocolVersion": "2025-06-18",
                "clientInfo": {"name": "Test Client", "version": "1.0.0"},
            },
        )

        assert response.id == 1
        assert response.result is not None
        assert response.result["protocolVersion"] == "2025-06-18"
        assert response.result["serverInfo"]["name"] == "Coda Tools MCP Server"
        assert "capabilities" in response.result

    @pytest.mark.asyncio
    async def test_handle_list_tools(self, mcp_server):
        """Test listing available tools."""
        response = await mcp_server.handle_list_tools(msg_id=2, params={})

        assert response.id == 2
        assert response.result is not None
        assert "tools" in response.result
        tools = response.result["tools"]

        # Verify some expected tools
        tool_names = [tool["name"] for tool in tools]
        assert "read_file" in tool_names
        assert "shell_execute" in tool_names
        assert "git_status" in tool_names

        # Verify tool schema structure
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert tool["inputSchema"]["type"] == "object"
            assert "properties" in tool["inputSchema"]

    @pytest.mark.asyncio
    async def test_handle_call_tool(self, mcp_server, tmp_path):
        """Test calling a tool through MCP."""
        # Create test file
        test_file = tmp_path / "mcp_test.txt"
        test_content = "MCP test content"
        test_file.write_text(test_content)

        # Call read_file tool
        response = await mcp_server.handle_call_tool(
            msg_id=3, params={"name": "read_file", "arguments": {"filepath": str(test_file)}}
        )

        assert response.id == 3
        assert response.result is not None
        assert "content" in response.result
        assert len(response.result["content"]) > 0
        assert response.result["content"][0]["type"] == "text"
        assert test_content in response.result["content"][0]["text"]
        assert not response.result["isError"]

    @pytest.mark.asyncio
    async def test_handle_call_tool_error(self, mcp_server):
        """Test error handling when calling tools."""
        # Try to read non-existent file
        response = await mcp_server.handle_call_tool(
            msg_id=4,
            params={"name": "read_file", "arguments": {"filepath": "/nonexistent/file.txt"}},
        )

        assert response.id == 4
        assert response.result is not None
        assert response.result["isError"]
        assert "content" in response.result
        assert "not found" in response.result["content"][0]["text"].lower()

    @pytest.mark.asyncio
    async def test_handle_unknown_tool(self, mcp_server):
        """Test calling unknown tool."""
        response = await mcp_server.handle_call_tool(
            msg_id=5, params={"name": "unknown_tool", "arguments": {}}
        )

        assert response.id == 5
        assert response.result is not None
        assert response.result["isError"]

    @pytest.mark.asyncio
    async def test_handle_list_resources(self, mcp_server):
        """Test listing resources (currently empty)."""
        response = await mcp_server.handle_list_resources(msg_id=6, params={})

        assert response.id == 6
        assert response.result is not None
        assert "resources" in response.result
        assert response.result["resources"] == []

    @pytest.mark.asyncio
    async def test_handle_list_prompts(self, mcp_server):
        """Test listing prompts (currently empty)."""
        response = await mcp_server.handle_list_prompts(msg_id=7, params={})

        assert response.id == 7
        assert response.result is not None
        assert "prompts" in response.result
        assert response.result["prompts"] == []

    @pytest.mark.asyncio
    async def test_process_mcp_message(self, mcp_server):
        """Test processing complete MCP messages."""
        # Test initialize
        init_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
        }

        response = await mcp_server.process_mcp_message(init_msg)
        assert response.result is not None
        assert response.error is None

        # Test unknown method
        unknown_msg = {"jsonrpc": "2.0", "id": 2, "method": "unknown/method", "params": {}}

        response = await mcp_server.process_mcp_message(unknown_msg)
        assert response.error is not None
        assert response.error["code"] == -32601

    @pytest.mark.asyncio
    async def test_http_endpoint(self, mcp_server):
        """Test MCP HTTP endpoint handling."""
        # Mock the request
        mock_request = AsyncMock()
        mock_request.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        }

        response = await mcp_server.handle_mcp_http(mock_request)

        # Response should be a web.Response
        assert hasattr(response, "body")
        assert hasattr(response, "status")

    @pytest.mark.asyncio
    async def test_websocket_endpoint(self, mcp_server):
        """Test MCP WebSocket endpoint handling."""
        # This is a complex test that would require mocking WebSocket behavior
        # For now, we'll test the basic structure
        assert hasattr(mcp_server, "handle_mcp_websocket")
        assert callable(mcp_server.handle_mcp_websocket)


class TestMCPClient:
    """Test MCP client functionality."""

    @pytest_asyncio.fixture
    async def mcp_client(self):
        """Create an MCP client instance."""
        client = MCPClient("http://localhost:8080/mcp")
        yield client
        if client.session and hasattr(client.session, "close"):
            if asyncio.iscoroutinefunction(client.session.close):
                await client.session.close()
            else:
                client.session.close()

    def test_client_initialization(self, mcp_client):
        """Test MCP client initialization."""
        assert mcp_client.server_url == "http://localhost:8080/mcp"
        assert mcp_client.auth_token is None
        assert mcp_client.session is None
        assert mcp_client.tools == []

    @pytest.mark.asyncio
    async def test_client_list_tools(self, mcp_client):
        """Test client listing tools from server."""
        # Mock the HTTP session and response
        mock_response = MagicMock()
        mock_response.json = AsyncMock(
            return_value={
                "jsonrpc": "2.0",
                "id": 2,
                "result": {
                    "tools": [
                        {
                            "name": "test_tool",
                            "description": "A test tool",
                            "inputSchema": {"type": "object", "properties": {}},
                        }
                    ]
                },
            }
        )

        # Create a mock session with proper async context manager
        mock_session = MagicMock()
        mock_session.post = MagicMock(
            return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock()
            )
        )

        mcp_client.session = mock_session

        tools = await mcp_client.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "test_tool"

    @pytest.mark.asyncio
    async def test_client_call_tool(self, mcp_client):
        """Test client calling tool on server."""
        # Mock the HTTP session and response
        mock_response = MagicMock()
        mock_response.json = AsyncMock(
            return_value={
                "jsonrpc": "2.0",
                "id": 3,
                "result": {
                    "content": [{"type": "text", "text": "Tool executed successfully"}],
                    "isError": False,
                },
            }
        )

        # Create a mock session with proper async context manager
        mock_session = MagicMock()
        mock_session.post = MagicMock(
            return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock()
            )
        )

        mcp_client.session = mock_session

        result = await mcp_client.call_tool("test_tool", {"param": "value"})
        assert "content" in result
        assert not result["isError"]

    @pytest.mark.asyncio
    async def test_client_websocket_connection(self):
        """Test client WebSocket connection."""
        client = MCPClient("ws://localhost:8080/mcp/ws")

        # Mock WebSocket connection
        mock_ws = AsyncMock()
        mock_ws.receive.return_value.type = aiohttp.WSMsgType.TEXT
        mock_ws.receive.return_value.data = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2025-06-18"}}
        )

        mock_session = AsyncMock()
        mock_session.ws_connect.return_value = mock_ws

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = mock_session

            # Test connection would happen here
            # await client.connect()

            assert client.server_url.startswith("ws")


class TestMCPServerManagement:
    """Test MCP server management functions."""

    @pytest.mark.asyncio
    async def test_start_stop_server(self):
        """Test starting and stopping MCP server."""
        # Ensure no server is running
        await stop_mcp_server()
        assert get_mcp_server() is None

        # Start server (using mock to avoid actual network binding)
        with patch("coda.tools.mcp_server.MCPServer.start", new_callable=AsyncMock):
            server = await start_mcp_server(port=0)
            assert server is not None
            assert get_mcp_server() is server

            # Try to start again - should return existing server
            server2 = await start_mcp_server(port=0)
            assert server2 is server

        # Stop server
        with patch("coda.tools.mcp_server.MCPServer.stop", new_callable=AsyncMock):
            await stop_mcp_server()
            assert get_mcp_server() is None


class TestMCPIntegration:
    """Test MCP integration with tool system."""

    @pytest.mark.asyncio
    async def test_mcp_tool_discovery(self):
        """Test that all registered tools are discoverable via MCP."""
        server = MCPServer()

        # Get tools via MCP
        response = await server.handle_list_tools(msg_id=1, params={})
        mcp_tools = response.result["tools"]
        mcp_tool_names = {tool["name"] for tool in mcp_tools}

        # Get tools from registry
        registry_tools = tool_registry.list_tools()
        registry_tool_names = {tool.name for tool in registry_tools}

        # All registry tools should be available via MCP
        assert mcp_tool_names == registry_tool_names

    @pytest.mark.asyncio
    async def test_mcp_tool_execution_matches_direct(self, tmp_path):
        """Test that MCP tool execution matches direct execution."""
        server = MCPServer()

        # Create test file
        test_file = tmp_path / "test.txt"
        test_content = "Test content for MCP"
        test_file.write_text(test_content)

        # Execute tool directly
        direct_result = await execute_tool("read_file", {"filepath": str(test_file)})

        # Execute tool via MCP
        mcp_response = await server.handle_call_tool(
            msg_id=1, params={"name": "read_file", "arguments": {"filepath": str(test_file)}}
        )

        # Results should match
        assert direct_result.success
        assert not mcp_response.result["isError"]
        assert test_content in str(direct_result.result)
        assert test_content in mcp_response.result["content"][0]["text"]

    @pytest.fixture
    def mock_provider(self):
        """Create a MockProvider instance."""
        return MockProvider()

    @pytest.mark.asyncio
    async def test_mcp_with_mock_provider(self, mock_provider):
        """Test MCP server works with mock provider context."""
        server = MCPServer()

        # List tools should work regardless of provider
        response = await server.handle_list_tools(msg_id=1, params={})
        assert len(response.result["tools"]) > 0

        # Tool execution should work
        response = await server.handle_call_tool(
            msg_id=2, params={"name": "get_current_time", "arguments": {}}
        )

        assert response.result is not None
        assert not response.result["isError"]
        assert "Current time" in response.result["content"][0]["text"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
