"""
ui/layout.py — Page config, sidebar, and shared UI structure.
"""

import streamlit as st
from utils.config import AppConfig, azure
from prebuilt.registry import get_display_names, get_description


def configure_page():
    """Set Streamlit page-level configuration."""
    st.set_page_config(
        page_title="Document Intelligence App",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def apply_custom_css():
    """Inject minimal custom CSS."""
    st.markdown(
        """
        <style>
        .main { padding: 2rem; }
        h1, h2 { color: #1f77b4; }
        code { background-color: #f5f5f5; padding: 0.2rem 0.4rem; border-radius: 0.3rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header():
    """App title and description."""
    st.title("📄 Document Intelligence App")
    st.markdown("Extract and analyze document data using Azure Cognitive Services.")
    st.divider()


def setup_sidebar() -> tuple[str, str]:
    """
    Render the sidebar and return the user's selections.

    Returns:
        (selected_page, selected_model_display_name)
    """
    with st.sidebar:
        st.title("⚙️ Settings")

        # Page navigation
        st.subheader("Navigation")
        page = st.radio(
            "Go to:",
            options=["📤 Upload & Analyze", "📊 View Results", "📋 Model Info"],
            label_visibility="collapsed",
        )

        # Model picker — names come from registry (single source of truth)
        st.subheader("Model")
        model_names = get_display_names()
        selected_model = st.selectbox(
            "Select model:",
            options=model_names,
            index=model_names.index("General Document"),
            help="Choose the Azure Document Intelligence model.",
        )

        # Show description as tooltip-style caption
        desc = get_description(selected_model)
        if desc:
            st.caption(desc)

        # Supported formats
        st.subheader("Supported Formats")
        st.info(
            f"**Types:** {', '.join(AppConfig.SUPPORTED_EXTENSIONS)}\n\n"
            f"**Max size:** {AppConfig.MAX_FILE_SIZE_MB} MB"
        )

        # Azure connection status
        st.subheader("Azure Status")
        if azure.is_configured():
            st.success("✅ Connected")
        else:
            st.error("❌ Not configured")
            st.warning(
                "Set `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` and "
                "`AZURE_DOCUMENT_INTELLIGENCE_KEY` in your `.env` file."
            )

        st.divider()
        st.caption("**Document Intelligence App** v2.0  \nPowered by Azure Cognitive Services")

    return page, selected_model

