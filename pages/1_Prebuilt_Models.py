"""
pages/1_Prebuilt_Models.py
Prebuilt Azure DI model analysis page.

Combines:
- theme.py function calls (render_header, render_metadata, render_summary_metrics,
  render_json_view, render_tables_view, render_key_value_pairs_view,
  render_extracted_fields_view, render_raw_text_view, render_pages_summary,
  render_error_message, render_success_message)
- Optimised two-column layout: JSON on left, structured data tabs on right
- Model description card, Excel table export, pages summary
"""

import io

import pandas as pd
import streamlit as st

from prebuilt.controllers.inference_controller import run_inference
from prebuilt.ui.theme import (PRIMARY, TEXT_MUTED, BORDER, SURFACE,
    apply_custom_styling,
    render_header,
    render_summary_metrics,
    render_metadata,
    render_json_view,
    render_tables_view,
    render_key_value_pairs_view,
    render_extracted_fields_view,
    render_raw_text_view,
    render_pages_summary,
    render_error_message,
    render_success_message,)

from utils.config import app_config, azure

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Prebuilt Models — Azure DI",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_custom_styling()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Settings")

    # Azure credentials
    st.subheader("Azure Configuration")
    endpoint = st.text_input(
        "DI Endpoint",
        value=azure.endpoint,
        placeholder="https://<resource>.cognitiveservices.azure.com/",
    )
    key = st.text_input("DI Key", value=azure.key, type="password")

    st.divider()

    # Model selection
    st.subheader("Model Configuration")
    model_names    = list(app_config.MODEL_MAP.keys())
    selected_model = st.selectbox(
        "Select Document Model:",
        options=model_names,
        index=2,   # Default: General Document
        help="Choose the Azure Document Intelligence model to analyze your document.",
    )

    # File type info
    st.subheader("Supported Formats")
    st.info(
        f"**File Types:** {', '.join(app_config.SUPPORTED_EXTENSIONS)}\n\n"
        f"**Max Size:** {app_config.MAX_FILE_SIZE_MB} MB"
    )

    # Azure status indicator
    st.subheader("Status")
    if endpoint and key:
        st.success("✅ Azure Connected")
    else:
        st.error("❌ Azure Not Configured")
        st.warning("Enter credentials above or set them in `.env`")

    st.divider()
    st.caption(
        "**Document Intelligence App** v1.0  \n"
        "Powered by Azure Cognitive Services"
    )
    st.divider()
    if st.button("🏠 Back to Home", use_container_width=True):
        st.switch_page("Home_app.py")

# ── Header ────────────────────────────────────────────────────────────────────
render_header()

# ── Model description card ────────────────────────────────────────────────────
MODEL_DESCRIPTIONS = {
    "OCR (Read)":       ("📝", "Basic text extraction from any document or image."),
    "Layout Analysis":  ("📐", "Text, tables, regions, and reading order from complex layouts."),
    "General Document": ("📂", "Key-value pairs, tables, and entities from generic documents."),
    "Invoice":          ("🧾", "Invoice-specific fields: amount, date, vendor, line items."),
    "Receipt":          ("🛒", "Receipt-specific fields: items, total, merchant, date."),
}
icon, desc = MODEL_DESCRIPTIONS.get(selected_model, ("📄", ""))
st.markdown(
    f'<div style="background:{SURFACE};border:1px solid {BORDER};border-radius:8px;'
    f'padding:12px 18px;margin-bottom:1rem;display:flex;align-items:center;gap:12px">'
    f'<span style="font-size:1.8rem">{icon}</span>'
    f'<span style="color:{TEXT_MUTED}">{desc}</span>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── File uploader ─────────────────────────────────────────────────────────────
st.subheader("📤 Upload & Analyze")
uploaded_file = st.file_uploader(
    "Drop a file here or click to browse",
    type=[ext.lstrip(".") for ext in app_config.SUPPORTED_EXTENSIONS],
    help=f"Max {app_config.MAX_FILE_SIZE_MB} MB",
    label_visibility="collapsed",
)

if not uploaded_file:
    st.info("⬆️ Upload a document above to begin analysis.")
    st.stop()

if not (endpoint and key):
    render_error_message("Azure credentials are missing. Enter them in the sidebar.")
    st.stop()

# ── Analyse button ────────────────────────────────────────────────────────────
if st.button("🔍 Analyse Document", type="primary"):
    with st.spinner(f"Analysing with **{selected_model}**…"):
        result = run_inference(
            file_bytes=uploaded_file.read(),
            filename=uploaded_file.name,
            model_display_name=selected_model,
            endpoint_override=endpoint,
            key_override=key,
        )

    if not result["success"]:
        render_error_message(result["error"])
        st.stop()

    st.session_state["prebuilt_result"]   = result["parsed"]
    st.session_state["prebuilt_filename"] = uploaded_file.name
    st.session_state["prebuilt_model"]    = selected_model
    st.session_state["prebuilt_saved"]    = result.get("saved_json_path", "")

# ── Guard: nothing to show yet ────────────────────────────────────────────────
parsed = st.session_state.get("prebuilt_result")
if not parsed:
    st.stop()

# ── Success banner + metadata ─────────────────────────────────────────────────
saved_path = st.session_state.get("prebuilt_saved", "")
render_success_message(saved_path)
render_metadata(parsed)
st.divider()

# ── Summary metrics ───────────────────────────────────────────────────────────
render_summary_metrics(parsed)
st.divider()

# ── Two-column results layout ─────────────────────────────────────────────────
# Left  → full JSON output  (render_json_view from theme.py)
# Right → structured tabs   (tables, KV pairs, fields, raw text)
left_col, right_col = st.columns(2, gap="medium")

with left_col:
    st.markdown(f'<h4 style="color:{PRIMARY}">📋 JSON Output</h4>', unsafe_allow_html=True)
    render_json_view(parsed)

with right_col:
    st.markdown(f'<h4 style="color:{PRIMARY}">📊 Structured Data</h4>', unsafe_allow_html=True)

    tab_tables, tab_kv, tab_fields, tab_text = st.tabs(
        ["📊 Tables", "🔑 Key-Value Pairs", "📄 Extracted Fields", "📝 Raw Text"]
    )

    # ── Tables tab (with Excel export) ───────────────────────────────────────
    with tab_tables:
        tables = parsed.get("tables", [])
        if tables:
            render_tables_view(parsed)

            # Excel export — one sheet per table
            try:
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                    for t_idx, table in enumerate(tables):
                        rows = table.get("rows", [])
                        if rows:
                            pd.DataFrame(rows).to_excel(
                                writer,
                                sheet_name=f"Table_{t_idx + 1}",
                                index=False,
                            )
                st.download_button(
                    "⬇️ Download Tables (Excel)",
                    data=buf.getvalue(),
                    file_name=f"{st.session_state.get('prebuilt_filename', 'doc')}_tables.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            except Exception:
                pass
        else:
            st.info("ℹ️ No tables found in the document.")

    # ── Key-Value Pairs tab ───────────────────────────────────────────────────
    with tab_kv:
        render_key_value_pairs_view(parsed)

    # ── Extracted Fields tab ──────────────────────────────────────────────────
    with tab_fields:
        render_extracted_fields_view(parsed)

    # ── Raw Text tab ──────────────────────────────────────────────────────────
    with tab_text:
        render_raw_text_view(parsed)

# ── Pages summary (full width) ────────────────────────────────────────────────
st.divider()
render_pages_summary(parsed)
