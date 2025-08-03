"""Tests for Streamlit agent event handler."""

import json
from unittest.mock import Mock, patch

from coda.apps.web.agent_event_handler import StreamlitAgentEventHandler
from coda.services.agents.agent_types import AgentEvent, AgentEventType


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
    def test_init_with_containers(self, mock_st):
        """Test initialization with containers."""
        handler = StreamlitAgentEventHandler(
            status_container=self.status_container, message_container=self.message_container
        )

        assert handler.status_container == self.status_container
        assert handler.message_container == self.message_container
        assert handler.current_status is None
        assert handler.response_chunks == []

    @patch("coda.apps.web.agent_event_handler.st")
    def test_init_without_containers(self, mock_st):
        """Test initialization without containers."""
        handler = StreamlitAgentEventHandler()

        assert handler.status_container is None
        assert handler.message_container is None

    @patch("coda.apps.web.agent_event_handler.st")
    def test_thinking_event(self, mock_st):
        """Test thinking event handling."""
        mock_status = Mock()
        mock_st.status.return_value = mock_status

        event = AgentEvent(type=AgentEventType.THINKING, message="Analyzing the code...")

        self.handler.handle_event(event)

        # Verify status container context manager was used
        self.status_container.__enter__.assert_called_once()
        self.status_container.__exit__.assert_called_once()

    @patch("coda.apps.web.agent_event_handler.st")
    def test_tool_execution_start_with_arguments(self, mock_st):
        """Test tool execution start with arguments."""
        mock_status = Mock()
        mock_st.status.return_value = mock_status

        event = AgentEvent(
            type=AgentEventType.TOOL_EXECUTION_START,
            message="Running file_read",
            data={"arguments": {"file_path": "test.py", "lines": 10}},
        )

        self.handler.handle_event(event)

        # Verify status was created
        self.status_container.__enter__.assert_called_once()

    @patch("coda.apps.web.agent_event_handler.st")
    def test_tool_execution_start_without_arguments(self, mock_st):
        """Test tool execution start without arguments."""
        event = AgentEvent(type=AgentEventType.TOOL_EXECUTION_START, message="Running simple tool")

        self.handler.handle_event(event)

        self.status_container.__enter__.assert_called_once()

    @patch("coda.apps.web.agent_event_handler.st")
    def test_tool_execution_end_with_json_output(self, mock_st):
        """Test tool execution end with JSON output."""
        # Set up current status
        mock_status = Mock()
        self.handler.current_status = mock_status

        output_data = {"files": ["test.py", "main.py"], "count": 2}
        event = AgentEvent(
            type=AgentEventType.TOOL_EXECUTION_END,
            message="Tool completed",
            data={"output": json.dumps(output_data)},
        )

        self.handler.handle_event(event)

        # Verify current status context was used
        mock_status.__enter__.assert_called_once()

    @patch("coda.apps.web.agent_event_handler.st")
    def test_tool_execution_end_with_text_output(self, mock_st):
        """Test tool execution end with text output."""
        mock_status = Mock()
        self.handler.current_status = mock_status

        event = AgentEvent(
            type=AgentEventType.TOOL_EXECUTION_END,
            message="Tool completed",
            data={"output": "File contents here..."},
        )

        self.handler.handle_event(event)

        mock_status.__enter__.assert_called_once()

    @patch("coda.apps.web.agent_event_handler.st")
    def test_error_event_with_current_status(self, mock_st):
        """Test error event when there's a current status."""
        mock_status = Mock()
        self.handler.current_status = mock_status

        event = AgentEvent(type=AgentEventType.ERROR, message="File not found")

        self.handler.handle_event(event)

        mock_status.__enter__.assert_called_once()

    @patch("coda.apps.web.agent_event_handler.st")
    def test_error_event_without_current_status(self, mock_st):
        """Test error event when there's no current status."""
        event = AgentEvent(type=AgentEventType.ERROR, message="Network timeout")

        self.handler.handle_event(event)

        self.message_container.__enter__.assert_called_once()

    @patch("coda.apps.web.agent_event_handler.st")
    def test_warning_event(self, mock_st):
        """Test warning event handling."""
        mock_status = Mock()
        self.handler.current_status = mock_status

        event = AgentEvent(type=AgentEventType.WARNING, message="Large file detected")

        self.handler.handle_event(event)

        mock_status.__enter__.assert_called_once()

    @patch("coda.apps.web.agent_event_handler.st")
    def test_status_update_event(self, mock_st):
        """Test status update event."""
        mock_status = Mock()
        mock_st.status.return_value = mock_status

        event = AgentEvent(type=AgentEventType.STATUS_UPDATE, message="Processing file 2 of 5")

        self.handler.handle_event(event)

        self.status_container.__enter__.assert_called_once()

    def test_response_chunk_event(self):
        """Test response chunk event."""
        event = AgentEvent(type=AgentEventType.RESPONSE_CHUNK, message="This is ")

        self.handler.handle_event(event)

        assert self.handler.response_chunks == ["This is "]

        # Add another chunk
        event2 = AgentEvent(type=AgentEventType.RESPONSE_CHUNK, message="a test")

        self.handler.handle_event(event2)

        assert self.handler.response_chunks == ["This is ", "a test"]

    @patch("coda.apps.web.agent_event_handler.st")
    @patch("coda.apps.web.agent_event_handler.render_message_with_code")
    def test_response_complete_with_chunks(self, mock_render, mock_st):
        """Test response complete with collected chunks."""
        # Set up chunks and current status
        self.handler.response_chunks = ["Hello ", "world!"]
        mock_status = Mock()
        self.handler.current_status = mock_status

        event = AgentEvent(type=AgentEventType.RESPONSE_COMPLETE, message="Final message")

        self.handler.handle_event(event)

        # Verify status was updated
        mock_status.update.assert_called_once_with(label="✅ Complete", state="complete")

        # Verify message was rendered with combined chunks
        mock_render.assert_called_once_with("Hello world!")
        self.message_container.__enter__.assert_called_once()

    @patch("coda.apps.web.agent_event_handler.st")
    @patch("coda.apps.web.agent_event_handler.render_message_with_code")
    def test_response_complete_without_chunks(self, mock_render, mock_st):
        """Test response complete without chunks."""
        mock_status = Mock()
        self.handler.current_status = mock_status

        event = AgentEvent(type=AgentEventType.RESPONSE_COMPLETE, message="Direct message")

        self.handler.handle_event(event)

        # Verify message from event was used
        mock_render.assert_called_once_with("Direct message")

    @patch("coda.apps.web.agent_event_handler.st")
    def test_final_answer_needed_event(self, mock_st):
        """Test final answer needed event."""
        event = AgentEvent(
            type=AgentEventType.FINAL_ANSWER_NEEDED, message="Please provide final answer"
        )

        self.handler.handle_event(event)

        self.status_container.__enter__.assert_called_once()

    @patch("coda.apps.web.agent_event_handler.render_message_with_code")
    def test_render_response(self, mock_render):
        """Test _render_response method."""
        content = "Test content with code"

        self.handler._render_response(content)

        mock_render.assert_called_once_with(content)

    def test_event_handling_without_containers(self):
        """Test event handling when containers are None."""
        handler = StreamlitAgentEventHandler()

        # Should not raise errors
        events = [
            AgentEvent(AgentEventType.THINKING, "thinking"),
            AgentEvent(AgentEventType.ERROR, "error"),
            AgentEvent(AgentEventType.WARNING, "warning"),
            AgentEvent(AgentEventType.RESPONSE_CHUNK, "chunk"),
        ]

        for event in events:
            handler.handle_event(event)  # Should not crash
