"""
ui/theme.py — Unified theme combining layout.py + display.py.

Replaces layout.py's apply_custom_styling() with unified CSS that covers
both the prebuilt and custom-model pages under the same design system.

Functions from layout.py:
    configure_page, apply_custom_styling, apply_theme (alias),
    setup_sidebar, check_azure_connection, render_header,
    render_summary_metrics, render_metadata

Functions from display.py:
    render_results_tabs, render_json_view, render_tables_view,
    render_key_value_pairs_view, render_extracted_fields_view,
    render_raw_text_view, render_pages_summary,
    render_error_message, render_success_message, render_processing_spinner
"""

import json

import pandas as pd
import streamlit as st

from utils.config import app_config, azure

# ── Design tokens ─────────────────────────────────────────────────────────────
PRIMARY    = "#1B4F8A"
ACCENT     = "#2D9CDB"
SUCCESS    = "#27AE60"
WARNING    = "#F2994A"
DANGER     = "#EB5757"
SURFACE    = "#F7F9FC"
BORDER     = "#E1E8F0"
TEXT_MUTED = "#6B7C93"


# ══════════════════════════════════════════════════════════════════════════════
# ── From layout.py ────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def configure_page():
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title="Document Intelligence App",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def apply_custom_styling():
    """
    Apply custom CSS for better UI/UX.
    Extended from the original layout.py to also cover custom-model
    annotation pills, extracted-text boxes, and step-header typography.
    """
    st.markdown(
        f"""
        <style>
        /* ── Main container ── */
        .main {{
            padding: 2rem;
        }}
        .main .block-container {{ max-width: 1200px; }}

        /* ── Headings ── */
        h1, h2 {{
            color: {PRIMARY};
        }}
        .step-header {{
            font-size: 1.4rem; font-weight: 700;
            margin-bottom: 0.5rem; color: {PRIMARY};
        }}

        /* ── Buttons ── */
        .stButton > button {{
            border-radius: 7px; font-weight: 600;
            border: 1.5px solid {BORDER};
            transition: all 0.15s ease;
        }}
        .stButton > button[kind="primary"] {{
            background: {PRIMARY}; color: white; border-color: {PRIMARY};
        }}
        .stButton > button[kind="primary"]:hover {{
            background: {ACCENT}; border-color: {ACCENT};
        }}

        /* ── Success/Error boxes ── */
        .success-box {{
            padding: 1rem;
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 0.5rem;
            color: #155724;
        }}
        .error-box {{
            padding: 1rem;
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            border-radius: 0.5rem;
            color: #721c24;
        }}

        /* ── Tabs ── */
        .streamlit-tabs {{ gap: 2rem; }}
        .stTabs [data-baseweb="tab-list"] {{
            gap: 6px; border-bottom: 2px solid {BORDER};
        }}
        .stTabs [data-baseweb="tab"] {{
            border-radius: 6px 6px 0 0;
            font-weight: 600; color: {TEXT_MUTED};
        }}
        .stTabs [aria-selected="true"] {{
            color: {PRIMARY}; border-bottom: 2px solid {PRIMARY};
        }}

        /* ── Code blocks ── */
        code {{
            background-color: #f5f5f5;
            padding: 0.2rem 0.4rem;
            border-radius: 0.3rem;
        }}

        /* ── Metrics ── */
        [data-testid="metric-container"] {{
            background: {SURFACE}; border: 1px solid {BORDER};
            border-radius: 8px; padding: 12px 16px;
        }}

        /* ── Sidebar ── */
        section[data-testid="stSidebar"],
        section[data-testid="stSidebar"] > div,
        div[data-testid="stSidebarContent"] {{
            background-color: var(--secondary-background-color) !important;
            color: var(--text-color) !important;}}
        section[data-testid="stSidebar"] {{
            border-right: 1px solid rgba(var(--text-color-rgb, 0,0,0), 0.08);}}

        /* Inputs and labels inside sidebar inherit the active theme */
        section[data-testid="stSidebar"] input,
        section[data-testid="stSidebar"] textarea,
        section[data-testid="stSidebar"] select,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] .stTextInput > div,
        section[data-testid="stSidebar"] .stSelectbox > div {{
           background-color: var(--background-color) !important;
           color: var(--text-color) !important;
           border-color: rgba(var(--text-color-rgb, 0,0,0), 0.15) !important;}}
        
        /* ── File uploader ── */
        [data-testid="stFileUploader"] {{
            border: 2px dashed {ACCENT};
            border-radius: 8px; background: #F0F7FF;
        }}

        /* ── Custom-model annotation pills ── */
        .annotation-pill {{
            display: inline-block; padding: 3px 10px; border-radius: 20px;
            font-size: 12px; font-weight: 700; color: white; margin: 2px;
        }}

        /* ── Custom-model text boxes ── */
        .extracted-text-box {{
            background: #f0fff4; border: 1px solid #38a169; border-radius: 6px;
            padding: 8px 12px; font-family: monospace; font-size: 13px;
            color: #276749; margin: 4px 0;
        }}
        .no-text-box {{
            background: #fff5f5; border: 1px solid #fc8181; border-radius: 6px;
            padding: 8px 12px; font-size: 13px; color: {DANGER}; margin: 4px 0;
        }}

        /* ── Landing page mode cards ── */
        .mode-card {{
            background: white; border: 2px solid {BORDER};
            border-radius: 14px; padding: 32px 28px; text-align: center;
            transition: all 0.2s ease; height: 100%;
        }}
        .mode-card:hover {{
            border-color: {ACCENT};
            box-shadow: 0 4px 20px rgba(45,156,219,0.15);
            transform: translateY(-2px);
        }}
        .mode-card .icon {{ font-size: 3rem; margin-bottom: 12px; }}
        .mode-card h3 {{ color: {PRIMARY}; margin: 0 0 8px 0; font-size: 1.2rem; }}
        .mode-card p {{ color: {TEXT_MUTED}; font-size: 0.9rem; margin: 0; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ── Public alias so both names work ──────────────────────────────────────────
# Home.py and any page can use either:
#   from ui.theme import apply_theme          ← landing page style
#   from ui.theme import apply_custom_styling ← original layout.py name
apply_theme = apply_custom_styling


def setup_sidebar():
    """Configure sidebar with navigation and settings."""
    with st.sidebar:
        st.title("⚙️ Settings")

        st.subheader("Navigation")
        page = st.radio(
            "Go to:",
            options=["📤 Upload & Analyze", "📊 View Results", "📋 Model Info"],
            label_visibility="collapsed",
        )

        st.subheader("Model Configuration")
        model_options = list(app_config.MODEL_MAP.keys())
        selected_model = st.selectbox(
            "Select Document Model:",
            options=model_options,
            index=2,
            help="Choose the Azure Document Intelligence model to analyze your document.",
        )

        st.subheader("Supported Formats")
        st.info(
            f"**File Types:** {', '.join(app_config.SUPPORTED_EXTENSIONS)}\n\n"
            f"**Max Size:** {app_config.MAX_FILE_SIZE_MB} MB"
        )

        st.subheader("Status")
        if check_azure_connection():
            st.success("✅ Azure Connected")
        else:
            st.error("❌ Azure Not Configured")
            st.warning(
                "Please set `AZURE_DI_ENDPOINT` "
                "and `AZURE_DI_KEY` in your `.env` file."
            )

        st.divider()
        st.caption(
            "**Document Intelligence App** v1.0  \n"
            "Powered by Azure Cognitive Services"
        )

        return page, selected_model


def check_azure_connection() -> bool:
    """Check if Azure credentials are configured."""
    return azure.is_configured()


def render_header():
    """Render app header."""
    col1, col2 = st.columns([0.9, 0.1])
    with col1:
        st.title("📄 Document Intelligence App")
        st.markdown("Extract and analyze document data using Azure Cognitive Services")
    st.divider()


def render_summary_metrics(parsed_output: dict):
    """Display summary metrics in columns."""
    summary = parsed_output.get("summary", {})

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Pages",            summary.get("total_pages",            0))
    with col2:
        st.metric("Tables",           summary.get("total_tables",           0))
    with col3:
        st.metric("Key-Value Pairs",  summary.get("total_key_value_pairs",  0))
    with col4:
        st.metric("Extracted Fields", summary.get("total_extracted_fields", 0))
    with col5:
        st.metric("Words",            summary.get("total_words",            0))


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


# ══════════════════════════════════════════════════════════════════════════════
# ── From display.py ───────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def render_results_tabs(parsed_output: dict):
    """Render multiple tabs for different result views."""
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "📋 JSON View",
            "📊 Tables",
            "🔑 Key-Value Pairs",
            "📄 Extracted Fields",
            "📝 Raw Text",
        ]
    )

    with tab1:
        render_json_view(parsed_output)
    with tab2:
        render_tables_view(parsed_output)
    with tab3:
        render_key_value_pairs_view(parsed_output)
    with tab4:
        render_extracted_fields_view(parsed_output)
    with tab5:
        render_raw_text_view(parsed_output)


def render_json_view(parsed_output: dict):
    """Display full JSON output in an expandable format."""
    st.subheader("Full JSON Output")

    col1, col2 = st.columns([0.7, 0.3])
    with col1:
        st.write("Complete parsed output in JSON format:")
    with col2:
        json_str = json.dumps(parsed_output, indent=2)
        st.download_button(
            label="📥 Download JSON",
            data=json_str,
            file_name=f"{parsed_output['meta']['filename']}_analysis.json",
            mime="application/json",
        )

    st.json(parsed_output)


def render_tables_view(parsed_output: dict):
    """Display extracted tables in a structured format."""
    st.subheader("Extracted Tables")

    tables = parsed_output.get("tables", [])

    if not tables:
        st.info("ℹ️ No tables found in the document.")
        return

    for table_idx, table in enumerate(tables):
        st.write(f"**Table {table.get('table_index', table_idx + 1)}**")
        st.caption(
            f"Rows: {table.get('row_count', '?')} | "
            f"Columns: {table.get('column_count', '?')}"
        )
        try:
            rows = table.get("rows", [])
            if rows:
                df = pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True)
            else:
                st.warning("Table has no rows.")
        except Exception as e:
            st.error(f"Error displaying table: {str(e)}")
        st.divider()


def render_key_value_pairs_view(parsed_output: dict):
    """Display key-value pairs in a structured table."""
    st.subheader("Key-Value Pairs")

    kv_pairs = parsed_output.get("key_value_pairs", [])

    if not kv_pairs:
        st.info("ℹ️ No key-value pairs found in the document.")
        return

    try:
        df = pd.DataFrame(kv_pairs)
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"Error displaying key-value pairs: {str(e)}")

    st.metric("Total Key-Value Pairs", len(kv_pairs))


def render_extracted_fields_view(parsed_output: dict):
    """Display extracted document fields (Invoice, Receipt, etc.)."""
    st.subheader("Extracted Fields")

    fields = parsed_output.get("extracted_fields", {})

    if not fields:
        st.info("ℹ️ No extracted fields found. This model may not support field extraction.")
        return

    field_data = []
    for field_name, field_info in fields.items():
        field_data.append({
            "Field":      field_name,
            "Value":      field_info.get("value", ""),
            "Content":    field_info.get("content", ""),
            "Confidence": f"{field_info.get('confidence', 0):.2%}" if field_info.get("confidence") else "N/A",
        })

    try:
        df = pd.DataFrame(field_data)
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"Error displaying extracted fields: {str(e)}")

    st.metric("Total Extracted Fields", len(fields))


def render_raw_text_view(parsed_output: dict):
    """Display raw concatenated text from pages."""
    st.subheader("Raw Text")

    raw_text = parsed_output.get("raw_text", "")

    if not raw_text:
        st.info("ℹ️ No raw text available.")
        return

    lines = raw_text.split("\n")
    st.caption(f"Total Lines: {len(lines)}")

    st.text_area(
        "Extracted Text:",
        value=raw_text,
        height=400,
        disabled=True,
        label_visibility="collapsed",
    )

    st.download_button(
        label="📥 Download Text",
        data=raw_text,
        file_name=f"{parsed_output['meta']['filename']}_text.txt",
        mime="text/plain",
    )


def render_pages_summary(parsed_output: dict):
    """Display a summary of pages."""
    st.subheader("Pages Summary")

    pages = parsed_output.get("pages", [])

    if not pages:
        st.info("ℹ️ No pages found.")
        return

    for page in pages:
        with st.expander(
            f"Page {page.get('page_number', '?')} - "
            f"{page.get('line_count', 0)} lines, "
            f"{page.get('word_count', 0)} words"
        ):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Dimensions:** {page.get('dimensions', 'N/A')}")
                st.write(f"**Lines:** {page.get('line_count', 0)}")
            with col2:
                st.write(f"**Words:** {page.get('word_count', 0)}")

            lines = page.get("lines", [])[:5]
            if lines:
                st.write("**First lines:**")
                for line in lines:
                    st.caption(line)


def render_error_message(error_msg: str):
    """Display error message in a styled box."""
    st.error(f"❌ **Analysis Failed:** {error_msg}")


def render_success_message(saved_path: str = ""):
    """Display success message."""
    message = "✅ **Document analyzed successfully!**"
    if saved_path:
        message += f"\n\nResults saved to: `{saved_path}`"
    st.success(message)


def render_processing_spinner(message: str = "Processing document..."):
    """Display a processing spinner."""
    with st.spinner(message):
        return st.container()
