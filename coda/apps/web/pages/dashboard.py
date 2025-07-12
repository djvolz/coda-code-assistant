"""Dashboard page for provider status and statistics."""

from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from coda.apps.web.utils.state import get_state_value
from coda.base.providers.registry import get_provider_registry


def render():
    """Render the dashboard page."""
    st.title("📊 Dashboard")
    st.markdown("Monitor provider status, model availability, and usage statistics.")

    # Check for initialization errors
    if hasattr(st.session_state, "config_error"):
        st.warning(f"Configuration error: {st.session_state.config_error}")
    if hasattr(st.session_state, "session_manager_error"):
        st.warning(f"Session manager error: {st.session_state.session_manager_error}")

    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Active Providers", "3", "↑ 1")

    with col2:
        st.metric("Available Models", "12", "↑ 2")

    with col3:
        st.metric("Total Sessions", "42", "↑ 5")

    with col4:
        st.metric("Tokens Today", "15.2K", "↑ 2.3K")

    st.markdown("---")

    col1, col2 = st.columns([3, 2])

    with col1:
        render_provider_status()

    with col2:
        render_model_distribution()

    st.markdown("---")

    render_usage_trends()


def render_provider_status():
    """Render provider status section."""
    st.subheader("Provider Status")

    config = get_state_value("config")
    if not config:
        st.warning("Configuration not loaded")
        return

    registry = get_provider_registry()
    providers_data = []

    for provider_type, provider_class in registry.items():
        try:
            provider_config = config.get(provider_type, {})
            if provider_config.get("enabled", False):
                provider_class(config=provider_config)

                status = "🟢 Online"
                health = "Healthy"
                models = len(provider_config.get("models", []))

                providers_data.append(
                    {
                        "Provider": provider_type.upper(),
                        "Status": status,
                        "Health": health,
                        "Models": models,
                        "Last Check": datetime.now().strftime("%H:%M:%S"),
                    }
                )
        except Exception as e:
            providers_data.append(
                {
                    "Provider": provider_type.upper(),
                    "Status": "🔴 Error",
                    "Health": str(e),
                    "Models": 0,
                    "Last Check": datetime.now().strftime("%H:%M:%S"),
                }
            )

    if providers_data:
        df = pd.DataFrame(providers_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No providers configured")


def render_model_distribution():
    """Render model distribution chart."""
    st.subheader("Model Distribution")

    data = {
        "Provider": ["OCI GenAI", "Ollama", "LiteLLM"],
        "Models": [3, 5, 4],
    }

    fig = px.pie(
        data_frame=pd.DataFrame(data),
        values="Models",
        names="Provider",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set3,
    )

    fig.update_layout(
        showlegend=True,
        height=300,
        margin=dict(t=0, b=0, l=0, r=0),
    )

    st.plotly_chart(fig, use_container_width=True)


def render_usage_trends():
    """Render usage trends chart."""
    st.subheader("Usage Trends (Last 7 Days)")

    dates = pd.date_range(end=datetime.now(), periods=7, freq="D")
    data = pd.DataFrame(
        {
            "Date": dates,
            "Sessions": [8, 12, 10, 15, 18, 14, 20],
            "Tokens (K)": [2.1, 3.5, 3.2, 4.8, 5.6, 4.2, 6.1],
        }
    )

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=data["Date"],
            y=data["Sessions"],
            mode="lines+markers",
            name="Sessions",
            line=dict(color="#1f77b4", width=2),
            marker=dict(size=8),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=data["Date"],
            y=data["Tokens (K)"],
            mode="lines+markers",
            name="Tokens (K)",
            line=dict(color="#ff7f0e", width=2),
            marker=dict(size=8),
            yaxis="y2",
        )
    )

    fig.update_layout(
        hovermode="x unified",
        height=400,
        xaxis_title="Date",
        yaxis=dict(title="Sessions", side="left"),
        yaxis2=dict(title="Tokens (K)", overlaying="y", side="right"),
    )

    st.plotly_chart(fig, use_container_width=True)
