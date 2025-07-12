#!/usr/bin/env python3
"""Demo app showcasing various Streamlit components.

This script demonstrates different Streamlit components including:
- Navigation with radio buttons
- Charts (Plotly)
- Forms and inputs
- Data display (dataframes)
- Various UI elements
"""

import streamlit as st


def main():
    st.set_page_config(page_title="Debug App", layout="wide")

    st.title("🔍 Debug Navigation App")

    # Simple sidebar
    with st.sidebar:
        st.title("Navigation")

        page = st.radio("Select Page", ["Dashboard", "Chat", "Sessions", "Settings"], index=0)

        st.write(f"Selected: '{page}'")

    # Main content area
    st.write(f"## Current Page: {page}")

    if page == "Dashboard":
        st.write("✅ Dashboard content loads")
        st.write("This is the dashboard page")

        # Test a simple chart
        import pandas as pd
        import plotly.express as px

        df = pd.DataFrame({"x": [1, 2, 3, 4], "y": [10, 11, 12, 13]})
        fig = px.line(df, x="x", y="y", title="Test Chart")
        st.plotly_chart(fig)

    elif page == "Chat":
        st.write("✅ Chat content loads")
        st.write("This is the chat page")

        # Test basic form elements
        st.selectbox("Provider", ["Option 1", "Option 2"])
        st.text_input("Type a message")

    elif page == "Sessions":
        st.write("✅ Sessions content loads")
        st.write("This is the sessions page")

        # Test data display
        import pandas as pd

        df = pd.DataFrame(
            {"Session": ["Session 1", "Session 2"], "Date": ["2023-01-01", "2023-01-02"]}
        )
        st.dataframe(df)

    elif page == "Settings":
        st.write("✅ Settings content loads")
        st.write("This is the settings page")

        # Test form elements
        st.checkbox("Enable feature")
        st.text_input("Configuration value")

    else:
        st.error(f"Unknown page: {page}")


if __name__ == "__main__":
    main()
