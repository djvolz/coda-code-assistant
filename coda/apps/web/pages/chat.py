"""Chat interface page."""

import streamlit as st

from coda.apps.web.components.chat_widget import render_chat_interface
from coda.apps.web.components.file_manager import (
    render_file_download_section,
    render_file_upload_widget,
)
from coda.apps.web.components.model_selector import render_model_selector
from coda.apps.web.utils.state import clear_chat_state, get_state_value, set_state_value
from coda.base.providers.registry import get_provider_registry


def render_provider_selector() -> str | None:
    """Render provider selection dropdown."""
    config = get_state_value("config")
    if not config:
        st.error("Configuration not loaded")
        return None

    # Get enabled providers from registry and config
    registry = get_provider_registry()
    available_providers = []
    providers_config = config.get("providers", {})

    for provider_name in registry:
        provider_config = providers_config.get(provider_name, {})
        if provider_config.get("enabled", False):
            available_providers.append(provider_name)

    if not available_providers:
        st.warning("No providers enabled. Please configure providers in Settings.")
        return None

    current_provider = get_state_value("current_provider")
    if current_provider not in available_providers:
        current_provider = available_providers[0]

    # Display friendly names
    provider_display_names = {
        "oci_genai": "OCI GenAI",
        "ollama": "Ollama",
        "litellm": "LiteLLM",
        "mock": "Mock (Testing)",
    }

    provider = st.selectbox(
        "Provider",
        options=available_providers,
        index=(
            available_providers.index(current_provider)
            if current_provider in available_providers
            else 0
        ),
        format_func=lambda x: provider_display_names.get(x, x.upper()),
    )

    set_state_value("current_provider", provider)
    return provider


def render():
    """Render the chat page."""
    st.title("💬 Chat Interface")

    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        provider = render_provider_selector()

    with col2:
        model = render_model_selector(provider)

    with col3:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            clear_chat_state()
            st.rerun()

    st.markdown("---")

    if provider and model:
        col1, col2 = st.columns([3, 1])

        with col1:
            render_chat_interface(provider, model)

        with col2:
            with st.expander("📎 Files", expanded=False):
                uploaded_files = render_file_upload_widget()
                if uploaded_files:
                    st.session_state.uploaded_files = uploaded_files

            with st.expander("💾 Download", expanded=False):
                render_file_download_section()
    else:
        st.info("👆 Select a provider and model to start chatting")
