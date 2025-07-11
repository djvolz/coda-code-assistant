"""Chat interface widget component."""

import asyncio
from datetime import datetime

import streamlit as st

from coda.apps.web.utils.state import get_state_value, set_state_value
from coda.base.providers.registry import ProviderFactory


def render_chat_interface(provider: str, model: str):
    """Render the main chat interface."""
    messages = st.session_state.get("messages", [])

    chat_container = st.container()

    with chat_container:
        for message in messages:
            with st.chat_message(message["role"]):
                if "```" in message["content"]:
                    render_message_with_code(message["content"])
                else:
                    st.markdown(message["content"])

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
            with st.spinner("Thinking..."):
                response = get_ai_response(provider, model, messages)
                if response:
                    if "```" in response:
                        render_message_with_code(response)
                    else:
                        st.markdown(response)

                    messages.append({"role": "assistant", "content": response})
                    st.session_state.messages = messages

                    save_to_session(provider, model, messages)
                else:
                    st.error("Failed to get response from AI")


def render_message_with_code(content: str):
    """Render a message that contains code blocks."""
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


def get_ai_response(provider: str, model: str, messages: list[dict[str, str]]) -> str | None:
    """Get response from the AI provider."""
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
