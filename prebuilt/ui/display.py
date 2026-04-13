"""
display.py — Display results in JSON and table formats with tabs
"""

import json
import streamlit as st
import pandas as pd
from typing import Any


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
    
    # Tab 1: JSON View
    with tab1:
        render_json_view(parsed_output)
    
    # Tab 2: Tables
    with tab2:
        render_tables_view(parsed_output)
    
    # Tab 3: Key-Value Pairs
    with tab3:
        render_key_value_pairs_view(parsed_output)
    
    # Tab 4: Extracted Fields
    with tab4:
        render_extracted_fields_view(parsed_output)
    
    # Tab 5: Raw Text
    with tab5:
        render_raw_text_view(parsed_output)


def render_json_view(parsed_output: dict):
    """Display full JSON output in an expandable format."""
    st.subheader("Full JSON Output")
    
    col1, col2 = st.columns([0.7, 0.3])
    
    with col1:
        st.write("Complete parsed output in JSON format:")
    
    with col2:
        # Download button
        json_str = json.dumps(parsed_output, indent=2)
        st.download_button(
            label="📥 Download JSON",
            data=json_str,
            file_name=f"{parsed_output['meta']['filename']}_analysis.json",
            mime="application/json",
        )
    
    # Display JSON with syntax highlighting
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
        
        # Convert to DataFrame for better display
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
    
    # Convert to DataFrame
    try:
        df = pd.DataFrame(kv_pairs)
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"Error displaying key-value pairs: {str(e)}")
    
    # Show total count
    st.metric("Total Key-Value Pairs", len(kv_pairs))


def render_extracted_fields_view(parsed_output: dict):
    """Display extracted document fields (Invoice, Receipt, etc.)."""
    st.subheader("Extracted Fields")
    
    fields = parsed_output.get("extracted_fields", {})
    
    if not fields:
        st.info("ℹ️ No extracted fields found. This model may not support field extraction.")
        return
    
    # Create a table of extracted fields
    field_data = []
    for field_name, field_info in fields.items():
        field_data.append({
            "Field": field_name,
            "Value": field_info.get("value", ""),
            "Content": field_info.get("content", ""),
            "Confidence": f"{field_info.get('confidence', 0):.2%}" if field_info.get('confidence') else "N/A",
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
    
    # Display with line count
    lines = raw_text.split("\n")
    st.caption(f"Total Lines: {len(lines)}")
    
    # Use text area for easy selection
    st.text_area(
        "Extracted Text:",
        value=raw_text,
        height=400,
        disabled=True,
        label_visibility="collapsed",
    )
    
    # Download button
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
    
    # Create expandable sections for each page
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
            
            # Show first few lines of page
            lines = page.get("lines", [])[:5]  # First 5 lines
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
