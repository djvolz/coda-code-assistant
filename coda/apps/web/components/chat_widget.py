"""Chat interface widget component."""

import asyncio
import re
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

from coda.apps.web.agent_event_handler import StreamlitAgentEventHandler
from coda.apps.web.services.agent_service import get_agent_service
from coda.apps.web.utils.state import get_state_value, set_state_value
from coda.base.providers.registry import ProviderFactory

try:
    from diagram_renderer import DiagramRenderer

    DIAGRAM_RENDERER_AVAILABLE = True
except ImportError:
    DIAGRAM_RENDERER_AVAILABLE = False


def render_chat_interface(provider: str, model: str):
    """Render the main chat interface."""
    messages = st.session_state.get("messages", [])

    chat_container = st.container()

    with chat_container:
        for message in messages:
            with st.chat_message(message["role"]):
                # Always use render_message_with_code to handle both diagrams and regular code
                render_message_with_code(message["content"])

    if prompt := st.chat_input("Type your message here..."):
        # Check for uploaded files and include in context
        uploaded_files = st.session_state.get("uploaded_files", [])
        if uploaded_files:
            from coda.apps.web.components.file_manager import create_file_context_prompt

            file_context = create_file_context_prompt(uploaded_files)
            full_prompt = file_context + prompt
            st.session_state.uploaded_files = []  # Clear after use
        else:
            full_prompt = prompt

        messages.append({"role": "user", "content": full_prompt})
        st.session_state.messages = messages

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            # Create containers for agent events
            status_container = st.container()
            message_container = st.container()

            # Create event handler
            event_handler = StreamlitAgentEventHandler(
                status_container=status_container, message_container=message_container
            )

            # Get agent service and response
            agent_service = get_agent_service()

            # Check if agent mode is enabled (default to True for new feature)
            use_agent = st.session_state.get("use_agent", True)

            if use_agent:
                # Run async agent response
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    response = loop.run_until_complete(
                        agent_service.get_agent_response(provider, model, messages, event_handler)
                    )

                    if response:
                        messages.append({"role": "assistant", "content": response})
                        st.session_state.messages = messages
                        save_to_session(provider, model, messages)
                    else:
                        st.error("Failed to get response from agent")

                except Exception as e:
                    st.error(f"Agent service error: {str(e)}")
                    st.write("**Error details:**")
                    st.write(f"Error type: {type(e).__name__}")
                    import traceback

                    st.code(traceback.format_exc())

                finally:
                    loop.close()
            else:
                # Fallback to direct provider response
                with st.spinner("Thinking..."):
                    response = get_ai_response_fallback(provider, model, messages)
                    if response:
                        # Always use render_message_with_code to handle both diagrams and regular code
                        render_message_with_code(response)

                        messages.append({"role": "assistant", "content": response})
                        st.session_state.messages = messages

                        save_to_session(provider, model, messages)
                    else:
                        st.error("Failed to get response from AI")


def detect_diagram_code(content: str) -> list[tuple[str, str]]:
    """Detect diagram code blocks in content."""
    diagram_languages = ["mermaid", "plantuml", "dot", "graphviz", "uml"]
    diagrams = []

    # Find all code blocks
    pattern = r"```(\w*)\n(.*?)\n```"
    matches = re.findall(pattern, content, re.DOTALL)

    for lang, code in matches:
        if lang.lower() in diagram_languages:
            diagrams.append((lang, code))
        elif not lang and DIAGRAM_RENDERER_AVAILABLE:
            # Try to detect diagram type for unlabeled code blocks
            renderer = DiagramRenderer()
            if renderer.detect_diagram_type(code):
                diagrams.append(("auto", code))

    return diagrams


def render_diagram(diagram_code: str, diagram_type: str = "auto") -> bool:
    """Render a diagram using diagram-renderer."""
    if not DIAGRAM_RENDERER_AVAILABLE:
        return False

    try:
        renderer = DiagramRenderer()

        # Render the diagram
        if diagram_type != "auto":
            # Wrap with proper markdown fence if type is known
            formatted_code = f"```{diagram_type}\n{diagram_code}\n```"
        else:
            formatted_code = diagram_code

        html_content = renderer.render_diagram_auto(formatted_code)

        if html_content:
            # Use Streamlit components to render the HTML
            components.html(html_content, height=600, scrolling=True)
            return True
    except Exception as e:
        st.error(f"Failed to render diagram: {str(e)}")

    return False


def render_message_with_code(content: str):
    """Render a message that contains code blocks and diagrams."""
    # Handle empty content
    if not content:
        return

    # First check if we have diagram renderer available and content has code blocks
    if DIAGRAM_RENDERER_AVAILABLE and "```" in content:
        # Detect diagrams
        diagrams = detect_diagram_code(content)

        # If we have diagrams, render them separately
        if diagrams:
            # Split content by code blocks to render text and diagrams separately
            parts = re.split(r"(```\w*\n.*?\n```)", content, flags=re.DOTALL)

            for part in parts:
                if part.startswith("```"):
                    # Check if this is a diagram
                    is_diagram = False
                    for diagram_type, diagram_code in diagrams:
                        if diagram_code in part:
                            # Render the diagram
                            with st.expander("📊 View Diagram", expanded=True):
                                if not render_diagram(diagram_code, diagram_type):
                                    # Fallback to code block
                                    st.code(diagram_code, language=diagram_type)
                            is_diagram = True
                            break

                    if not is_diagram:
                        # Regular code block
                        lines = part[3:].split("\n", 1)
                        language = lines[0].strip() if lines[0].strip() else "python"
                        code = (
                            lines[1][:-3]
                            if len(lines) > 1 and lines[1].endswith("```")
                            else lines[1]
                            if len(lines) > 1
                            else part[3:-3]
                        )
                        st.code(code, language=language)
                else:
                    # Regular markdown text
                    if part.strip():
                        st.markdown(part)
            return

    # Handle content without code blocks or when diagram renderer is not available
    if "```" in content:
        # Original implementation for code blocks without diagram support
        parts = content.split("```")

        for i, part in enumerate(parts):
            if i % 2 == 0:
                if part.strip():
                    st.markdown(part)
            else:
                lines = part.split("\n", 1)
                language = lines[0].strip() if lines[0].strip() else "python"
                code = lines[1] if len(lines) > 1 else part

                st.code(code, language=language)
    else:
        # Just markdown content
        st.markdown(content)


def get_ai_response_fallback(
    provider: str, model: str, messages: list[dict[str, str]]
) -> str | None:
    """Fallback direct provider response (renamed from get_ai_response)."""
    loop = None
    try:
        config = get_state_value("config")
        if not config:
            return None

        # Use ProviderFactory to create provider instance
        factory = ProviderFactory(config)
        provider_instance = factory.create(provider)

        # Convert messages to Message objects
        from coda.base.providers.base import Message, Role

        provider_messages = []
        for msg in messages:
            role = Role.USER if msg["role"] == "user" else Role.ASSISTANT
            provider_messages.append(Message(role=role, content=msg["content"]))

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        response = loop.run_until_complete(
            provider_instance.achat(
                messages=provider_messages,
                model=model,
                temperature=0.7,
                max_tokens=2000,
            )
        )

        return response.content

    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None
    finally:
        if loop:
            loop.close()


def save_to_session(provider: str, model: str, messages: list[dict[str, str]]):
    """Save the conversation to the session database."""
    session_manager = get_state_value("session_manager")
    if not session_manager:
        return

    session_id = get_state_value("current_session_id")

    try:
        if not session_id:
            session = session_manager.create_session(
                name=f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                provider=provider,
                model=model,
            )
            session_id = session.id
            set_state_value("current_session_id", session_id)

        if len(messages) >= 2:
            last_user_msg = messages[-2]
            last_assistant_msg = messages[-1]

            session_manager.add_message(
                session_id=session_id,
                role=last_user_msg["role"],
                content=last_user_msg["content"],
            )

            session_manager.add_message(
                session_id=session_id,
                role=last_assistant_msg["role"],
                content=last_assistant_msg["content"],
            )

    except Exception as e:
        st.error(f"Error saving to session: {e}")
