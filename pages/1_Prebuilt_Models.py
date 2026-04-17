"""
app.py — Main Streamlit entry point.

Run with:
    streamlit run app.py
"""

import streamlit as st
from prebuilt.layout import configure_page, apply_custom_css, render_header, setup_sidebar
from prebuilt.display import render_results, render_error, render_success
from prebuilt.analyzer import run_analysis


def main():
    configure_page() # set page title, icon, layout, and theme
    apply_custom_css() 

    page, selected_model = setup_sidebar()
    render_header()

    # ── Upload & Analyze ───────────────────────────────────────────────────────
    if page == "📤 Upload & Analyze":

        uploaded = st.file_uploader(
            "Upload a document",
            type=["pdf", "png", "jpg", "jpeg", "tiff", "bmp"],
            help="Supported: PDF, PNG, JPG, JPEG, TIFF, BMP — max 50 MB",
        )

        if uploaded is not None:
            st.write(f"**File:** `{uploaded.name}` — **Model:** `{selected_model}`")

            if st.button("🚀 Analyze Document", type="primary"):
                with st.spinner("Sending to Azure Document Intelligence…"): 
                    result = run_analysis(
                        file_bytes=uploaded.read(),
                        filename=uploaded.name,
                        display_name=selected_model,
                    )

                if result.success:
                    render_success(result.saved_path, result.processing_time_ms)
                    st.session_state["last_result"] = result.parsed
                    render_results(result.parsed)
                else:
                    render_error(result.error)

    # ── View Results (last analysis) ───────────────────────────────────────────
    elif page == "📊 View Results":
        if "last_result" not in st.session_state:
            st.info("ℹ️ No results yet. Upload and analyze a document first.")
        else:
            render_results(st.session_state["last_result"])

    # ── Model Info ─────────────────────────────────────────────────────────────
    elif page == "📋 Model Info":
        from prebuilt.registry import MODELS
        st.subheader("Available Models")
        for name, model in MODELS.items():
            with st.expander(f"**{name}**"):
                st.write(f"**Azure Model ID:** `{model.model_id}`")
                st.write(f"**Description:** {model.description}")
                st.write(f"**Enhanced extraction:** {'✅ Yes' if model.has_enhancer else '—'}")


if __name__ == "__main__":
    main()
