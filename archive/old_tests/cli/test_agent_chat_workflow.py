"""Functional tests for agent chat workflows in CLI."""

import os
import tempfile
from unittest.mock import Mock, patch

import pytest
from rich.console import Console

from coda.agents.decorators import tool
from coda.cli.agent_chat import AgentChatHandler
from coda.providers.base import Message, Role


# Helper function to create workflow test tool
def create_workflow_test_tool():
    """Create test tool for workflow testing."""

    @tool
    def workflow_test_tool(message: str) -> str:
        """Test tool for workflow testing."""
        return f"Processed: {message}"

    return workflow_test_tool


class MockCLI:
    """Mock CLI for testing."""

    def __init__(self):
        self.messages = []
        self.interrupt_event = Mock()
        self.interrupt_event.is_set.return_value = False


class TestAgentChatWorkflow:
    """Test agent chat workflows in CLI."""

    def _create_agent_handler(self, cli, provider):
        """Create an AgentChatHandler with the correct signature."""
        console = Console()
        return AgentChatHandler(provider, cli, console)

    @pytest.mark.asyncio
    async def test_agent_chat_basic_workflow(self):
        """Test basic agent chat workflow."""
        # Setup
        cli = MockCLI()
        provider = Mock()

        # Mock provider response
        response = Mock()
        response.content = "Hello! I can help you with that."
        response.tool_calls = []
        provider.chat = Mock(return_value=response)

        # Mock model info
        model_info = Mock()
        model_info.id = "test-model"
        model_info.supports_functions = True
        provider.list_models.return_value = [model_info]

        handler = self._create_agent_handler(cli, provider)

        # Create messages
        messages = [Message(role=Role.USER, content="Hello, agent!")]

        # Test chat
        result, updated_messages = await handler.chat_with_agent(
            messages=messages, model="test-model"
        )

        # Verify
        assert result == "Hello! I can help you with that."
        assert len(updated_messages) > len(messages)  # Should have added assistant response

    @pytest.mark.asyncio
    async def test_agent_chat_with_tool_execution(self):
        """Test agent chat with tool execution."""
        cli = MockCLI()
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

        provider.chat = Mock(side_effect=[response1, response2])

        # Mock model info
        model_info = Mock()
        model_info.id = "test-model"
        model_info.supports_functions = True
        provider.list_models.return_value = [model_info]

        handler = self._create_agent_handler(cli, provider)

        # Mock the tool availability
        workflow_test_tool = create_workflow_test_tool()
        with patch.object(handler, "get_available_tools", return_value=[workflow_test_tool]):
            messages = [Message(role=Role.USER, content="Process 'test input'")]

            # Test chat
            result, updated_messages = await handler.chat_with_agent(
                messages=messages, model="test-model"
            )

            # Verify
            assert "processed" in result.lower() or "test input" in result.lower()

    @pytest.mark.asyncio
    async def test_agent_error_handling_workflow(self):
        """Test agent error handling in CLI workflow."""
        cli = MockCLI()
        provider = Mock()

        # Mock provider to raise error
        provider.chat = Mock(side_effect=Exception("Provider error"))

        # Mock model info
        model_info = Mock()
        model_info.id = "test-model"
        model_info.supports_functions = True
        provider.list_models.return_value = [model_info]

        handler = self._create_agent_handler(cli, provider)

        messages = [Message(role=Role.USER, content="Cause an error")]

        # Test chat with error
        result, updated_messages = await handler.chat_with_agent(
            messages=messages, model="test-model"
        )

        # Should handle error gracefully
        assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_multi_turn_conversation_workflow(self):
        """Test multi-turn conversation with agent."""
        cli = MockCLI()
        provider = Mock()

        # Mock responses for multi-turn conversation
        responses = [
            Mock(
                content="I'll help you create a file.",
                tool_calls=[
                    Mock(
                        name="write_file",
                        id="w1",
                        arguments={"file_path": "/tmp/test.txt", "content": "Hello"},
                    )
                ],
            ),
            Mock(content="File created successfully.", tool_calls=[]),
            Mock(
                content="Now I'll read it back.",
                tool_calls=[
                    Mock(name="read_file", id="r1", arguments={"file_path": "/tmp/test.txt"})
                ],
            ),
            Mock(content="The file contains: Hello", tool_calls=[]),
        ]

        provider.chat = Mock(side_effect=responses)

        # Mock model info
        model_info = Mock()
        model_info.id = "test-model"
        model_info.supports_functions = True
        provider.list_models.return_value = [model_info]

        handler = self._create_agent_handler(cli, provider)

        # Add file tools
        from coda.agents.builtin_tools import read_file, write_file

        with patch.object(handler, "get_available_tools", return_value=[read_file, write_file]):
            # First turn
            messages1 = [Message(role=Role.USER, content="Create a file with 'Hello'")]
            result1, updated_messages1 = await handler.chat_with_agent(
                messages=messages1, model="test-model"
            )
            assert "created" in result1.lower() or "file" in result1.lower()

            # Second turn
            messages2 = updated_messages1 + [Message(role=Role.USER, content="Now read it back")]
            result2, updated_messages2 = await handler.chat_with_agent(
                messages=messages2, model="test-model"
            )
            assert "Hello" in result2 or "contains" in result2.lower()

    @pytest.mark.asyncio
    async def test_agent_with_system_prompt(self):
        """Test agent respecting system prompts."""
        cli = MockCLI()
        provider = Mock()

        response = Mock()
        response.content = "As an expert, I recommend..."
        response.tool_calls = []
        provider.chat = Mock(return_value=response)

        # Mock model info
        model_info = Mock()
        model_info.id = "test-model"
        model_info.supports_functions = True
        provider.list_models.return_value = [model_info]

        handler = self._create_agent_handler(cli, provider)

        messages = [Message(role=Role.USER, content="Give me expert advice")]

        await handler.chat_with_agent(
            messages=messages, model="test-model", system_prompt="You are an expert assistant."
        )

        # Verify system prompt was used (it's passed to Agent's instructions)
        assert handler.agent is not None
        assert "expert" in handler.agent.instructions.lower()

    @pytest.mark.asyncio
    async def test_streaming_mode_workflow(self):
        """Test agent in streaming mode fallback."""
        cli = MockCLI()
        provider = Mock()

        # Mock streaming response
        chunks = []
        for text in ["Hello", " from", " streaming", " mode!"]:
            chunk = Mock()
            chunk.content = text
            chunks.append(chunk)

        provider.chat_stream.return_value = iter(chunks)

        handler = self._create_agent_handler(cli, provider)

        messages = [Message(role=Role.USER, content="Test streaming")]

        # Test fallback streaming
        result = await handler.stream_chat_fallback(messages=messages, model="test-model")

        assert result == "Hello from streaming mode!"

    @pytest.mark.asyncio
    async def test_tool_toggle_workflow(self):
        """Test toggling tools on/off."""
        cli = MockCLI()
        provider = Mock()

        handler = self._create_agent_handler(cli, provider)

        # Initially tools should be on
        assert handler.use_tools is True

        # Toggle off
        result = handler.toggle_tools()
        assert result is False
        assert handler.use_tools is False
        assert handler.agent is None  # Should reset agent

        # Toggle back on
        result = handler.toggle_tools()
        assert result is True
        assert handler.use_tools is True

    @pytest.mark.asyncio
    async def test_agent_without_function_support(self):
        """Test agent behavior when model doesn't support functions."""
        cli = MockCLI()
        provider = Mock()

        # Mock model info without function support
        model_info = Mock()
        model_info.id = "basic-model"
        model_info.supports_functions = False
        provider.list_models.return_value = [model_info]

        handler = self._create_agent_handler(cli, provider)

        # Should not use agent
        assert handler.should_use_agent("basic-model") is False

    @pytest.mark.asyncio
    async def test_file_operation_workflow(self):
        """Test complete file operation workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cli = MockCLI()
            provider = Mock()

            test_file = os.path.join(tmpdir, "workflow_test.txt")

            # Mock responses for file operations
            write_call = Mock(
                name="write_file",
                id="w1",
                arguments={"file_path": test_file, "content": "Test content for workflow"},
            )

            read_call = Mock(name="read_file", id="r1", arguments={"file_path": test_file})

            list_call = Mock(name="list_files", id="l1", arguments={"directory": tmpdir})

            responses = [
                Mock(content="Creating file...", tool_calls=[write_call]),
                Mock(content="File created.", tool_calls=[]),
                Mock(content="Reading file...", tool_calls=[read_call]),
                Mock(content="File contains: Test content for workflow", tool_calls=[]),
                Mock(content="Listing directory...", tool_calls=[list_call]),
                Mock(content="Directory contains: workflow_test.txt", tool_calls=[]),
            ]

            provider.chat = Mock(side_effect=responses)

            # Mock model info
            model_info = Mock()
            model_info.id = "test-model"
            model_info.supports_functions = True
            provider.list_models.return_value = [model_info]

            handler = self._create_agent_handler(cli, provider)

            # Add all file operation tools
            from coda.agents.builtin_tools import list_files, read_file, write_file

            with patch.object(
                handler, "get_available_tools", return_value=[read_file, write_file, list_files]
            ):
                # Execute workflow
                messages = [Message(role=Role.USER, content=f"Create a file in {tmpdir}")]
                result1, msgs1 = await handler.chat_with_agent(
                    messages=messages, model="test-model"
                )

                messages = msgs1 + [Message(role=Role.USER, content="Now read it")]
                result2, msgs2 = await handler.chat_with_agent(
                    messages=messages, model="test-model"
                )

                messages = msgs2 + [Message(role=Role.USER, content="List the directory")]
                result3, msgs3 = await handler.chat_with_agent(
                    messages=messages, model="test-model"
                )

                # Verify
                assert "workflow_test.txt" in result3 or "created" in result1.lower()
