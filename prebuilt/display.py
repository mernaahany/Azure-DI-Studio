"""
ui/display.py — Render analysis results in Streamlit tabs.


"""

import json
import streamlit as st
from prebuilt.table_parser import (
    get_summary_df,
    get_fields_df,
    get_kv_df,
    get_tables_dfs,
    get_pages_df,
)


# ── Main entry point ───────────────────────────────────────────────────────────

def render_results(parsed: dict): # parsed is the output of json_parser.build_json_output, which is a cleaned and structured version of the raw Azure result.
    """Render all result views inside tabs."""

    # Summary metrics bar (always shown above tabs)
    _render_metrics(parsed)
    st.divider()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 JSON",
        "📊 Tables",
        "🔑 Key-Value Pairs", # for general docs.
        "📄 Extracted Fields",
        "📝 Raw Text",
    ])

    with tab1: _render_json(parsed)
    with tab2: _render_tables(parsed)
    with tab3: _render_kv_pairs(parsed)
    with tab4: _render_fields(parsed)
    with tab5: _render_raw_text(parsed)


# ── Tabs ───────────────────────────────────────────────────────────────────────

def _render_json(parsed: dict):
    st.subheader("Full JSON Output")
    col1, col2 = st.columns([0.75, 0.25])
    with col2:
        st.download_button(
            label="📥 Download JSON",
            data=json.dumps(parsed, indent=2),
            file_name=f"{parsed['meta']['filename']}_analysis.json",
            mime="application/json",
        )
    with col1:
        st.json(parsed)


def _render_tables(parsed: dict):
    st.subheader("Extracted Tables")
    dfs = get_tables_dfs(parsed)
    if not dfs:
        st.info("ℹ️ No tables found in this document.")
        return
    for i, df in enumerate(dfs, start=1):
        st.write(f"**Table {i}**")
        st.dataframe(df, use_container_width=True)
        st.divider()


def _render_kv_pairs(parsed: dict):
    st.subheader("Key-Value Pairs")
    df = get_kv_df(parsed)
    if df is None:
        st.info("ℹ️ No key-value pairs found.")
        return
    st.dataframe(df, use_container_width=True) #user container width to allow horizontal scrolling if many columns
    st.metric("Total", len(df)) # show total count of kv pairs in the dataset


def _render_fields(parsed: dict):
    st.subheader("Extracted Fields")
    df = get_fields_df(parsed)
    if df is None:
        st.info("ℹ️ No extracted fields. This model may not support field extraction.")
        return
    st.dataframe(df, use_container_width=True)
    st.metric("Total Fields", len(df))

    # If Invoice or Receipt, also show the dedicated details block 
    
    if "invoice_details" in parsed:
        st.subheader("Invoice Details") # if the model is an invoice model, there will be a special "invoice_details" section in the enhanced parsed output that contains commonly extracted invoice fields in a more structured way than just the generic extracted_fields dict. This is for better display and to highlight important invoice info.
        st.json(parsed["invoice_details"])

    if "receipt_details" in parsed:
        st.subheader("Receipt Details")
        items = parsed["receipt_details"].get("items", [])
        if items:
            st.write("**Line Items**") # line items are content extracted from the receipt and structured into a list of dicts, which we can display as a table. This is more user-friendly than showing them as part of the raw extracted_fields.
            st.dataframe(items, use_container_width=True)
        st.json({k: v for k, v in parsed["receipt_details"].items() if k != "items"})


def _render_raw_text(parsed: dict):
    st.subheader("Raw Text")
    text = parsed.get("raw_text", "")
    if not text:
        st.info("ℹ️ No raw text available.")
        return
    lines = text.split("\n")
    st.caption(f"Total Lines: {len(lines)}")
    st.text_area("", value=text, height=400, disabled=True, label_visibility="collapsed")
    st.download_button(
        label="📥 Download Text",
        data=text,
        file_name=f"{parsed['meta']['filename']}_text.txt",
        mime="text/plain",
    )


# ── Metrics bar ────────────────────────────────────────────────────────────────

def _render_metrics(parsed: dict):
    s = parsed.get("summary", {})
    cols = st.columns(5)
    metrics = [
        ("Pages",        s.get("total_pages", 0)),
        ("Tables",       s.get("total_tables", 0)),
        ("KV Pairs",     s.get("total_kv_pairs", 0)),
        ("Fields",       s.get("total_fields", 0)),
        ("Words",        s.get("total_words", 0)),
    ]
    for col, (label, value) in zip(cols, metrics):
        col.metric(label, value)


# ── Status messages ────────────────────────────────────────────────────────────

def render_error(msg: str):
    st.error(f"❌ **Analysis Failed:** {msg}")


def render_success(saved_path: str = "", time_ms: float = 0):
    extra = ""
    if saved_path:
        extra += f"\n\nSaved to: `{saved_path}`"
    if time_ms:
        extra += f"  |  Processed in {time_ms:.0f} ms"
    st.success(f"✅ **Document analyzed successfully!**{extra}")
