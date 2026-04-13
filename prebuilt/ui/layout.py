"""
layout.py — Page config, sidebar, navigation, and UI styling
"""

import streamlit as st
from utils.config import AppConfig


def configure_page():
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title="Document Intelligence App",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def apply_custom_styling():
    """Apply custom CSS for better UI/UX."""
    st.markdown(
        """
        <style>
        /* Main container padding */
        .main {
            padding: 2rem;
        }
        
        /* Header styling */
        h1, h2 {
            color: #1f77b4;
        }
        
        /* Success/Error boxes */
        .success-box {
            padding: 1rem;
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 0.5rem;
            color: #155724;
        }
        
        .error-box {
            padding: 1rem;
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            border-radius: 0.5rem;
            color: #721c24;
        }
        
        /* Tab styling */
        .streamlit-tabs {
            gap: 2rem;
        }
        
        /* Code block styling */
        code {
            background-color: #f5f5f5;
            padding: 0.2rem 0.4rem;
            border-radius: 0.3rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def setup_sidebar():
    """Configure sidebar with navigation and settings."""
    with st.sidebar:
        st.title("⚙️ Settings")
        
        # Navigation section
        st.subheader("Navigation")
        page = st.radio(
            "Go to:",
            options=["📤 Upload & Analyze", "📊 View Results", "📋 Model Info"],
            label_visibility="collapsed",
        )
        
        # Model selection
        st.subheader("Model Configuration")
        model_options = list(AppConfig.MODEL_MAP.keys())
        selected_model = st.selectbox(
            "Select Document Model:",
            options=model_options,
            index=2,  # Default to "General Document"
            help="Choose the Azure Document Intelligence model to analyze your document.",
        )
        
        # File type info
        st.subheader("Supported Formats")
        st.info(
            f"**File Types:** {', '.join(AppConfig.SUPPORTED_EXTENSIONS)}\n\n"
            f"**Max Size:** {AppConfig.MAX_FILE_SIZE_MB} MB"
        )
        
        # Azure status
        st.subheader("Status")
        if check_azure_connection():
            st.success("✅ Azure Connected")
        else:
            st.error("❌ Azure Not Configured")
            st.warning(
                "Please set `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` "
                "and `AZURE_DOCUMENT_INTELLIGENCE_KEY` in your `.env` file."
            )
        
        # App info
        st.divider()
        st.caption(
            "**Document Intelligence App** v1.0  \n"
            "Powered by Azure Cognitive Services"
        )
        
        return page, selected_model


def check_azure_connection() -> bool:
    """Check if Azure credentials are configured."""
    from utils.config import AzureConfig
    return AzureConfig.is_configured()


def render_header():
    """Render app header."""
    col1, col2 = st.columns([0.9, 0.1])
    with col1:
        st.title("📄 Document Intelligence App")
        st.markdown(
            """
            Extract and analyze document data using Azure Cognitive Services
            """
        )
    st.divider()


def render_summary_metrics(parsed_output: dict):
    """Display summary metrics in columns."""
    summary = parsed_output.get("summary", {})
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Pages", summary.get("total_pages", 0))
    with col2:
        st.metric("Tables", summary.get("total_tables", 0))
    with col3:
        st.metric("Key-Value Pairs", summary.get("total_key_value_pairs", 0))
    with col4:
        st.metric("Extracted Fields", summary.get("total_extracted_fields", 0))
    with col5:
        st.metric("Words", summary.get("total_words", 0))


def render_metadata(parsed_output: dict):
    """Display document metadata."""
    meta = parsed_output.get("meta", {})
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write(f"**Filename:** {meta.get('filename', 'N/A')}")
    with col2:
        st.write(f"**Model:** {meta.get('model', 'N/A')}")
    with col3:
        st.write(f"**Analyzed:** {meta.get('analyzed_at', 'N/A')}")
