"""Simplified main Streamlit application for debugging."""

import streamlit as st

# Import pages
try:
    from coda.apps.web.pages import chat, dashboard, sessions, settings
    from coda.apps.web.utils.state import init_session_state

    PAGES_AVAILABLE = True
except Exception as e:
    PAGES_AVAILABLE = False
    import_error = str(e)


def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="Coda Assistant", page_icon="🤖", layout="wide", initial_sidebar_state="expanded"
    )

    # Initialize session state
    if PAGES_AVAILABLE:
        try:
            init_session_state()
        except Exception as e:
            st.error(f"State initialization failed: {e}")

    # Sidebar navigation
    with st.sidebar:
        st.title("🤖 Coda Assistant")
        st.markdown("---")

        if PAGES_AVAILABLE:
            page = st.radio("Navigation", ["Dashboard", "Chat", "Sessions", "Settings"], index=0)
        else:
            st.error("Pages not available")
            st.error(f"Import error: {import_error}")
            return

    # Main content area
    st.title(f"{page} Page")

    if not PAGES_AVAILABLE:
        st.error("Cannot load pages due to import errors")
        return

    # Simple page routing
    try:
        if page == "Dashboard":
            st.write("Loading Dashboard...")
            dashboard.render()
        elif page == "Chat":
            st.write("Loading Chat...")
            chat.render()
        elif page == "Sessions":
            st.write("Loading Sessions...")
            sessions.render()
        elif page == "Settings":
            st.write("Loading Settings...")
            settings.render()
        else:
            st.error(f"Unknown page: {page}")

    except Exception as e:
        st.error(f"Error rendering {page}: {str(e)}")
        st.exception(e)

        # Show fallback content
        st.markdown("---")
        st.write("**Fallback Content:**")
        st.write(f"This is a placeholder for the {page} page.")
        st.write("The page failed to load properly.")


if __name__ == "__main__":
    main()
