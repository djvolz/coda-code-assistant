"""Session state management for Streamlit."""

from pathlib import Path
from typing import Any

import streamlit as st

from coda.base.session.manager import SessionManager
from coda.services.config import get_config_service


def init_session_state():
    """Initialize Streamlit session state with required values."""
    if "initialized" not in st.session_state:
        st.session_state.initialized = True

        try:
            config_service = get_config_service()
            st.session_state.config = config_service.to_dict()
        except Exception as e:
            # Store error for later display, don't show in UI during init
            st.session_state.config = None
            st.session_state.config_error = str(e)

        try:
            db_path = Path.home() / ".config" / "coda" / "sessions.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            st.session_state.session_manager = SessionManager()
        except Exception as e:
            # Store error for later display, don't show in UI during init
            st.session_state.session_manager = None
            st.session_state.session_manager_error = str(e)

        st.session_state.current_session_id = None
        st.session_state.current_provider = None
        st.session_state.current_model = None
        st.session_state.messages = []
        st.session_state.providers = {}
        st.session_state.models = {}


def get_state_value(key: str, default: Any = None) -> Any:
    """Get a value from session state with a default."""
    return st.session_state.get(key, default)


def set_state_value(key: str, value: Any):
    """Set a value in session state."""
    st.session_state[key] = value


def clear_chat_state():
    """Clear chat-related session state."""
    st.session_state["messages"] = []
    st.session_state["current_session_id"] = None
