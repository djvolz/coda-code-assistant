"""Streamlit event handler for agent events."""

import json
from typing import Any

import streamlit as st

from coda.services.agents.agent_types import AgentEvent, AgentEventHandler, AgentEventType


class StreamlitAgentEventHandler(AgentEventHandler):
    """Handles agent events for Streamlit web interface."""

    def __init__(
        self,
        status_container: Any | None = None,
        message_container: Any | None = None,
    ):
        self.status_container = status_container
        self.message_container = message_container
        self.current_status = None
        self.response_chunks = []

    def handle_event(self, event: AgentEvent) -> None:
        """Handle agent event with appropriate Streamlit rendering."""

        if event.type == AgentEventType.THINKING:
            if self.status_container:
                with self.status_container:
                    self.current_status = st.status("🤔 Thinking...")

        elif event.type == AgentEventType.TOOL_EXECUTION_START:
            if self.status_container:
                with self.status_container:
                    self.current_status = st.status(f"🔧 {event.message}")
                    if event.data and "arguments" in event.data:
                        if self.current_status:
                            with self.current_status:
                                st.json(event.data["arguments"])

        elif event.type == AgentEventType.TOOL_EXECUTION_END:
            if self.current_status:
                try:
                    with self.current_status:
                        st.success("✅ Tool completed")
                        if event.data and "output" in event.data:
                            output = event.data["output"]
                            try:
                                # Try to parse as JSON for better formatting
                                result_json = json.loads(output)
                                st.json(result_json)
                            except Exception:
                                st.text(output)
                except Exception:
                    # If status update fails, try to show output in message container
                    if self.message_container:
                        with self.message_container:
                            st.success("✅ Tool completed")
                            if event.data and "output" in event.data:
                                st.text(str(event.data["output"]))

        elif event.type == AgentEventType.ERROR:
            if self.current_status:
                with self.current_status:
                    st.error(f"❌ {event.message}")
            elif self.message_container:
                with self.message_container:
                    st.error(event.message)

        elif event.type == AgentEventType.WARNING:
            if self.current_status:
                with self.current_status:
                    st.warning(event.message)
            elif self.message_container:
                with self.message_container:
                    st.warning(event.message)

        elif event.type == AgentEventType.STATUS_UPDATE:
            if self.status_container:
                with self.status_container:
                    self.current_status = st.status(event.message)

        elif event.type == AgentEventType.RESPONSE_CHUNK:
            # Collect chunks for streaming display
            self.response_chunks.append(event.message)

        elif event.type == AgentEventType.RESPONSE_COMPLETE:
            # Close any active status
            if self.current_status:
                self.current_status.update(label="✅ Complete", state="complete")

            # Only render if we actually have a response
            if event.message and event.message.strip():
                # Render complete response with any collected chunks
                if self.message_container:
                    full_response = (
                        "".join(self.response_chunks) if self.response_chunks else event.message
                    )
                    with self.message_container:
                        self._render_response(full_response)
            # Clear chunks for next response
            self.response_chunks = []

        elif event.type == AgentEventType.FINAL_ANSWER_NEEDED:
            if self.status_container:
                with self.status_container:
                    st.warning(f"⚠️ {event.message}")

    def _render_response(self, content: str):
        """Render response content with diagram support."""
        # Reuse existing diagram detection logic
        from coda.apps.web.components.chat_widget import render_message_with_code

        render_message_with_code(content)
