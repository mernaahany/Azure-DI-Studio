"""
pages/2_Custom_Model.py
Custom model trainer — 5-step guided workflow.
Identical logic to the original app.py but with unified theme + Home nav.
"""

import streamlit as st

from prebuilt.ui.theme import apply_theme, PRIMARY, TEXT_MUTED
from utils.config import SESSION_DEFAULTS

from custom.steps.step1_upload import render_step1
from custom.steps.step2_fields import render_step2
from custom.steps.step3_annotate import render_step3
from custom.steps.step4_train import render_step4
from custom.steps.step5_test import render_step5

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Custom Model Trainer — Azure DI",
    page_icon="🏗️",
    layout="wide",
)
apply_theme()

# ── Session state defaults ────────────────────────────────────────────────────
for k, v in SESSION_DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f'<h2 style="color:{PRIMARY};margin-top:0">⚙️ Configuration</h2>', unsafe_allow_html=True)

    di_endpoint    = st.text_input("DI Endpoint",            placeholder="https://<resource>.cognitiveservices.azure.com/")
    di_key         = st.text_input("DI Key",                 type="password")
    blob_conn_str  = st.text_input("Blob Connection String", type="password")
    blob_container = st.text_input("Blob Container",         placeholder="training-docs")

    st.divider()

    # Step progress tracker
    st.markdown("**Workflow Progress**")
    step_labels = ["Upload PDFs", "Define Fields", "Annotate", "Train Model", "Test Model"]
    for i, label in enumerate(step_labels, 1):
        current = st.session_state.step
        if current > i:
            icon, color = "✅", "#27AE60"
        elif current == i:
            icon, color = "▶️", PRIMARY
        else:
            icon, color = "○", TEXT_MUTED
        st.markdown(
            f'<div style="padding:3px 0;color:{color};font-size:0.9rem">'
            f'{icon} &nbsp;{label}</div>',
            unsafe_allow_html=True,
        )

    st.divider()
    if st.button("🏠 Back to Home", use_container_width=True):
        st.switch_page("Home_app.py")

# ── Page header ───────────────────────────────────────────────────────────────
st.markdown(
    f'<h1 style="color:{PRIMARY};margin-bottom:0.2rem">🏗️ Custom Model Trainer</h1>'
    f'<p style="color:{TEXT_MUTED};margin-top:0">Train and test your own Azure Document Intelligence model in 5 steps.</p>',
    unsafe_allow_html=True,
)
st.divider()

# ── Step router ───────────────────────────────────────────────────────────────
step = st.session_state.step

if step == 1:
    render_step1()

elif step == 2:
    render_step2()

elif step == 3:
    render_step3(di_endpoint=di_endpoint, di_key=di_key)

elif step == 4:
    render_step4(di_endpoint=di_endpoint, di_key=di_key)

elif step == 5:
    render_step5(di_endpoint=di_endpoint, di_key=di_key)
