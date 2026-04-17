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
