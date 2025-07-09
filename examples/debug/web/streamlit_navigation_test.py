#!/usr/bin/env python3
"""Test Streamlit radio button navigation functionality.

This script demonstrates and tests basic Streamlit navigation using radio buttons
in the sidebar. It's useful for debugging navigation-related issues.
"""

import streamlit as st


def main():
    st.set_page_config(page_title="Debug App", layout="wide")

    st.write("# Debug Navigation Test")
    st.write("This is a minimal test to verify basic Streamlit navigation works.")

    # Sidebar
    with st.sidebar:
        st.write("## Navigation")

        # Simple radio button
        page = st.radio("Choose page:", ["Page 1", "Page 2", "Page 3"], index=0)

        st.write(f"**Selected:** {page}")

    # Main content
    st.write(f"## Current Page: {page}")

    if page == "Page 1":
        st.write("✅ This is Page 1 content")
        st.write("You should see this text when Page 1 is selected")

    elif page == "Page 2":
        st.write("✅ This is Page 2 content")
        st.write("You should see this text when Page 2 is selected")

    elif page == "Page 3":
        st.write("✅ This is Page 3 content")
        st.write("You should see this text when Page 3 is selected")

    st.write("---")
    st.write("**Debug Info:**")
    st.write(f"- Selected page: '{page}'")
    st.write(f"- Page type: {type(page)}")


if __name__ == "__main__":
    main()
