import streamlit as st
from utils.pdf_utils import render_page_pil


# All file types accepted by Azure Document Intelligence OCR
ACCEPTED_EXTENSIONS = [
    "pdf",
    "png",
    "jpg", "jpeg", "jpe", "jif", "jfi", "jfif",
    "tif", "tiff",
]
 
# Extensions we can render a visual thumbnail for
_RENDERABLE_AS_PDF = {"pdf"}
_RENDERABLE_AS_IMAGE = {"png", "jpg", "jpeg", "jpe", "jif", "jfi", "jfif", "tif", "tiff"}
 
# Icon fallbacks for non-renderable types
_TYPE_ICONS = {
    "pdf":  "📄", "png": "🖼️", "jpg": "🖼️", "jpeg": "🖼️",
    "jpe":  "🖼️", "jif": "🖼️", "jfi": "🖼️", "jfif": "🖼️",
    "tif":  "🖼️", "tiff": "🖼️",
}
 
 
def _get_ext(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
 
 
def _render_thumbnail(fname: str, file_bytes: bytes):
    """Try to show a preview; fall back to a labelled icon on any error."""
    ext = _get_ext(fname)
    try:
        if ext in _RENDERABLE_AS_PDF:
            thumb, _, _ = render_page_pil(file_bytes, 0, dpi=72)
            st.image(thumb, caption=fname[:25], use_container_width=True)
            return
        if ext in _RENDERABLE_AS_IMAGE:
            st.image(file_bytes, caption=fname[:25], use_container_width=True)
            return
    except Exception:
        pass
    # Non-renderable or render failed
    icon = _TYPE_ICONS.get(ext, "📁")
    st.markdown(
        f"<div style='text-align:center;font-size:2rem'>{icon}</div>"
        f"<div style='text-align:center;font-size:11px;color:#555'>{fname[:25]}</div>",
        unsafe_allow_html=True,
    )
 
 
def render_step1():
    st.markdown('<p class="step-header">Step 1 — Upload Documents</p>', unsafe_allow_html=True)
    st.info(
        "Upload **at least 5 documents** to train a robust custom model.  \n"
        "Supported formats: **PDF, PNG, JPG/JPEG, TIFF**"
    )
 
    uploaded = st.file_uploader(
        "Choose documents",
        type=ACCEPTED_EXTENSIONS,
        accept_multiple_files=True,
    )
    if uploaded:
        for f in uploaded:
            if f.name not in st.session_state.uploaded_files:
                st.session_state.uploaded_files[f.name] = f.read()
 
    count = len(st.session_state.uploaded_files)
    if count:
        st.success(f"✅ {count} document(s) ready")
        cols = st.columns(min(count, 4))
        for i, fname in enumerate(st.session_state.uploaded_files):
            with cols[i % 4]:
                _render_thumbnail(fname, st.session_state.uploaded_files[fname])
 
        if count < 5:
            st.warning(f"Need {5 - count} more document(s) to continue.")
        else:
            if st.button("➡️ Define Fields", type="primary"):
                st.session_state.step = 2
                st.rerun()
 
