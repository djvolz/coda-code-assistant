"""Functional tests for agent chat workflows in CLI."""

import os
import tempfile
from unittest.mock import AsyncMock, Mock, patch

import pytest

from coda.agents.decorators import tool
from coda.cli.agent_chat import AgentChatHandler
from coda.cli.tool_chat import ToolChatHandler


# Helper function to create workflow test tool
def create_workflow_test_tool():
    """Create test tool for workflow testing."""
    @tool
    def workflow_test_tool(message: str) -> str:
        """Test tool for workflow testing."""
        return f"Processed: {message}"

    return workflow_test_tool


class MockChatSession:
    """Mock chat session for testing."""

    def __init__(self):
        self.messages = []
        self.add_message_calls = []
        self.mode = "default"
        self.settings = {"tools": {"enabled": True}}

    def add_message(self, role, content):
        """Mock add_message method."""
        self.messages.append({"role": role, "content": content})
        self.add_message_calls.append((role, content))


class TestAgentChatWorkflow:
    """Test agent chat workflows in CLI."""

    @pytest.mark.asyncio
    async def test_agent_chat_basic_workflow(self):
        """Test basic agent chat workflow."""
        # Setup
        session = MockChatSession()
        provider = Mock()

        # Mock provider response
        response = Mock()
        response.content = "Hello! I can help you with that."
        response.tool_calls = []
        provider.chat = AsyncMock(return_value=response)

        handler = AgentChatHandler(session, provider)

        # Test chat
        result = await handler.handle_chat("Hello, agent!")

        # Verify
        assert result == "Hello! I can help you with that."
        assert len(session.add_message_calls) == 2  # user and assistant
        assert session.add_message_calls[0] == ("user", "Hello, agent!")
        assert session.add_message_calls[1] == ("assistant", "Hello! I can help you with that.")

    @pytest.mark.asyncio
    async def test_agent_chat_with_tool_execution(self):
        """Test agent chat with tool execution."""
        MockChatSession()
        provider = Mock()

        # Mock tool call
        tool_call = Mock()
        tool_call.name = "workflow_test_tool"
        tool_call.id = "test_call"
        tool_call.arguments = {"message": "test input"}

        # Mock provider responses
        response1 = Mock()
        response1.content = "I'll process that for you."
        response1.tool_calls = [tool_call]

        response2 = Mock()
        response2.content = "I've processed your message: test input"
        response2.tool_calls = []

        provider.chat = AsyncMock(side_effect=[response1, response2])

        # Create handler and mock tool availability
        console = Mock()
        cli = Mock()
        handler = AgentChatHandler(provider, cli, console)

        # Mock the tool availability and model info
        workflow_test_tool = create_workflow_test_tool()
        with patch.object(handler, 'get_available_tools', return_value=[workflow_test_tool]):
            # Mock model supports functions
            model_info = Mock()
            model_info.id = "test-model"
            model_info.supports_functions = True
            provider.list_models.return_value = [model_info]

            # Test chat - need to call the actual method
            messages = [Mock(role="user", content="Process 'test input'")]
            result, _ = await handler.chat_with_agent(messages, "test-model")

            # Verify
            assert "processed" in result.lower()

    @pytest.mark.asyncio
    async def test_tool_chat_handler_workflow(self):
        """Test tool chat handler workflow."""
        session = MockChatSession()
        provider = Mock()

        # Mock response
        response = Mock()
        response.content = "Tools are now enabled."
        response.tool_calls = []
        provider.chat = AsyncMock(return_value=response)

        handler = ToolChatHandler(session, provider)

        # Test enabling tools
        workflow_test_tool = create_workflow_test_tool()
        with patch('coda.cli.tool_chat.get_builtin_tools', return_value=[workflow_test_tool]):
            result = await handler.handle_chat("Enable tools")

        assert "Tools are now enabled." in result

    @pytest.mark.asyncio
    async def test_agent_error_handling_workflow(self):
        """Test agent error handling in CLI workflow."""
        session = MockChatSession()
        provider = Mock()

        # Mock provider to raise error
        provider.chat = AsyncMock(side_effect=Exception("Provider error"))

        handler = AgentChatHandler(session, provider)

        # Test chat with error
        result = await handler.handle_chat("Cause an error")

        # Should handle error gracefully
        assert "error" in result.lower()
        assert len(session.add_message_calls) >= 1  # At least user message

    @pytest.mark.asyncio
    async def test_multi_turn_conversation_workflow(self):
        """Test multi-turn conversation with agent."""
        session = MockChatSession()
        provider = Mock()

        # Mock responses for multi-turn conversation
        responses = [
            Mock(content="I'll help you create a file.", tool_calls=[
                Mock(name="write_file", id="w1", arguments={
                    "file_path": "/tmp/test.txt",
                    "content": "Hello"
                })
            ]),
            Mock(content="File created successfully.", tool_calls=[]),
            Mock(content="Now I'll read it back.", tool_calls=[
                Mock(name="read_file", id="r1", arguments={
                    "file_path": "/tmp/test.txt"
                })
            ]),
            Mock(content="The file contains: Hello", tool_calls=[])
        ]

        provider.chat = AsyncMock(side_effect=responses)

        handler = AgentChatHandler(session, provider)

        # Add file tools
        from coda.agents.builtin_tools import read_file, write_file
        handler.agent.add_tool(read_file)
        handler.agent.add_tool(write_file)

        # First turn
        result1 = await handler.handle_chat("Create a file with 'Hello'")
        assert "created" in result1.lower()

        # Second turn
        result2 = await handler.handle_chat("Now read it back")
        assert "Hello" in result2

        # Verify conversation history is maintained
        assert len(session.messages) > 4  # Multiple turns with tool calls

    @pytest.mark.asyncio
    async def test_tools_command_workflow(self):
        """Test /tools command workflow."""
        session = MockChatSession()

        # Mock interactive module
        with patch('coda.cli.tool_chat.interactive') as mock_interactive:
            mock_interactive.get_tools_for_mode.return_value = [create_workflow_test_tool()]

            handler = ToolChatHandler(session, None)

            # Test /tools command
            with patch('builtins.print') as mock_print:
                await handler.handle_chat("/tools")

            # Verify tools listing was printed
            mock_print.assert_called()
            call_args = [str(call) for call in mock_print.call_args_list]
            assert any("workflow_test_tool" in arg for arg in call_args)

    @pytest.mark.asyncio
    async def test_agent_with_system_prompt(self):
        """Test agent respecting system prompts."""
        session = MockChatSession()
        session.mode = "expert"
        session.system_prompt = "You are an expert assistant."

        provider = Mock()
        response = Mock()
        response.content = "As an expert, I recommend..."
        response.tool_calls = []
        provider.chat = AsyncMock(return_value=response)

        handler = AgentChatHandler(session, provider)

        await handler.handle_chat("Give me expert advice")

        # Verify system prompt was included
        provider.chat.assert_called_once()
        messages = provider.chat.call_args[0][0]
        assert any(msg.get("role") == "system" for msg in messages)

    @pytest.mark.asyncio
    async def test_streaming_mode_workflow(self):
        """Test agent in streaming mode."""
        session = MockChatSession()
        session.stream = True
        provider = Mock()

        # Mock streaming response
        async def mock_stream():
            chunks = ["Hello", " from", " streaming", " mode!"]
            for chunk in chunks:
                response = Mock()
                response.content = chunk
                response.tool_calls = []
                yield response

        provider.stream = Mock(return_value=mock_stream())
        provider.stream_available = True

        handler = AgentChatHandler(session, provider)

        # Collect streamed content
        result = ""
        async for chunk in handler.handle_stream("Test streaming"):
            result += chunk.content if hasattr(chunk, 'content') else str(chunk)

        assert "Hello from streaming mode!" in result

    @pytest.mark.asyncio
    async def test_tool_permission_workflow(self):
        """Test tool execution with permissions."""
        session = MockChatSession()
        session.settings = {
            "tools": {
                "enabled": True,
                "require_approval": True
            }
        }
        provider = Mock()

        # Mock tool call requiring approval
        tool_call = Mock()
        tool_call.name = "run_command"
        tool_call.id = "cmd1"
        tool_call.arguments = {"command": "rm -rf /"}

        response1 = Mock()
        response1.content = "I need to run a command."
        response1.tool_calls = [tool_call]

        provider.chat = AsyncMock(return_value=response1)

        handler = AgentChatHandler(session, provider)

        # Add dangerous tool
        from coda.agents.builtin_tools import run_command
        handler.agent.add_tool(run_command)

        # Mock user approval
        with patch('builtins.input', return_value='n'):  # Deny permission
            await handler.handle_chat("Delete everything")

        # Should not execute dangerous command
        assert len(handler.agent.conversation_history) > 0

    @pytest.mark.asyncio
    async def test_agent_context_preservation(self):
        """Test that agent preserves context across messages."""
        session = MockChatSession()
        provider = Mock()

        # Setup responses that reference previous context
        responses = [
            Mock(content="I'll remember that your name is Alice.", tool_calls=[]),
            Mock(content="Hello Alice! How can I help you today?", tool_calls=[])
        ]

        provider.chat = AsyncMock(side_effect=responses)

        handler = AgentChatHandler(session, provider)

        # First message
        await handler.handle_chat("My name is Alice")

        # Second message should remember context
        result = await handler.handle_chat("Do you remember my name?")

        assert "Alice" in result

        # Verify conversation history is maintained
        assert len(handler.agent.conversation_history) >= 4  # 2 user + 2 assistant

    @pytest.mark.asyncio
    async def test_file_operation_workflow(self):
        """Test complete file operation workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session = MockChatSession()
            provider = Mock()

            test_file = os.path.join(tmpdir, "workflow_test.txt")

            # Mock responses for file operations
            write_call = Mock(name="write_file", id="w1", arguments={
                "file_path": test_file,
                "content": "Test content for workflow"
            })

            read_call = Mock(name="read_file", id="r1", arguments={
                "file_path": test_file
            })

            list_call = Mock(name="list_files", id="l1", arguments={
                "directory": tmpdir
            })

            responses = [
                Mock(content="Creating file...", tool_calls=[write_call]),
                Mock(content="File created.", tool_calls=[]),
                Mock(content="Reading file...", tool_calls=[read_call]),
                Mock(content="File contains: Test content for workflow", tool_calls=[]),
                Mock(content="Listing directory...", tool_calls=[list_call]),
                Mock(content="Directory contains: workflow_test.txt", tool_calls=[])
            ]

            provider.chat = AsyncMock(side_effect=responses)

            handler = AgentChatHandler(session, provider)

            # Add all file operation tools
            from coda.agents.builtin_tools import list_files, read_file, write_file
            handler.agent.add_tool(read_file)
            handler.agent.add_tool(write_file)
            handler.agent.add_tool(list_files)

            # Execute workflow
            await handler.handle_chat(f"Create a file in {tmpdir}")
            await handler.handle_chat("Now read it")
            result = await handler.handle_chat("List the directory")

            # Verify
            assert "workflow_test.txt" in result
            assert os.path.exists(test_file)
            assert open(test_file).read() == "Test content for workflow"
