"""Tool configuration UI for web interface."""

import streamlit as st

from coda.services.agents.builtin_tools import get_builtin_tools


def render_tool_settings():
    """Render tool configuration interface."""

    st.subheader("🔧 Available Tools")

    # Get available tools
    tools = get_builtin_tools()

    if not tools:
        st.info("No tools available")
        return

    # Tool selection - extract names from function tools
    tool_names = []
    for tool in tools:
        if hasattr(tool, "_tool_name"):
            tool_names.append(tool._tool_name)
        else:
            tool_names.append(tool.__name__)
    selected_tools = st.multiselect(
        "Select tools to enable:",
        options=tool_names,
        default=tool_names,  # All tools enabled by default
        help="Tools provide additional capabilities like file operations, web search, etc.",
    )

    # Store selection in session state
    st.session_state.enabled_tools = selected_tools

    # Tool descriptions
    if st.expander("📖 Tool Descriptions", expanded=False):
        for tool in tools:
            tool_name = getattr(tool, "_tool_name", tool.__name__)
            if tool_name in selected_tools:
                tool_description = getattr(
                    tool, "_tool_description", tool.__doc__ or "No description available"
                )
                st.write(f"**{tool_name}**: {tool_description}")


def get_enabled_tools():
    """Get list of enabled tools from session state."""
    enabled_tool_names = st.session_state.get("enabled_tools", [])
    all_tools = get_builtin_tools()
    filtered_tools = []

    for tool in all_tools:
        tool_name = getattr(tool, "_tool_name", tool.__name__)
        if tool_name in enabled_tool_names:
            filtered_tools.append(tool)

    return filtered_tools


def render_agent_settings():
    """Render agent configuration settings."""
    st.subheader("🎛️ Agent Settings")

    # Agent mode toggle
    use_agent = st.checkbox(
        "Enable Agent Mode",
        value=st.session_state.get("use_agent", True),
        help="Use the agent system with tools, or fallback to direct provider responses",
    )
    st.session_state.use_agent = use_agent

    if use_agent:
        # Temperature setting
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=2.0,
            value=st.session_state.get("agent_temperature", 0.7),
            step=0.1,
            help="Controls randomness in responses. Lower values are more focused and deterministic.",
        )
        st.session_state.agent_temperature = temperature

        # Max tokens setting
        max_tokens = st.slider(
            "Max Tokens",
            min_value=100,
            max_value=4000,
            value=st.session_state.get("agent_max_tokens", 2000),
            step=100,
            help="Maximum number of tokens in the response.",
        )
        st.session_state.agent_max_tokens = max_tokens

        # Tools configuration
        st.markdown("---")
        render_tool_settings()

        # Show enabled tools count
        enabled_tools = st.session_state.get("enabled_tools", [])
        st.info(f"✅ {len(enabled_tools)} tools enabled")
    else:
        st.info("🔄 Using direct provider mode (no tools available)")
