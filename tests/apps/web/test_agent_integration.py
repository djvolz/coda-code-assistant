"""Tests for web agent integration."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from coda.apps.web.agent_event_handler import StreamlitAgentEventHandler
from coda.apps.web.services.agent_service import WebAgentService, get_agent_service
from coda.services.agents.agent_types import AgentEvent, AgentEventType


class TestWebAgentService:
    """Test WebAgentService functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.service = WebAgentService()

    @patch("coda.apps.web.services.agent_service.get_state_value")
    @patch("coda.apps.web.services.agent_service.ProviderFactory")
    @patch("coda.apps.web.services.agent_service.get_builtin_tools")
    @patch("coda.apps.web.services.agent_service.Agent")
    def test_get_or_create_agent(self, mock_agent, mock_tools, mock_factory, mock_get_state):
        """Test agent creation and caching."""
        # Mock dependencies
        mock_get_state.return_value = {"providers": {"test": {"enabled": True}}}
        mock_provider = Mock()
        mock_factory.return_value.create.return_value = mock_provider
        mock_tools.return_value = [Mock(name="test_tool")]
        mock_agent_instance = Mock()
        mock_agent.return_value = mock_agent_instance

        # Mock event handler
        event_handler = Mock()

        # Test first call creates agent
        agent = self.service.get_or_create_agent("test", "model", event_handler)

        assert agent == mock_agent_instance
        assert self.service.current_provider == "test"
        assert self.service.current_model == "model"
        mock_agent.assert_called_once()

        # Test second call returns cached agent
        mock_agent.reset_mock()
        agent2 = self.service.get_or_create_agent("test", "model", event_handler)

        assert agent2 == mock_agent_instance
        mock_agent.assert_not_called()

        # Test different provider creates new agent
        agent3 = self.service.get_or_create_agent("test2", "model", event_handler)

        assert agent3 == mock_agent_instance
        mock_agent.assert_called_once()

    @patch("coda.apps.web.services.agent_service.st")
    @patch.object(WebAgentService, "get_or_create_agent")
    async def test_get_agent_response_success(self, mock_get_agent, mock_st):
        """Test successful agent response."""
        # Mock agent
        mock_agent = Mock()
        mock_response = Mock()
        mock_response.content = "Test response"
        mock_agent.arun = AsyncMock(return_value=mock_response)
        mock_get_agent.return_value = mock_agent

        # Mock event handler
        event_handler = Mock()

        # Test messages
        messages = [{"role": "user", "content": "Hello"}]

        result = await self.service.get_agent_response("test", "model", messages, event_handler)

        assert result == "Test response"
        mock_agent.arun.assert_called_once()

    @patch("coda.apps.web.services.agent_service.st")
    @patch.object(WebAgentService, "get_or_create_agent")
    async def test_get_agent_response_error(self, mock_get_agent, mock_st):
        """Test agent response with error."""
        # Mock agent to raise exception
        mock_agent = Mock()
        mock_agent.arun = AsyncMock(side_effect=Exception("Test error"))
        mock_get_agent.return_value = mock_agent

        # Mock event handler
        event_handler = Mock()

        # Test messages
        messages = [{"role": "user", "content": "Hello"}]

        result = await self.service.get_agent_response("test", "model", messages, event_handler)

        assert result is None
        mock_st.error.assert_called_with("Agent error: Test error")

    def test_get_agent_service_singleton(self):
        """Test that get_agent_service returns singleton."""
        service1 = get_agent_service()
        service2 = get_agent_service()

        assert service1 is service2
        assert isinstance(service1, WebAgentService)


class TestStreamlitAgentEventHandler:
    """Test StreamlitAgentEventHandler functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.status_container = Mock()
        self.message_container = Mock()
        self.handler = StreamlitAgentEventHandler(
            status_container=self.status_container, message_container=self.message_container
        )

    @patch("coda.apps.web.agent_event_handler.st")
    def test_handle_thinking_event(self, mock_st):
        """Test handling thinking event."""
        event = AgentEvent(type=AgentEventType.THINKING, message="Thinking about the problem...")

        self.handler.handle_event(event)

        # Verify status container was used
        self.status_container.__enter__.assert_called()

    @patch("coda.apps.web.agent_event_handler.st")
    def test_handle_tool_execution_start(self, mock_st):
        """Test handling tool execution start event."""
        event = AgentEvent(
            type=AgentEventType.TOOL_EXECUTION_START,
            message="Running file_read tool",
            data={"arguments": {"file": "test.py"}},
        )

        self.handler.handle_event(event)

        # Verify status container was used
        self.status_container.__enter__.assert_called()

    @patch("coda.apps.web.agent_event_handler.st")
    def test_handle_tool_execution_end(self, mock_st):
        """Test handling tool execution end event."""
        # Set up a current status
        self.handler.current_status = Mock()

        event = AgentEvent(
            type=AgentEventType.TOOL_EXECUTION_END,
            message="Tool completed",
            data={"output": '{"result": "success"}'},
        )

        self.handler.handle_event(event)

        # Verify current status was used
        self.handler.current_status.__enter__.assert_called()

    @patch("coda.apps.web.agent_event_handler.st")
    def test_handle_error_event(self, mock_st):
        """Test handling error event."""
        event = AgentEvent(type=AgentEventType.ERROR, message="Something went wrong")

        # Test with current status
        self.handler.current_status = Mock()
        self.handler.handle_event(event)

        self.handler.current_status.__enter__.assert_called()

    @patch("coda.apps.web.agent_event_handler.st")
    def test_handle_response_chunk(self, mock_st):
        """Test handling response chunk event."""
        event = AgentEvent(type=AgentEventType.RESPONSE_CHUNK, message="This is a chunk")

        self.handler.handle_event(event)

        assert "This is a chunk" in self.handler.response_chunks

    @patch("coda.apps.web.agent_event_handler.st")
    @patch("coda.apps.web.agent_event_handler.render_message_with_code")
    def test_handle_response_complete(self, mock_render, mock_st):
        """Test handling response complete event."""
        # Add some chunks
        self.handler.response_chunks = ["Hello", " world"]
        self.handler.current_status = Mock()

        event = AgentEvent(type=AgentEventType.RESPONSE_COMPLETE, message="Complete")

        self.handler.handle_event(event)

        # Verify status was updated
        self.handler.current_status.update.assert_called_with(label="✅ Complete", state="complete")

        # Verify message was rendered
        mock_render.assert_called_with("Hello world")


@pytest.mark.integration
class TestWebAgentIntegration:
    """Integration tests for web agent functionality."""

    @patch("coda.apps.web.services.agent_service.get_state_value")
    @patch("coda.apps.web.services.agent_service.ProviderFactory")
    @patch("coda.apps.web.services.agent_service.get_builtin_tools")
    @patch("coda.apps.web.services.agent_service.st")
    async def test_full_agent_workflow(self, mock_st, mock_tools, mock_factory, mock_get_state):
        """Test full agent workflow from request to response."""
        # Mock session state for tools
        mock_st.session_state.get.return_value = ["test_tool"]

        # Mock dependencies
        mock_get_state.return_value = {"providers": {"test": {"enabled": True}}}
        mock_provider = Mock()
        mock_factory.return_value.create.return_value = mock_provider

        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tools.return_value = [mock_tool]

        # Mock agent
        with patch("coda.apps.web.services.agent_service.Agent") as mock_agent_class:
            mock_agent = Mock()
            mock_response = Mock()
            mock_response.content = "Agent response"
            mock_agent.arun = AsyncMock(return_value=mock_response)
            mock_agent_class.return_value = mock_agent

            # Test service
            service = WebAgentService()
            event_handler = StreamlitAgentEventHandler()

            messages = [{"role": "user", "content": "Hello"}]
            result = await service.get_agent_response("test", "model", messages, event_handler)

            assert result == "Agent response"
            mock_agent.arun.assert_called_once()

            # Verify agent was created with correct parameters
            mock_agent_class.assert_called_once()
            call_args = mock_agent_class.call_args
            assert call_args[1]["provider"] == mock_provider
            assert call_args[1]["model"] == "model"
            assert call_args[1]["tools"] == [mock_tool]
            assert call_args[1]["event_handler"] == event_handler
