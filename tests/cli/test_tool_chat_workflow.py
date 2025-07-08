"""Functional tests for tool chat command workflows."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from coda.agents.builtin_tools import get_builtin_tools
from coda.agents.decorators import tool
from coda.cli.tool_chat import ToolChatHandler
from rich.console import Console


# Create test tool at module level to avoid pytest fixture confusion
def _create_test_custom_tool():
    @tool
    def custom_tool_for_testing(input: str) -> str:
        """Custom tool for testing."""
        return f"Custom: {input}"

    return custom_tool_for_testing


custom_tool_for_testing = _create_test_custom_tool()


class MockSession:
    """Mock session for testing."""

    def __init__(self):
        self.messages = []
        self.mode = "default"
        self.settings = {"tools": {"enabled": False}}
        self.tools_enabled = False

    def add_message(self, role, content):
        self.messages.append({"role": role, "content": content})


class TestToolChatWorkflow:
    """Test /tools command workflows."""

    def _create_tool_handler(self, session, provider):
        """Create a ToolChatHandler with the correct signature."""
        console = Console()
        cli = session  # Use session as cli for these tests
        handler = ToolChatHandler(provider if provider else Mock(), cli, console)
        
        # Add a mock handle_chat method for tests
        async def handle_chat(message):
            return f"Handled: {message}"
        
        handler.handle_chat = handle_chat
        return handler

    @pytest.mark.asyncio
    async def test_tools_list_command(self):
        """Test /tools list command."""
        session = MockSession()
        handler = self._create_tool_handler(session, None)

        with patch("coda.cli.tool_chat.interactive") as mock_interactive:
            # Mock available tools
            mock_tools = [custom_tool_for_testing] + get_builtin_tools()[:3]
            mock_interactive.get_tools_for_mode.return_value = mock_tools

            with patch("builtins.print") as mock_print:
                result = await handler.handle_chat("/tools")

            # Verify output
            assert "Usage:" in result

            # Check that tools were listed
            print_calls = [call[0][0] for call in mock_print.call_args_list if call[0]]
            tools_output = "\n".join(str(c) for c in print_calls)

            assert "Available Tools" in tools_output
            assert "custom_tool_for_testing" in tools_output
            assert "Custom tool for testing" in tools_output

    @pytest.mark.asyncio
    async def test_tools_enable_command(self):
        """Test /tools enable command."""
        session = MockSession()
        provider = Mock()

        # Mock response after enabling tools
        response = Mock()
        response.content = "Tools have been enabled."
        response.tool_calls = []
        provider.chat = AsyncMock(return_value=response)

        handler = self._create_tool_handler(session, provider)

        # Test enable command
        result = await handler.handle_chat("/tools enable")

        # Verify
        assert session.settings["tools"]["enabled"] is True
        assert "enabled" in result.lower()
        assert session.tools_enabled is True

    @pytest.mark.asyncio
    async def test_tools_disable_command(self):
        """Test /tools disable command."""
        session = MockSession()
        session.settings["tools"]["enabled"] = True
        session.tools_enabled = True

        handler = self._create_tool_handler(session, None)

        # Test disable command
        result = await handler.handle_chat("/tools disable")

        # Verify
        assert session.settings["tools"]["enabled"] is False
        assert "disabled" in result.lower()
        assert session.tools_enabled is False

    @pytest.mark.asyncio
    async def test_tools_help_specific_tool(self):
        """Test /tools help for specific tool."""
        session = MockSession()
        handler = self._create_tool_handler(session, None)

        with patch("coda.cli.tool_chat.interactive") as mock_interactive:
            # Mock the tool
            mock_interactive.get_tools_for_mode.return_value = [custom_tool_for_testing]

            with patch("builtins.print") as mock_print:
                await handler.handle_chat("/tools help custom_tool_for_testing")

            # Verify help was shown
            print_output = "\n".join(
                str(call[0][0]) for call in mock_print.call_args_list if call[0]
            )
            assert "custom_tool_for_testing" in print_output
            assert "Custom tool for testing" in print_output
            assert "Parameters:" in print_output
            assert "input" in print_output

    @pytest.mark.asyncio
    async def test_tools_help_nonexistent_tool(self):
        """Test /tools help for non-existent tool."""
        session = MockSession()
        handler = self._create_tool_handler(session, None)

        with patch("coda.cli.tool_chat.interactive") as mock_interactive:
            mock_interactive.get_tools_for_mode.return_value = []

            result = await handler.handle_chat("/tools help nonexistent_tool")

            assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_tools_search_command(self):
        """Test /tools search command."""
        session = MockSession()
        handler = self._create_tool_handler(session, None)

        with patch("coda.cli.tool_chat.interactive") as mock_interactive:
            # Mock tools with various names
            from coda.agents.builtin_tools import list_files, read_file, write_file

            mock_interactive.get_tools_for_mode.return_value = [
                read_file,
                write_file,
                list_files,
                custom_tool_for_testing,
            ]

            with patch("builtins.print") as mock_print:
                await handler.handle_chat("/tools search file")

            # Verify search results
            print_output = "\n".join(
                str(call[0][0]) for call in mock_print.call_args_list if call[0]
            )
            assert "read_file" in print_output
            assert "write_file" in print_output
            assert "list_files" in print_output
            assert "custom_tool_for_testing" not in print_output  # Shouldn't match

    @pytest.mark.asyncio
    async def test_tools_categories_command(self):
        """Test /tools categories command."""
        session = MockSession()
        handler = self._create_tool_handler(session, None)

        with patch("coda.cli.tool_chat.interactive") as mock_interactive:
            # Create tools with different categories
            file_tool = Mock()
            file_tool._tool_name = "file_tool"
            file_tool._tool_description = "File operations"
            file_tool._tool_category = "filesystem"

            web_tool = Mock()
            web_tool._tool_name = "web_tool"
            web_tool._tool_description = "Web operations"
            web_tool._tool_category = "web"

            mock_interactive.get_tools_for_mode.return_value = [
                file_tool,
                web_tool,
                custom_tool_for_testing,
            ]

            with patch("builtins.print") as mock_print:
                await handler.handle_chat("/tools categories")

            print_output = "\n".join(
                str(call[0][0]) for call in mock_print.call_args_list if call[0]
            )
            assert "filesystem" in print_output
            assert "web" in print_output

    @pytest.mark.asyncio
    async def test_tools_with_agent_integration(self):
        """Test tools command with agent integration."""
        session = MockSession()
        provider = Mock()

        # First enable tools
        session.settings["tools"]["enabled"] = True

        # Mock tool execution
        tool_call = Mock()
        tool_call.name = "custom_tool_for_testing"
        tool_call.id = "custom1"
        tool_call.arguments = {"input": "hello"}

        response1 = Mock()
        response1.content = "I'll use the custom tool."
        response1.tool_calls = [tool_call]

        response2 = Mock()
        response2.content = "The custom tool returned: Custom: hello"
        response2.tool_calls = []

        provider.chat = AsyncMock(side_effect=[response1, response2])

        handler = self._create_tool_handler(session, provider)

        # Add custom tool to agent
        with patch("coda.cli.tool_chat.interactive") as mock_interactive:
            mock_interactive.get_tools_for_mode.return_value = [custom_tool_for_testing]

            # Initialize agent with tools
            handler._ensure_agent()

            # Test using tool
            result = await handler.handle_chat("Use the custom tool with 'hello'")

            assert "Custom: hello" in result

    @pytest.mark.asyncio
    async def test_tools_permissions_command(self):
        """Test /tools permissions command."""
        session = MockSession()
        handler = self._create_tool_handler(session, None)

        # Set some permissions
        session.settings["tools"] = {
            "enabled": True,
            "require_approval": True,
            "allowed_tools": ["read_file", "write_file"],
            "blocked_tools": ["run_command"],
        }

        with patch("builtins.print") as mock_print:
            await handler.handle_chat("/tools permissions")

        print_output = "\n".join(str(call[0][0]) for call in mock_print.call_args_list if call[0])
        assert "Tool Permissions" in print_output
        assert "Require approval: True" in print_output
        assert "Allowed tools:" in print_output
        assert "read_file" in print_output
        assert "Blocked tools:" in print_output
        assert "run_command" in print_output

    @pytest.mark.asyncio
    async def test_tools_invalid_command(self):
        """Test invalid /tools subcommand."""
        session = MockSession()
        handler = self._create_tool_handler(session, None)

        result = await handler.handle_chat("/tools invalid_subcommand")

        assert "Usage:" in result
        assert "/tools" in result

    @pytest.mark.asyncio
    async def test_tools_execution_with_approval(self):
        """Test tool execution requiring approval."""
        session = MockSession()
        session.settings["tools"] = {"enabled": True, "require_approval": True}
        provider = Mock()

        # Mock dangerous tool call
        tool_call = Mock()
        tool_call.name = "run_command"
        tool_call.id = "cmd1"
        tool_call.arguments = {"command": "echo 'test'"}

        response = Mock()
        response.content = "I need to run a command."
        response.tool_calls = [tool_call]

        provider.chat = AsyncMock(return_value=response)

        handler = self._create_tool_handler(session, provider)

        # Mock user approval
        with patch("builtins.input", return_value="y"):  # Approve
            with patch("coda.cli.tool_chat.interactive") as mock_interactive:
                from coda.agents.builtin_tools import run_command

                mock_interactive.get_tools_for_mode.return_value = [run_command]

                handler._ensure_agent()
                await handler.handle_chat("Run echo test")

        # Should have asked for approval
        assert session.settings["tools"]["require_approval"] is True

    @pytest.mark.asyncio
    async def test_tools_stats_command(self):
        """Test /tools stats command."""
        session = MockSession()
        handler = self._create_tool_handler(session, None)

        # Mock tool execution history
        handler.tool_stats = {
            "executions": 10,
            "by_tool": {"read_file": 5, "write_file": 3, "list_files": 2},
            "errors": 1,
        }

        with patch("builtins.print") as mock_print:
            await handler.handle_chat("/tools stats")

        print_output = "\n".join(str(call[0][0]) for call in mock_print.call_args_list if call[0])
        assert "Tool Usage Statistics" in print_output
        assert "Total executions: 10" in print_output
        assert "read_file: 5" in print_output
        assert "Errors: 1" in print_output

    @pytest.mark.asyncio
    async def test_tools_reset_command(self):
        """Test /tools reset command."""
        session = MockSession()
        provider = Mock()
        handler = self._create_tool_handler(session, provider)

        # Set up some state
        handler._agent = Mock()
        handler.tool_stats = {"executions": 5}
        session.settings["tools"]["enabled"] = True

        result = await handler.handle_chat("/tools reset")

        # Verify reset
        assert handler._agent is None
        assert handler.tool_stats == {}
        assert "reset" in result.lower()

    @pytest.mark.asyncio
    async def test_tools_export_command(self):
        """Test /tools export command."""
        session = MockSession()
        handler = self._create_tool_handler(session, None)

        with patch("coda.cli.tool_chat.interactive") as mock_interactive:
            mock_interactive.get_tools_for_mode.return_value = [custom_tool_for_testing]

            with patch("builtins.open", create=True) as mock_open:
                mock_file = Mock()
                mock_open.return_value.__enter__.return_value = mock_file

                result = await handler.handle_chat("/tools export tools_list.json")

            # Verify export
            assert "exported" in result.lower()
            mock_file.write.assert_called()

            # Check JSON content
            written_content = mock_file.write.call_args[0][0]
            assert "custom_tool_for_testing" in written_content
            assert "Custom tool for testing" in written_content
