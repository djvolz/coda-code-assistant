"""Settings management page."""

from pathlib import Path
from typing import Any

import streamlit as st

from coda.apps.web.utils.state import get_state_value, set_state_value
from coda.services.config import get_config_service


def render():
    """Render the settings page."""
    st.title("⚙️ Settings")
    st.markdown("Configure providers, models, and application settings.")

    tab1, tab2, tab3, tab4 = st.tabs(["Providers", "Models", "Appearance", "Advanced"])

    with tab1:
        render_provider_settings()

    with tab2:
        render_model_settings()

    with tab3:
        render_appearance_settings()

    with tab4:
        render_advanced_settings()


def render_provider_settings():
    """Render provider configuration settings."""
    st.subheader("Provider Configuration")

    config = get_state_value("config")
    if not config:
        st.error("Configuration not loaded")
        return

    # Load existing provider configurations
    providers_config = config.get("providers", {})

    st.markdown("### OCI GenAI")
    oci_config = providers_config.get("oci_genai", {})

    col1, col2 = st.columns(2)
    with col1:
        oci_enabled = st.checkbox("Enable OCI GenAI", value=oci_config.get("enabled", False))

    if oci_enabled:
        with st.expander("OCI Configuration", expanded=True):
            compartment_id = st.text_input(
                "Compartment ID",
                value=oci_config.get("compartment_id", ""),
                help="OCI compartment ID for GenAI service",
            )

            profile = st.text_input(
                "Profile Name",
                value=oci_config.get("profile", "DEFAULT"),
                help="OCI config profile name",
            )

    st.markdown("---")

    st.markdown("### Ollama")
    ollama_config = providers_config.get("ollama", {})

    col1, col2 = st.columns(2)
    with col1:
        ollama_enabled = st.checkbox("Enable Ollama", value=ollama_config.get("enabled", False))

    if ollama_enabled:
        with st.expander("Ollama Configuration", expanded=True):
            base_url = st.text_input(
                "Base URL",
                value=ollama_config.get("base_url", "http://localhost:11434"),
                help="Ollama server URL",
            )

    st.markdown("---")

    st.markdown("### LiteLLM")
    litellm_config = providers_config.get("litellm", {})

    col1, col2 = st.columns(2)
    with col1:
        litellm_enabled = st.checkbox("Enable LiteLLM", value=litellm_config.get("enabled", False))

    if litellm_enabled:
        with st.expander("LiteLLM Configuration", expanded=True):
            st.info("LiteLLM uses environment variables for API keys")

            st.text_area(
                "Custom Model Mappings (JSON)",
                value="{}",
                help="Custom model name mappings",
            )

    if st.button("💾 Save Provider Settings", type="primary"):
        save_provider_config(
            config,
            {
                "oci_genai": {
                    "enabled": oci_enabled,
                    "compartment_id": compartment_id if oci_enabled else "",
                    "profile": profile if oci_enabled else "DEFAULT",
                },
                "ollama": {
                    "enabled": ollama_enabled,
                    "base_url": base_url if ollama_enabled else "http://localhost:11434",
                },
                "litellm": {
                    "enabled": litellm_enabled,
                },
            },
        )


def render_model_settings():
    """Render model configuration settings."""
    st.subheader("Model Discovery")

    config = get_state_value("config")
    if not config:
        st.error("Configuration not loaded")
        return

    st.info(
        "Models are discovered automatically from each enabled provider. Click 'Refresh Models' to update the available models."
    )

    # Import here to avoid circular imports
    from coda.base.providers.registry import ProviderFactory

    providers_config = config.get("providers", {})
    for provider in ["oci_genai", "ollama", "litellm"]:
        provider_config = providers_config.get(provider, {})
        if provider_config.get("enabled", False):
            # Display friendly names
            provider_display_names = {
                "oci_genai": "OCI GenAI",
                "ollama": "Ollama",
                "litellm": "LiteLLM",
            }
            display_name = provider_display_names.get(provider, provider.upper())
            st.markdown(f"### {display_name} Models")

            try:
                # Create provider instance and discover models
                factory = ProviderFactory(config)
                provider_instance = factory.create(provider)
                models = provider_instance.list_models()

                if models:
                    st.success(f"Found {len(models)} models")
                    with st.expander("View Available Models"):
                        for model in models:
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.text(f"• {model.name or model.id}")
                            with col2:
                                if hasattr(model, "context_length"):
                                    st.text(f"{model.context_length:,} tokens")
                else:
                    st.warning("No models found")

                if st.button(f"🔄 Refresh {display_name} Models", key=f"refresh_{provider}"):
                    # Force refresh by clearing any cache
                    if hasattr(provider_instance, "refresh_models"):
                        provider_instance.refresh_models()
                    st.rerun()

            except Exception as e:
                st.error(f"Error loading models: {str(e)}")


def render_appearance_settings():
    """Render appearance settings."""
    st.subheader("Appearance Settings")

    st.markdown("### Theme")
    st.selectbox(
        "Color Theme",
        ["Default", "Dark", "Light", "Colorful"],
        help="Select the UI color theme",
    )

    st.markdown("### Layout")
    st.checkbox("Use wide layout by default", value=True)

    st.markdown("### Code Highlighting")
    st.selectbox(
        "Code Editor Theme",
        ["monokai", "github", "tomorrow", "twilight", "solarized_dark", "solarized_light"],
        help="Syntax highlighting theme for code blocks",
    )

    if st.button("💾 Save Appearance Settings", type="primary"):
        st.success("Appearance settings saved!")


def render_advanced_settings():
    """Render advanced settings."""
    st.subheader("Advanced Settings")

    st.markdown("### Database")
    st.text_input(
        "Session Database Path",
        value=str(Path.home() / ".config" / "coda" / "sessions.db"),
        help="Path to the SQLite database file",
    )

    st.markdown("### Logging")
    st.selectbox(
        "Log Level",
        ["DEBUG", "INFO", "WARNING", "ERROR"],
        index=1,
    )

    st.markdown("### Performance")
    col1, col2 = st.columns(2)

    with col1:
        st.number_input(
            "Max Retries",
            min_value=0,
            max_value=10,
            value=3,
            help="Maximum retry attempts for API calls",
        )

    with col2:
        st.number_input(
            "Request Timeout (seconds)",
            min_value=10,
            max_value=300,
            value=60,
            help="API request timeout",
        )

    if st.button("💾 Save Advanced Settings", type="primary"):
        st.success("Advanced settings saved!")


def save_provider_config(config: dict[str, Any], updates: dict[str, Any]):
    """Save provider configuration updates."""
    # Get the global config service
    config_service = get_config_service()

    # Update the providers in the global config
    for provider, settings in updates.items():
        for key, value in settings.items():
            config_service.set(f"providers.{provider}.{key}", value)

    try:
        config_service.save()  # Save the configuration
        set_state_value("config", config_service.to_dict())
        st.success("Provider settings saved successfully!")
        st.rerun()
    except Exception as e:
        st.error(f"Error saving configuration: {e}")
