"""Additional tests to improve coverage for agent.py."""

from unittest.mock import Mock, patch

import pytest
from rich.console import Console

from coda.agents.agent import Agent
from coda.agents.decorators import tool
from coda.agents.function_tool import FunctionTool
from coda.agents.types import (
    PerformedActionType,
)
from coda.providers.base import BaseProvider, ChatCompletion, Message, Model, Role, Tool, ToolCall


@pytest.mark.unit
@pytest.mark.fast
class TestAgentAdditional:
    """Additional tests to improve agent coverage."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock provider."""
        provider = Mock(spec=BaseProvider)
        provider.list_models.return_value = [
            Model(
                id="test.model",
                name="Test Model",
                provider="test",
                context_length=4096,
                max_tokens=1024,
                supports_streaming=True,
                supports_functions=True,
            )
        ]
        provider.chat.return_value = ChatCompletion(
            content="Test response", model="test.model", finish_reason="stop"
        )
        return provider

    @pytest.fixture
    def sample_tool(self):
        """Create a sample tool function."""

        @tool
        def sample_function(text: str) -> str:
            """A sample tool function.

            Args:
                text: Input text

            Returns:
                Processed text
            """
            return f"Processed: {text}"

        return sample_function

    @pytest.fixture
    def agent(self, mock_provider, sample_tool):
        """Create an agent instance."""
        return Agent(
            provider=mock_provider,
            model="test.model",
            instructions="Test instructions",
            tools=[sample_tool],
            name="Test Agent",
            description="A test agent",
            temperature=0.5,
            max_tokens=1000,
        )

    def test_init_with_minimal_params(self, mock_provider):
        """Test agent initialization with minimal parameters."""
        agent = Agent(provider=mock_provider, model="test.model")

        assert agent.provider == mock_provider
        assert agent.model == "test.model"
        assert agent.instructions == "You are a helpful assistant"
        assert agent.tools == []
        assert agent.name == "Agent"
        assert agent.description is None
        assert agent.temperature == 0.7
        assert agent.max_tokens == 2000

    def test_init_with_all_params(self, mock_provider, sample_tool):
        """Test agent initialization with all parameters."""
        console = Console()
        agent = Agent(
            provider=mock_provider,
            model="test.model",
            instructions="Custom instructions",
            tools=[sample_tool],
            name="Custom Agent",
            description="Custom description",
            temperature=0.9,
            max_tokens=500,
            console=console,
            custom_param="value",
        )

        assert agent.provider == mock_provider
        assert agent.model == "test.model"
        assert agent.instructions == "Custom instructions"
        assert len(agent.tools) == 1
        assert agent.name == "Custom Agent"
        assert agent.description == "Custom description"
        assert agent.temperature == 0.9
        assert agent.max_tokens == 500
        assert agent.console == console
        assert agent.kwargs == {"custom_param": "value"}

    def test_process_tools_with_function_tool(self, mock_provider):
        """Test processing tools when FunctionTool is provided."""
        func_tool = FunctionTool(
            name="test_tool",
            description="Test tool",
            callable=lambda x: x,
            parameters={"type": "object", "properties": {}},
        )

        agent = Agent(provider=mock_provider, model="test.model", tools=[func_tool])

        assert len(agent._function_tools) == 1
        assert agent._function_tools[0] == func_tool
        assert "test_tool" in agent._tool_map

    def test_process_tools_with_undecorated_callable(self, mock_provider):
        """Test processing tools with undecorated callable."""

        def undecorated_func():
            """Undecorated function."""
            pass

        with patch.object(Console, "print") as mock_print:
            agent = Agent(provider=mock_provider, model="test.model", tools=[undecorated_func])

            # Should print warning
            mock_print.assert_called_once()
            assert "not decorated with @tool" in str(mock_print.call_args)
            assert len(agent._function_tools) == 0

    def test_get_provider_tools(self, agent):
        """Test converting FunctionTools to provider Tool format."""
        provider_tools = agent._get_provider_tools()

        assert len(provider_tools) == 1
        assert isinstance(provider_tools[0], Tool)
        assert provider_tools[0].name == "sample_function"
        assert provider_tools[0].description.startswith("A sample tool function.")

    @pytest.mark.asyncio
    async def test_run_async_simple_response(self, agent):
        """Test run_async with simple response (no tools)."""
        response = await agent.run_async("Hello")

        assert response.data["content"] == "Test response"
        assert response.data["model"] == "test.model"

        # Check that provider.chat was called
        agent.provider.chat.assert_called_once()
        call_args = agent.provider.chat.call_args
        messages = call_args[1]["messages"]

        # First call should have system and user messages
        assert len(messages) == 2
        assert messages[0].role == Role.SYSTEM
        assert messages[0].content == "Test instructions"
        assert messages[1].role == Role.USER
        assert messages[1].content == "Hello"

        # Response data should contain the full message history
        assert len(response.data["messages"]) == 3  # system, user, assistant

    @pytest.mark.asyncio
    async def test_run_async_with_existing_messages(self, agent):
        """Test run_async with existing message history."""
        existing_messages = [
            Message(role=Role.USER, content="Previous question"),
            Message(role=Role.ASSISTANT, content="Previous answer"),
        ]

        response = await agent.run_async("New question", messages=existing_messages)

        assert response.content == "Test response"

        # Check messages passed to provider
        call_args = agent.provider.chat.call_args
        messages = call_args[1]["messages"]

        # Should have system + existing + new user message
        assert len(messages) == 4
        assert messages[0].role == Role.SYSTEM  # System instructions added
        assert messages[1].content == "Previous question"
        assert messages[2].content == "Previous answer"
        assert messages[3].content == "New question"

    @pytest.mark.asyncio
    async def test_run_async_with_system_message_already_present(self, agent):
        """Test run_async when system message already exists."""
        existing_messages = [
            Message(role=Role.SYSTEM, content="Existing system message"),
            Message(role=Role.USER, content="Previous question"),
        ]

        await agent.run_async("New question", messages=existing_messages)

        # Check messages - should not add duplicate system message
        call_args = agent.provider.chat.call_args
        messages = call_args[1]["messages"]

        assert len(messages) == 3
        assert messages[0].content == "Existing system message"
        assert messages[2].content == "New question"

    @pytest.mark.asyncio
    async def test_run_async_with_tool_calls(self, agent):
        """Test run_async with tool calls."""
        # Mock provider to return tool calls
        tool_call = ToolCall(
            id="call_123", name="sample_function", arguments='{"text": "test input"}'
        )

        agent.provider.chat.side_effect = [
            # First response with tool call
            ChatCompletion(
                content="", model="test.model", finish_reason="tool_calls", tool_calls=[tool_call]
            ),
            # Second response after tool execution
            ChatCompletion(
                content="Final response with tool result", model="test.model", finish_reason="stop"
            ),
        ]

        # Mock callback
        mock_callback = Mock()

        response = await agent.run_async("Process this text", on_fulfilled_action=mock_callback)

        assert response.content == "Final response with tool result"
        assert len(response.performed_actions) == 1
        assert response.performed_actions[0].type == PerformedActionType.TOOL_CALL

        # Check callback was called
        mock_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_async_model_without_tool_support(self, mock_provider):
        """Test run_async when model doesn't support tools."""
        # Mock model without tool support
        mock_provider.list_models.return_value = [
            Model(
                id="test.model",
                name="Test Model",
                provider="test",
                context_length=4096,
                max_tokens=1024,
                supports_streaming=True,
                supports_functions=False,  # No tool support
            )
        ]

        @tool
        def dummy_tool(x: str) -> str:
            """Dummy tool."""
            return x

        agent = Agent(provider=mock_provider, model="test.model", tools=[dummy_tool])

        await agent.run_async("Test")

        # Should not pass tools to provider
        call_args = mock_provider.chat.call_args
        assert "tools" not in call_args[1]

    @pytest.mark.asyncio
    async def test_run_async_max_steps_limit(self, agent):
        """Test run_async respects max_steps limit."""
        # Mock provider to always return tool calls
        tool_call = ToolCall(id="call_123", name="sample_function", arguments='{"text": "test"}')

        agent.provider.chat.return_value = ChatCompletion(
            content="", model="test.model", finish_reason="tool_calls", tool_calls=[tool_call]
        )

        response = await agent.run_async("Test", max_steps=2)

        # Should stop after max_steps
        assert agent.provider.chat.call_count == 2
        assert len(response.performed_actions) == 2

    @pytest.mark.asyncio
    async def test_run_async_tool_execution_error(self, mock_provider):
        """Test run_async handles tool execution errors."""

        @tool
        def error_tool(x: str) -> str:
            """Tool that raises error."""
            raise ValueError("Tool error")

        agent = Agent(provider=mock_provider, model="test.model", tools=[error_tool])

        tool_call = ToolCall(id="call_123", name="error_tool", arguments='{"x": "test"}')

        agent.provider.chat.side_effect = [
            ChatCompletion(
                content="", model="test.model", finish_reason="tool_calls", tool_calls=[tool_call]
            ),
            ChatCompletion(content="Error handled", model="test.model", finish_reason="stop"),
        ]

        response = await agent.run_async("Test")

        assert response.content == "Error handled"
        assert len(response.performed_actions) == 1
        assert "error" in response.performed_actions[0].output.lower()

    @pytest.mark.asyncio
    async def test_run_async_tool_call_loop_detection(self, agent):
        """Test run_async detects tool call loops."""
        # Mock provider to return same tool call repeatedly
        tool_call = ToolCall(id="call_123", name="sample_function", arguments='{"text": "test"}')

        agent.provider.chat.side_effect = [
            # Return same tool call 3 times
            ChatCompletion(
                content="", model="test.model", finish_reason="tool_calls", tool_calls=[tool_call]
            ),
            ChatCompletion(
                content="", model="test.model", finish_reason="tool_calls", tool_calls=[tool_call]
            ),
            ChatCompletion(
                content="", model="test.model", finish_reason="tool_calls", tool_calls=[tool_call]
            ),
            # Final response after loop detection
            ChatCompletion(content="Loop broken", model="test.model", finish_reason="stop"),
        ]

        with patch.object(agent.console, "print") as mock_print:
            response = await agent.run_async("Test")

            # Should detect loop and print warning
            assert any("Loop detected" in str(call) for call in mock_print.call_args_list)
            assert response.content == "Loop broken"

    def test_detect_tool_call_loops(self, agent):
        """Test tool call loop detection logic."""
        # Test no loop - different tools
        tool_calls = [ToolCall(id="1", name="tool1", arguments="{}")]
        recent_calls = [
            [ToolCall(id="2", name="tool2", arguments="{}")],
            [ToolCall(id="3", name="tool3", arguments="{}")],
        ]

        assert not agent._detect_tool_call_loops(tool_calls, recent_calls, 3, 2)

        # Test loop detected - same tool called multiple times
        tool_calls = [ToolCall(id="4", name="tool1", arguments="{}")]
        recent_calls = [
            [ToolCall(id="1", name="tool1", arguments="{}")],
            [ToolCall(id="2", name="tool1", arguments="{}")],
        ]

        assert agent._detect_tool_call_loops(tool_calls, recent_calls, 3, 2)

    def test_execute_tool_calls(self, agent):
        """Test executing tool calls."""
        tool_calls = [ToolCall(id="1", name="sample_function", arguments='{"text": "hello"}')]

        results = agent._execute_tool_calls(tool_calls)

        assert len(results) == 1
        assert results[0]["tool_call_id"] == "1"
        assert results[0]["output"] == "Processed: hello"

    def test_execute_tool_calls_invalid_json(self, agent):
        """Test executing tool calls with invalid JSON arguments."""
        tool_calls = [ToolCall(id="1", name="sample_function", arguments="invalid json")]

        results = agent._execute_tool_calls(tool_calls)

        assert len(results) == 1
        assert "error" in results[0]["output"].lower()
        assert "JSON" in results[0]["output"]

    def test_execute_tool_calls_unknown_tool(self, agent):
        """Test executing tool calls with unknown tool."""
        tool_calls = [ToolCall(id="1", name="unknown_tool", arguments="{}")]

        results = agent._execute_tool_calls(tool_calls)

        assert len(results) == 1
        assert "not found" in results[0]["output"]

    def test_create_tool_message(self, agent):
        """Test creating tool result message."""
        tool_results = [
            {"tool_call_id": "1", "output": "Result 1"},
            {"tool_call_id": "2", "output": "Result 2"},
        ]

        message = agent._create_tool_message(tool_results)

        assert message.role == Role.TOOL
        assert "Result 1" in message.content
        assert "Result 2" in message.content

    @pytest.mark.asyncio
    async def test_run_async_with_status_indicator(self, agent):
        """Test run_async with status indicator."""
        mock_status = Mock()

        response = await agent.run_async("Test", status=mock_status)

        assert response.data["content"] == "Test response"
        # Status should be updated during execution
        mock_status.update.assert_called()

    @pytest.mark.asyncio
    async def test_run_async_empty_instructions(self, mock_provider):
        """Test run_async with empty instructions."""
        agent = Agent(
            provider=mock_provider, model="test.model", instructions=""  # Empty instructions
        )

        await agent.run_async("Test")

        # Should not add system message for empty instructions
        call_args = mock_provider.chat.call_args
        messages = call_args[1]["messages"]

        assert len(messages) == 1
        assert messages[0].role == Role.USER

    @pytest.mark.asyncio
    async def test_run_async_provider_exception(self, agent):
        """Test run_async handles provider exceptions."""
        agent.provider.chat.side_effect = Exception("Provider error")

        with pytest.raises(Exception, match="Provider error"):
            await agent.run_async("Test")

    def test_run_sync(self, agent):
        """Test synchronous run method."""
        # The run method should exist and wrap run_async
        result = agent.run("Test sync")

        assert result.content == "Test response"
        agent.provider.chat.assert_called_once()

    def test_run_sync_with_all_params(self, agent):
        """Test synchronous run with all parameters."""
        mock_callback = Mock()
        existing_messages = [Message(role=Role.USER, content="Previous")]

        result = agent.run(
            "Test", messages=existing_messages, max_steps=5, on_fulfilled_action=mock_callback
        )

        assert result.content == "Test response"
