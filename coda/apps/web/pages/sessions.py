"""Sessions management page."""

from datetime import datetime

import streamlit as st

from coda.apps.web.utils.state import get_state_value
from coda.base.session.models import Session


def render():
    """Render the sessions page."""
    st.title("📁 Session Management")
    st.markdown("View and manage your chat sessions.")

    session_manager = get_state_value("session_manager")
    if not session_manager:
        st.error("Session manager not available")
        return

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        search_query = st.text_input("🔍 Search sessions", placeholder="Enter keywords...")

    with col2:
        filter_provider = st.selectbox("Provider", ["All", "OCI", "Ollama", "LiteLLM"])

    with col3:
        sort_by = st.selectbox("Sort by", ["Date (Newest)", "Date (Oldest)", "Name"])

    st.markdown("---")

    try:
        sessions = session_manager.get_active_sessions()

        if search_query:
            sessions = [s for s in sessions if search_query.lower() in s.name.lower()]

        if filter_provider != "All":
            sessions = [s for s in sessions if s.provider == filter_provider.lower()]

        if sort_by == "Date (Newest)":
            sessions.sort(key=lambda x: x.created_at, reverse=True)
        elif sort_by == "Date (Oldest)":
            sessions.sort(key=lambda x: x.created_at)
        else:
            sessions.sort(key=lambda x: x.name)

        if sessions:
            render_sessions_list(sessions, session_manager)
        else:
            st.info("No sessions found")

    except Exception as e:
        st.error(f"Error loading sessions: {e}")


def render_sessions_list(sessions: list[Session], session_manager):
    """Render the list of sessions."""
    for session in sessions:
        with st.expander(f"**{session.name}** - {session.created_at.strftime('%Y-%m-%d %H:%M')}"):
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                st.write(f"**ID:** {session.id}")
                st.write(f"**Provider:** {session.provider}")
                st.write(f"**Model:** {session.model}")

            with col2:
                messages = session_manager.get_messages(session.id)
                st.metric("Messages", len(messages))

            with col3:
                if session.updated_at:
                    st.write("**Last Updated:**")
                    st.write(session.updated_at.strftime("%Y-%m-%d %H:%M"))

            st.markdown("---")

            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("📋 Load Session", key=f"load_{session.id}", use_container_width=True):
                    load_session(session.id)
                    st.success("Session loaded!")
                    st.switch_page("pages/chat.py")

            with col2:
                if st.button("📄 Export", key=f"export_{session.id}", use_container_width=True):
                    export_session(session, session_manager)

            with col3:
                if st.button("🗑️ Delete", key=f"delete_{session.id}", use_container_width=True):
                    if delete_session(session.id, session_manager):
                        st.rerun()


def load_session(session_id: str):
    """Load a session into the chat interface."""
    st.session_state.current_session_id = session_id
    session_manager = get_state_value("session_manager")
    if session_manager:
        messages = session_manager.get_messages(session_id)
        st.session_state.messages = [{"role": msg.role, "content": msg.content} for msg in messages]


def export_session(session: Session, session_manager):
    """Export a session to a downloadable format."""
    messages = session_manager.get_messages(session.id)

    export_data = {
        "session": {
            "id": session.id,
            "name": session.name,
            "provider": session.provider,
            "model": session.model,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        },
        "messages": [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
            }
            for msg in messages
        ],
    }

    import json

    json_str = json.dumps(export_data, indent=2)

    st.download_button(
        label="Download JSON",
        data=json_str,
        file_name=f"session_{session.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
    )


def delete_session(session_id: str, session_manager) -> bool:
    """Delete a session."""
    try:
        session_manager.delete_session(session_id)
        st.success("Session deleted successfully")
        return True
    except Exception as e:
        st.error(f"Error deleting session: {e}")
        return False
