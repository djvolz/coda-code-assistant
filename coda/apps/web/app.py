"""Main Streamlit application for Coda Assistant Web UI."""

import streamlit as st

from coda.apps.web.pages import chat, dashboard, sessions, settings
from coda.apps.web.utils.state import init_session_state


def configure_page():
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title="Coda Assistant",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "Get Help": "https://github.com/yourusername/coda-assistant",
            "Report a bug": "https://github.com/yourusername/coda-assistant/issues",
            "About": "# Coda Assistant\n\nA multi-provider AI assistant for code development.",
        },
    )


def setup_sidebar() -> str:
    """Setup the sidebar navigation and return selected page."""
    with st.sidebar:
        st.title("🤖 Coda Assistant")
        st.markdown("---")

        # Use a key to persist the radio selection
        page = st.radio(
            "Navigation",
            ["📊 Dashboard", "💬 Chat", "📁 Sessions", "⚙️ Settings"],
            index=0,
            key="navigation_radio",
        )

        st.markdown("---")

        st.markdown("### Quick Stats")
        if "session_manager" in st.session_state and st.session_state.session_manager is not None:
            try:
                total_sessions = len(st.session_state.session_manager.get_active_sessions())
                st.metric("Total Sessions", total_sessions)
            except Exception:
                st.metric("Total Sessions", "N/A")

        st.markdown("---")

        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    return page


def render_page(page: str):
    """Render the selected page."""
    # Simple page routing without emojis in keys
    try:
        if page == "📊 Dashboard":
            dashboard.render()
        elif page == "💬 Chat":
            chat.render()
        elif page == "📁 Sessions":
            sessions.render()
        elif page == "⚙️ Settings":
            settings.render()
        else:
            st.error(f"Page not found: {page}")

    except Exception as e:
        st.error(f"Error loading {page}: {str(e)}")
        st.exception(e)

        # Show fallback content
        st.markdown("---")
        st.write("**Fallback Content:**")
        st.write(f"This is a placeholder for the {page} page.")
        st.write("The page failed to load properly.")


def main():
    """Main application entry point."""
    configure_page()

    init_session_state()

    selected_page = setup_sidebar()

    # Debug info
    # st.write(f"Selected page: {selected_page}")

    render_page(selected_page)


if __name__ == "__main__":
    main()
