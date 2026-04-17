"""
Home.py — Landing page.
Asks the user whether they want the Prebuilt or Custom Model workflow
then navigates to the correct Streamlit page.
"""

import streamlit as st
from theme import apply_theme, PRIMARY, ACCENT, TEXT_MUTED, BORDER   # ← fixed: was prebuilt.ui.theme

st.set_page_config(
    page_title="Azure Document Intelligence",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed",
)

apply_theme()

st.markdown(
    f"""
    <div style="text-align:center;padding:3rem 1rem 2rem 1rem">
        <div style="font-size:3.5rem;margin-bottom:0.5rem">📄</div>
        <h1 style="color:{PRIMARY};font-size:2.4rem;margin:0">
            Azure Document Intelligence
        </h1>
        <p style="color:{TEXT_MUTED};font-size:1.05rem;margin-top:0.5rem;max-width:580px;margin-left:auto;margin-right:auto">
            Extract, analyse, and train on documents using Azure Cognitive Services.
            Choose a workflow below to get started.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Mode cards
col_left, col_right = st.columns(2, gap="large")

with col_left:
    st.markdown(
        """
        <div class="mode-card">
            <div class="icon">🔍</div>
            <h3>Prebuilt Models</h3>
            <p>
                Instantly analyse PDFs and images using Azure's ready-made models:
                OCR, Layout, General Documents, Invoices, and Receipts.
                Upload a file and get structured JSON + table results in seconds.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    if st.button("🔍 Use Prebuilt Models →", type="primary", use_container_width=True, key="go_prebuilt"):
        st.switch_page("pages/1_Prebuilt_Models.py")

with col_right:
    st.markdown(
        """
        <div class="mode-card">
            <div class="icon">🏗️</div>
            <h3>Custom Model</h3>
            <p>
                Train your own extraction model on your specific document type.
                Upload labelled PDFs, draw bounding boxes, define fields, train on Azure,
                and test the model — all in a guided 5-step workflow.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    if st.button("🏗️ Train Custom Model →", use_container_width=True, key="go_custom"):
        st.switch_page("pages/2_Custom_Model.py")

#  Feature comparison 
st.markdown("<br>", unsafe_allow_html=True)
st.divider()
st.markdown(
    f'<h3 style="text-align:center;color:{PRIMARY}">Which should I choose?</h3>',
    unsafe_allow_html=True,
)

cmp1, cmp2, cmp3 = st.columns(3)

with cmp1:
    st.markdown(
        f"""
        <div style="background:{ACCENT}12;border:1px solid {ACCENT}40;border-radius:10px;padding:18px">
        <strong style="color:{ACCENT}">⚡ Speed</strong><br><br>
        <b>Prebuilt</b> — results in seconds, no training needed.<br><br>
        <b>Custom</b> — one-time training (minutes), then fast inference.
        </div>
        """,
        unsafe_allow_html=True,
    )

with cmp2:
    st.markdown(
        """
        <div style="background:#27AE6012;border:1px solid #27AE6040;border-radius:10px;padding:18px">
        <strong style="color:#27AE60">🎯 Accuracy</strong><br><br>
        <b>Prebuilt</b> — optimised for standard document types (invoices, receipts, etc.).<br><br>
        <b>Custom</b> — highest accuracy on <em>your</em> specific document layout.
        </div>
        """,
        unsafe_allow_html=True,
    )

with cmp3:
    st.markdown(
        """
        <div style="background:#8E24AA12;border:1px solid #8E24AA40;border-radius:10px;padding:18px">
        <strong style="color:#8E24AA">📋 Use Case</strong><br><br>
        <b>Prebuilt</b> — generic invoices, receipts, or any text extraction.<br><br>
        <b>Custom</b> — proprietary forms, internal documents, unique layouts.
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    f'<p style="text-align:center;color:{TEXT_MUTED};margin-top:2rem;font-size:0.85rem">'
    f"Powered by Azure Cognitive Services · Document Intelligence"
    f"</p>",
    unsafe_allow_html=True,
)

