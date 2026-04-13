import io
import json

import fitz  # PyMuPDF
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

from utils.pdf_utils import field_color, render_page_pil, get_page_count


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _field_str(field_val) -> str:
    """Best string representation of a DocumentField."""
    if field_val is None:
        return ""
    for attr in ("value_string", "value_number", "value_date",
                 "value_time", "value_integer", "content"):
        v = getattr(field_val, attr, None)
        if v is not None:
            return str(v)
    return ""


def _conf_bar_html(conf: float | None, threshold: float) -> str:
    if conf is None:
        return '<span style="color:#aaa;font-size:12px">—</span>'
    bar_c = "#22c55e" if conf >= threshold else ("#f59e0b" if conf >= 0.50 else "#ef4444")
    bar_w = int(conf * 80)
    return (
        f'<div style="display:flex;align-items:center;gap:6px">'
        f'<div style="width:80px;height:8px;background:#e5e7eb;border-radius:4px">'
        f'<div style="width:{bar_w}px;height:8px;background:{bar_c};border-radius:4px"></div></div>'
        f'<span style="color:{bar_c};font-weight:700;font-size:13px">{conf:.0%}</span>'
        f'</div>'
    )


def _draw_di_results_on_page(
    pdf_bytes: bytes,
    page_num: int,
    doc_result,
    analyze_result,
    fields: list[str],
    dpi: int = 150,
) -> Image.Image:
    """
    Render one PDF page and draw colored bounding boxes for every extracted field.
    Uses Azure DI page dimensions (in inches) for correct coordinate scaling.
    """
    img, img_w, img_h = render_page_pil(pdf_bytes, page_num, dpi=dpi)
    draw = ImageDraw.Draw(img, "RGBA")

    # Use DI page object for accurate inch→pixel scaling
    di_page = next(
        (p for p in (analyze_result.pages or []) if (p.page_number - 1) == page_num),
        None,
    )
    if di_page is None:
        return img

    sx = img_w / di_page.width
    sy = img_h / di_page.height

    for field_name, field_val in (doc_result.fields or {}).items():
        if field_val is None:
            continue
        color = field_color(fields, field_name)
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)

        for br in (getattr(field_val, "bounding_regions", None) or []):
            if (br.page_number - 1) != page_num:
                continue
            poly = br.polygon or []
            if len(poly) < 8:
                continue
            xs = [poly[i] * sx for i in range(0, len(poly), 2)]
            ys = [poly[i] * sy for i in range(1, len(poly), 2)]
            x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)

            draw.rectangle([x0, y0, x1, y1],
                           fill=(r, g, b, 45),
                           outline=(r, g, b, 230),
                           width=2)
            val_str = _field_str(field_val)[:22]
            label   = f"{field_name}: {val_str}" if val_str else field_name
            lw      = len(label) * 7 + 8
            draw.rectangle([x0, max(0, y0 - 20), x0 + lw, y0],
                           fill=(r, g, b, 230))
            draw.text((x0 + 4, max(0, y0 - 17)), label,
                      fill=(255, 255, 255, 255))
    return img


def _annotated_images_for_doc(
    pdf_bytes: bytes,
    doc_result,
    analyze_result,
    fields: list[str],
    dpi: int = 150,
) -> list[Image.Image]:
    """Return a list of annotated PIL Images — one per page that has boxes (+ page 1 always)."""
    total_pages = get_page_count(pdf_bytes)
    images = []
    for page_num in range(total_pages):
        page_has_boxes = any(
            any(
                (br.page_number - 1) == page_num
                for br in (getattr(fv, "bounding_regions", None) or [])
            )
            for fv in (doc_result.fields or {}).values()
            if fv is not None
        )
        if not page_has_boxes and page_num > 0:
            continue
        img = _draw_di_results_on_page(
            pdf_bytes, page_num, doc_result, analyze_result, fields, dpi=dpi
        )
        images.append((page_num + 1, img))
    return images


# ── Download helpers ──────────────────────────────────────────────────────────

def _images_to_pdf_bytes(page_images: list[tuple[int, Image.Image]]) -> bytes:
    """Convert a list of PIL Images into a single PDF (in memory)."""
    if not page_images:
        return b""
    imgs = [img.convert("RGB") for _, img in page_images]
    buf = io.BytesIO()
    imgs[0].save(buf, format="PDF", save_all=True, append_images=imgs[1:])
    return buf.getvalue()


def _image_to_png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ──────────────────────────────────────────────────────────────────────────────
# Main render function
# ──────────────────────────────────────────────────────────────────────────────

def render_step5(di_endpoint: str, di_key: str):
    st.markdown(
        '<p class="step-header">Step 5 — Test Custom Model</p>',
        unsafe_allow_html=True,
    )
    st.info(
        "Upload one or more PDFs, pick your trained model, and inspect "
        "extracted fields with annotated bounding boxes overlaid on each page."
    )

    # ── Model ID + threshold ──────────────────────────────────────────────────
    col_model, col_thresh = st.columns([3, 1])
    with col_model:
        test_model_id = st.text_input(
            "Model ID to test",
            value=st.session_state.get("model_id", ""),
            placeholder="custom-model-abc12345",
            help="The model_id of the custom model trained in Step 4.",
        )
    with col_thresh:
        conf_threshold = st.slider(
            "Confidence threshold",
            min_value=0.0, max_value=1.0,
            value=0.80, step=0.05,
            help="Fields below this value are highlighted in red.",
        )

    st.divider()

    # ── File upload ───────────────────────────────────────────────────────────
    st.markdown("#### 📂 Upload Documents to Analyse")
    uploaded = st.file_uploader(
        "Choose PDFs",
        type=["pdf"],
        accept_multiple_files=True,
        key="test_upload",
    )

    if "test_files" not in st.session_state:
        st.session_state.test_files = {}
    for f in (uploaded or []):
        st.session_state.test_files[f.name] = f.read()

    if not st.session_state.test_files:
        st.caption("No documents uploaded yet.")
        _nav()
        return

    # ── Thumbnail strip ───────────────────────────────────────────────────────
    st.success(f"✅ {len(st.session_state.test_files)} document(s) ready")
    thumb_cols = st.columns(min(len(st.session_state.test_files), 4))
    for i, (fname, pdf_bytes) in enumerate(st.session_state.test_files.items()):
        with thumb_cols[i % 4]:
            try:
                thumb, _, _ = render_page_pil(pdf_bytes, 0, dpi=72)
                st.image(thumb, caption=fname[:25], use_container_width=True)
            except Exception:
                st.markdown(f"📄 `{fname}`")

    if st.button("🗑️ Clear uploaded documents", key="clear_test"):
        st.session_state.test_files = {}
        st.session_state.pop("test_results_store", None)
        st.rerun()

    st.divider()

    # ── Guards ────────────────────────────────────────────────────────────────
    if not all([di_endpoint, di_key]):
        st.warning("⚠️ Fill in DI Endpoint and Key in the sidebar to enable analysis.")
        _nav()
        return
    if not test_model_id:
        st.warning("⚠️ Enter a Model ID above to enable analysis.")
        _nav()
        return

    # ── Run Analysis ──────────────────────────────────────────────────────────
    if st.button("🔍 Run Analysis", type="primary"):
        _run_analysis(di_endpoint, di_key, test_model_id, conf_threshold)

    _nav()


# ──────────────────────────────────────────────────────────────────────────────
# Analysis engine
# ──────────────────────────────────────────────────────────────────────────────

def _run_analysis(
    di_endpoint: str,
    di_key: str,
    test_model_id: str,
    conf_threshold: float,
):
    client = DocumentIntelligenceClient(
        endpoint=di_endpoint,
        credential=AzureKeyCredential(di_key),
    )

    fields: list[str] = list(st.session_state.get("fields", []))
    all_rows: list[dict] = []

    # Store annotated images per filename for download
    annotated_store: dict[str, list[tuple[int, Image.Image]]] = {}

    progress = st.progress(0, text="Starting analysis…")
    total    = len(st.session_state.test_files)

    for doc_idx, (fname, pdf_bytes) in enumerate(st.session_state.test_files.items()):
        progress.progress(doc_idx / total, text=f"Analysing {fname}…")

        try:
            poller = client.begin_analyze_document(
                model_id=test_model_id,
                content_type="application/pdf",
                body=pdf_bytes,
            )
            result = poller.result()
        except Exception as e:
            st.error(f"❌ Analysis failed for **{fname}**: {e}")
            continue

        if not result.documents:
            st.warning(f"⚠️ No documents extracted from **{fname}**.")
            continue

        for doc in result.documents:
            # Sync field list
            for fn in (doc.fields or {}):
                if fn not in fields:
                    fields.append(fn)

            doc_conf   = getattr(doc, "confidence", None)
            conf_label = f"{doc_conf:.1%}" if doc_conf is not None else "—"

            # ── Document header card ──────────────────────────────────────────
            st.markdown(
                f'<div style="background:#f8fafc;border:1px solid #e2e8f0;'
                f'border-radius:10px;padding:14px 18px;margin:12px 0 6px 0">'
                f'<div style="display:flex;justify-content:space-between;align-items:center">'
                f'<span style="font-weight:700;font-size:1rem">📄 {fname}</span>'
                f'<span style="font-size:13px;color:#64748b">'
                f'Doc confidence: <strong>{conf_label}</strong></span>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

            # ── Field results table ───────────────────────────────────────────
            st.markdown(
                '<div style="display:grid;grid-template-columns:180px 1fr 160px;'
                'gap:10px;padding:6px 12px;background:#f1f5f9;border-radius:6px;'
                'font-weight:700;font-size:13px;color:#475569;margin-bottom:2px">'
                '<span>Field</span><span>Value</span><span>Confidence</span></div>',
                unsafe_allow_html=True,
            )

            for field_name, field_val in sorted((doc.fields or {}).items()):
                val_str  = _field_str(field_val)
                conf_val = getattr(field_val, "confidence", None) if field_val else None
                color    = field_color(fields, field_name)
                low      = conf_val is not None and conf_val < conf_threshold
                row_bg   = "#fff8f8" if low else "white"

                val_display = (
                    f'<span style="font-family:monospace;font-size:13px">{val_str}</span>'
                    if val_str
                    else '<span style="color:#aaa;font-size:12px;font-style:italic">not found</span>'
                )
                st.markdown(
                    f'<div style="display:grid;grid-template-columns:180px 1fr 160px;'
                    f'gap:10px;align-items:center;padding:9px 12px;'
                    f'border-bottom:1px solid #f0f0f0;background:{row_bg}">'
                    f'<span class="annotation-pill" style="background:{color}">{field_name}</span>'
                    f'{val_display}'
                    f'{_conf_bar_html(conf_val, conf_threshold)}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                all_rows.append({
                    "document":        fname,
                    "field":           field_name,
                    "value":           val_str,
                    "confidence":      round(conf_val, 4) if conf_val is not None else None,
                    "above_threshold": (conf_val >= conf_threshold) if conf_val is not None else None,
                })

            # ── Build annotated images ────────────────────────────────────────
            page_images = _annotated_images_for_doc(pdf_bytes, doc, result, fields, dpi=150)
            annotated_store[fname] = page_images

            # ── View annotated pages ──────────────────────────────────────────
            with st.expander("🖼️ View annotated pages", expanded=True):
                if page_images:
                    for page_num, img in page_images:
                        st.image(img, caption=f"Page {page_num}", use_container_width=True)
                else:
                    plain, _, _ = render_page_pil(pdf_bytes, 0, dpi=150)
                    st.image(plain, caption="Page 1 (no bounding regions returned)",
                             use_container_width=True)

            # ── Per-document downloads (image + PDF + JSON) ───────────────────
            st.markdown("**Download this document:**")
            dl1, dl2, dl3 = st.columns(3)
            stem = fname.replace(".pdf", "")

            # Single-page PNG (first annotated page)
            if page_images:
                with dl1:
                    first_img = page_images[0][1]
                    st.download_button(
                        "⬇️ Page 1 as PNG",
                        data=_image_to_png_bytes(first_img),
                        file_name=f"{stem}_annotated_p1.png",
                        mime="image/png",
                        use_container_width=True,
                        key=f"dl_png_{fname}",
                    )

                # All annotated pages as PDF
                with dl2:
                    pdf_out = _images_to_pdf_bytes(page_images)
                    st.download_button(
                        "⬇️ All pages as PDF",
                        data=pdf_out,
                        file_name=f"{stem}_annotated.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key=f"dl_pdf_{fname}",
                    )

            # Per-document JSON
            doc_rows = [r for r in all_rows if r["document"] == fname]
            with dl3:
                st.download_button(
                    "⬇️ Fields as JSON",
                    data=json.dumps(doc_rows, indent=2),
                    file_name=f"{stem}_fields.json",
                    mime="application/json",
                    use_container_width=True,
                    key=f"dl_json_{fname}",
                )

            # ── Raw SDK response ──────────────────────────────────────────────
            with st.expander("🔍 Raw SDK response"):
                raw: dict = {}
                for fn, fv in (doc.fields or {}).items():
                    if fv is None:
                        raw[fn] = None
                        continue
                    d = {}
                    for attr in ("value_string", "value_number", "value_date",
                                 "content", "confidence"):
                        v = getattr(fv, attr, None)
                        if v is not None:
                            d[attr] = v
                    raw[fn] = d
                st.json(raw)

    progress.progress(1.0, text="✅ Analysis complete")

    if not all_rows:
        return

    # ── Cross-document summary ────────────────────────────────────────────────
    st.divider()
    st.markdown("## 📋 Cross-Document Summary")

    df = pd.DataFrame(all_rows)

    try:
        pivot = df.pivot_table(
            index="document", columns="field",
            values="value", aggfunc="first",
        )
        st.dataframe(pivot, use_container_width=True)
    except Exception:
        st.dataframe(
            df[["document", "field", "value", "confidence"]],
            use_container_width=True, hide_index=True,
        )

    # Average confidence per field
    conf_df = df[df["confidence"].notna()].copy()
    if not conf_df.empty:
        conf_df["confidence"] = pd.to_numeric(conf_df["confidence"], errors="coerce")
        avg_conf = (
            conf_df.groupby("field")["confidence"]
            .mean().reset_index()
            .sort_values("confidence", ascending=False)
        )
        st.markdown("**Average Confidence by Field:**")
        for _, row in avg_conf.iterrows():
            c     = row["confidence"]
            bar_c = "#22c55e" if c >= conf_threshold else "#ef4444"
            color = field_color(fields, row["field"]) if row["field"] in fields else "#546E7A"
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;margin:4px 0">'
                f'<span class="annotation-pill" style="background:{color};'
                f'min-width:140px;text-align:center">{row["field"]}</span>'
                f'<div style="width:200px;background:#e5e7eb;border-radius:4px;height:10px">'
                f'<div style="width:{int(c*100)}%;background:{bar_c};'
                f'height:10px;border-radius:4px"></div></div>'
                f'<span style="font-weight:700;color:{bar_c}">{c:.1%}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ──  export ───────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 📥 Export All Results")
    d1, d2, d3 = st.columns(3)

    with d1:
        st.download_button(
            "⬇️ Download CSV",
            data=df.to_csv(index=False),
            file_name="test_results.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with d2:
        st.download_button(
            "⬇️ Download JSON",
            data=df.to_json(orient="records", indent=2),
            file_name="test_results.json",
            mime="application/json",
            use_container_width=True,
        )
    with d3:
        # All annotated pages across all docs → one merged PDF
        all_pages: list[tuple[int, Image.Image]] = []
        for pages in annotated_store.values():
            all_pages.extend(pages)
        if all_pages:
            st.download_button(
                "⬇️ All docs annotated PDF",
                data=_images_to_pdf_bytes(all_pages),
                file_name="all_annotated.pdf",
                mime="application/pdf",
                use_container_width=True,
            )


# ──────────────────────────────────────────────────────────────────────────────
# Navigation
# ──────────────────────────────────────────────────────────────────────────────

def _nav():
    st.divider()
    nav1, nav2 = st.columns(2)
    with nav1:
        if st.button("⬅️ Back to Training"):
            st.session_state.step = 4
            st.rerun()
    with nav2:
        if st.button("🔄 Start New Project"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
