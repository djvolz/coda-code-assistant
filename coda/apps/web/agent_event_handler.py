"""Streamlit event handler for agent events."""

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
        self.response_chunks = []
        self.current_status = None
        self.current_tool_name = None

    def handle_event(self, event: AgentEvent) -> None:
        """Handle agent event with appropriate Streamlit rendering."""
        try:
            if event.type == AgentEventType.THINKING:
                if self.status_container:
                    with self.status_container:
                        st.info("🤔 Thinking...")

            elif event.type == AgentEventType.TOOL_EXECUTION_START:
                if self.status_container:
                    with self.status_container:
                        tool_name = event.message.replace("Running tool: ", "")
                        st.info(f"🔧 Executing {tool_name}...")

            elif event.type == AgentEventType.TOOL_EXECUTION_END:
                if self.status_container:
                    with self.status_container:
                        tool_name = (
                            event.message.replace("Running tool: ", "") if event.message else "tool"
                        )
                        st.success(f"✅ {tool_name} completed")
                        if event.data and "output" in event.data:
                            output = event.data["output"]
                            # Simple output display
                            st.text(f"Result: {output}")

            elif event.type == AgentEventType.ERROR:
                if self.status_container:
                    with self.status_container:
                        st.error(f"❌ Error: {event.message}")

            elif event.type == AgentEventType.RESPONSE_CHUNK:
                # Just collect chunks
                self.response_chunks.append(event.message)

            elif event.type == AgentEventType.RESPONSE_COMPLETE:
                # Just clear chunks
                self.response_chunks = []

        except Exception as e:
            print(f"Event handler error: {str(e)}")
            import traceback

            print(traceback.format_exc())

    def _render_response(self, content: str):
        """Render response content with diagram support."""
        # Reuse existing diagram detection logic
        from coda.apps.web.components.chat_widget import render_message_with_code

        render_message_with_code(content)
