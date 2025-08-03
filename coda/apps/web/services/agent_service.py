"""Agent service for web interface."""

import streamlit as st

from coda.apps.web.agent_event_handler import StreamlitAgentEventHandler
from coda.apps.web.utils.state import get_state_value
from coda.base.providers.base import Message, Role
from coda.base.providers.registry import ProviderFactory
from coda.services.agents import Agent
from coda.services.agents.builtin_tools import get_builtin_tools


class WebAgentService:
    """Service for managing agent interactions in web interface."""

    def __init__(self):
        self.agent: Agent | None = None
        self.current_provider: str | None = None
        self.current_model: str | None = None

    def get_or_create_agent(
        self, provider: str, model: str, event_handler: StreamlitAgentEventHandler
    ) -> Agent:
        """Get existing agent or create new one if provider/model changed."""

        if self.agent is None or self.current_provider != provider or self.current_model != model:
            config = get_state_value("config")
            if not config:
                raise ValueError("No configuration available")

            # Create provider instance
            factory = ProviderFactory(config)
            provider_instance = factory.create(provider)

            # Get available tools - allow filtering via session state
            all_tools = get_builtin_tools()
            # Default to all tools if no selection made yet
            default_tool_names = [getattr(tool, "_tool_name", tool.__name__) for tool in all_tools]
            enabled_tool_names = st.session_state.get("enabled_tools", default_tool_names)

            tools = []
            for tool in all_tools:
                tool_name = getattr(tool, "_tool_name", tool.__name__)
                if tool_name in enabled_tool_names:
                    tools.append(tool)

            # Get agent settings from session state
            temperature = st.session_state.get("agent_temperature", 0.7)
            max_tokens = st.session_state.get("agent_max_tokens", 2000)

            # Create agent with event handler
            self.agent = Agent(
                provider=provider_instance,
                model=model,
                instructions="""You are Coda, an AI code assistant. You help users with:
- Code analysis and debugging
- File operations and project management
- Web research and information gathering
- Writing documentation and explanations
- General programming assistance

You have access to various tools to help accomplish tasks. When you use a tool and get results, always incorporate those results into your final response to the user. For example:
- If you call get_datetime and get a timestamp, tell the user what time it is in a readable format
- If you call list_files and get file names, show the user the files
- If you call read_file and get content, include relevant parts in your response

Important: Use tool results directly without trying to parse them as JSON unless they are actually JSON data. Simple strings like timestamps or file paths should be used as-is.

Be direct and helpful by using the tool results to fully answer the user's question.""",
                tools=tools,
                name="Coda Assistant",
                temperature=temperature,
                max_tokens=max_tokens,
                event_handler=event_handler,
            )

            self.current_provider = provider
            self.current_model = model

        return self.agent

    async def get_agent_response(
        self,
        provider: str,
        model: str,
        messages: list[dict[str, str]],
        event_handler: StreamlitAgentEventHandler,
    ) -> str | None:
        """Get response from agent with tool support."""

        try:
            agent = self.get_or_create_agent(provider, model, event_handler)

            # Convert messages to Message objects (excluding the last user message)
            agent_messages = []
            user_input = ""

            for i, msg in enumerate(messages):
                if i == len(messages) - 1 and msg["role"] == "user":
                    # Last user message becomes the input
                    user_input = msg["content"]
                else:
                    role = Role.USER if msg["role"] == "user" else Role.ASSISTANT
                    agent_messages.append(Message(role=role, content=msg["content"]))

            # Debug: Log what we're sending to the agent
            if hasattr(st, "_debug_mode"):  # Only in debug mode
                st.write("**Debug - Sending to agent:**")
                st.write(f"Input: {user_input}")
                st.write(f"Message history length: {len(agent_messages)}")

            # Get response from agent using run_async_streaming
            try:
                response_content, updated_messages = await agent.run_async_streaming(
                    input=user_input,
                    messages=agent_messages if agent_messages else None,
                    max_steps=5,
                )

                # Debug: Show final response info
                if hasattr(st, "_debug_mode"):  # Only in debug mode
                    st.write("**Debug - Agent response:**")
                    st.write(f"Response content: {response_content}")
                    st.write(f"Final message count: {len(updated_messages)}")

                # Ensure the final response is displayed immediately
                if response_content and event_handler.message_container:
                    with event_handler.message_container:
                        event_handler._render_response(response_content)

                return response_content

            except Exception as agent_error:
                st.error(f"Agent execution error: {str(agent_error)}")
                st.write("**Error details:**")
                st.write(f"Error type: {type(agent_error).__name__}")
                st.write(f"Error message: {str(agent_error)}")
                import traceback

                st.code(traceback.format_exc())
                return None

        except Exception as e:
            st.error(f"Agent error: {str(e)}")
            return None


# Global service instance
_agent_service = WebAgentService()


def get_agent_service() -> WebAgentService:
    """Get the global agent service instance."""
    return _agent_service
