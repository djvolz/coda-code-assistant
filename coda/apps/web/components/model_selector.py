"""Model selection component."""

import streamlit as st

from coda.apps.web.utils.state import get_state_value, set_state_value
from coda.base.providers.registry import ProviderFactory


def render_model_selector(provider: str | None) -> str | None:
    """Render model selection dropdown based on selected provider."""
    if not provider:
        st.selectbox("Model", [], disabled=True)
        return None

    config = get_state_value("config")
    if not config:
        return None

    # Display friendly names
    provider_display_names = {
        "oci_genai": "OCI GenAI",
        "ollama": "Ollama",
        "litellm": "LiteLLM",
        "mock": "Mock (Testing)",
    }
    display_name = provider_display_names.get(provider, provider.upper())

    try:
        # Use ProviderFactory to create provider instance and discover models
        factory = ProviderFactory(config)
        provider_instance = factory.create(provider)

        # Get available models from the provider
        model_objects = provider_instance.list_models()

        if not model_objects:
            st.warning(f"No models available for {display_name}")
            return None

        # Extract model IDs for the dropdown
        model_ids = [model.id for model in model_objects]

        # Store model objects in session state for later use
        set_state_value(f"{provider}_models", {model.id: model for model in model_objects})

        current_model = get_state_value("current_model")
        if current_model not in model_ids:
            current_model = model_ids[0]

        # Create a format function to show more info about models
        def format_model(model_id: str) -> str:
            models_dict = get_state_value(f"{provider}_models", {})
            model_obj = models_dict.get(model_id)
            if model_obj and hasattr(model_obj, "name") and model_obj.name:
                return f"{model_obj.name} ({model_id})"
            return model_id

        model = st.selectbox(
            "Model",
            options=model_ids,
            index=model_ids.index(current_model) if current_model in model_ids else 0,
            format_func=format_model,
        )

        set_state_value("current_model", model)
        return model

    except Exception as e:
        st.error(f"Error loading models for {display_name}: {str(e)}")
        return None
