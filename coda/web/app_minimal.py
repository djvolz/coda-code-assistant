"""Minimal Streamlit app to test navigation."""

import streamlit as st

st.set_page_config(page_title="Test Navigation", layout="wide")


def main():
    """Main app."""

    # Sidebar navigation
    with st.sidebar:
        st.title("Navigation Test")
        page = st.radio("Select Page", ["Home", "About", "Contact"])

    # Main content
    st.title(f"Current Page: {page}")

    if page == "Home":
        st.write("This is the Home page")
        st.info("Welcome to the home page!")
    elif page == "About":
        st.write("This is the About page")
        st.success("Learn more about us here!")
    elif page == "Contact":
        st.write("This is the Contact page")
        st.warning("Get in touch with us!")


if __name__ == "__main__":
    main()
