import io
import json
import base64

import streamlit as st
import streamlit.components.v1 as _components
from PIL import Image

from utils.pdf_utils import (
    field_color, render_page_pil, get_page_count,
    extract_text_from_box, draw_annotations_on_img,
)
from utils.schema_builders import build_labels_json, build_fields_json
from utils.ocr_cache import is_cached, get_ocr_data, run_ocr, get_words_in_box

CANVAS_W = 860
 
# ─── Session-state key for the chosen extraction mode ────────────────────────
_MODE_KEY = "extraction_mode"   # "PyMuPDF (PDF only)" | "Azure OCR (all formats)"
 
 
def _get_mode() -> str:
    return st.session_state.get(_MODE_KEY, "PyMuPDF (PDF only)")
 
 
# ─────────────────────────────────────────────────────────────────────────────
# OCR side-panel (shown only when Azure OCR mode is selected)
# ─────────────────────────────────────────────────────────────────────────────
 
def _render_ocr_panel(selected_pdf: str, pdf_bytes: bytes, di_endpoint: str, di_key: str):
    """
    Renders the Azure OCR status widget. Allows the user to trigger OCR once
    per document; subsequent draws extract text from the in-memory cache.
    """
    if is_cached(selected_pdf):
        total_words = sum(
            len(p["words"]) for p in get_ocr_data(selected_pdf)["pages"]
        )
        st.success(
            f"✅ **OCR cached** — {total_words} words indexed. "
            "Text will auto-fill when you draw a box."
        )
        if st.button("🔄 Re-run OCR", key="rerun_ocr"):
            with st.spinner("Running Azure prebuilt-read…"):
                try:
                    run_ocr(selected_pdf, pdf_bytes, di_endpoint, di_key)
                    st.rerun()
                except Exception as e:
                    st.error(f"OCR failed: {e}")
    else:
        st.info(
            "💡 **OCR not run yet for this document.**  \n"
            "Click the button below to analyse it with Azure prebuilt-read. "
            "This runs **once per document** — text will auto-fill on every box you draw."
        )
        if not (di_endpoint and di_key):
            st.warning("⚠️ Add your DI Endpoint and Key in the sidebar first.")
        else:
            if st.button("🔍 Run OCR on this document", type="primary", key="run_ocr_btn"):
                with st.spinner("Running Azure prebuilt-read OCR…"):
                    try:
                        run_ocr(selected_pdf, pdf_bytes, di_endpoint, di_key)
                        st.success("✅ OCR complete!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"OCR failed: {e}")
 
 
# ─────────────────────────────────────────────────────────────────────────────
# Text extraction dispatcher
# ─────────────────────────────────────────────────────────────────────────────
 
def _extract_text(
    mode: str,
    selected_pdf: str,
    pdf_bytes: bytes,
    page_num: int,          # 0-based (PyMuPDF convention)
    orig_x: int, orig_y: int, orig_w: int, orig_h: int,
    img_w: int,  img_h: int,
) -> str:
    """
    Unified text extraction that delegates to the appropriate backend.
 
    Returns the extracted text string (may be empty if nothing found).
    """
    if mode == "PyMuPDF (PDF only)":
        return extract_text_from_box(
            pdf_bytes, page_num, orig_x, orig_y, orig_w, orig_h, img_w, img_h,
        )
 
    # ── Azure OCR path ────────────────────────────────────────────────────────
    if not is_cached(selected_pdf):
        return ""   # OCR not run yet; caller shows a warning
 
    # Convert pixel box → normalised [0..1] coords for the OCR lookup
    x1n = orig_x / img_w
    y1n = orig_y / img_h
    x2n = (orig_x + orig_w) / img_w
    y2n = (orig_y + orig_h) / img_h # user-drawn box is converted to normalised coordinates to match the format of the OCR.
 
    return get_words_in_box( #overlaping , words.
        ocr_data=get_ocr_data(selected_pdf),
        page_number=page_num + 1,          # Azure OCR is 1-based
        box_norm=(x1n, y1n, x2n, y2n), #user bardo btmatch m3  ocr azure
    )
 
 
# ─────────────────────────────────────────────────────────────────────────────
# Main render function
# ─────────────────────────────────────────────────────────────────────────────
 
def render_step3(di_endpoint: str = "", di_key: str = ""):
    """
    Renders the annotation step.
 
    Parameters
    ----------
    di_endpoint : Azure DI endpoint (forwarded from app.py sidebar).
                  Only needed when Azure OCR mode is selected.
    di_key      : Azure DI API key. Same caveat as above.
    """
    st.markdown('<p class="step-header">Step 3 — Annotate Documents</p>', unsafe_allow_html=True)
 
    filenames = list(st.session_state.uploaded_files.keys())
    fields    = st.session_state.fields
 
    # ── Extraction mode selector ──────────────────────────────────────────────
    mode_col, info_col = st.columns([2, 3])
    with mode_col:
        mode = st.radio(
            "Text extraction method",
            ["PyMuPDF (PDF only)", "Azure OCR (all formats)"],
            index=0 if _get_mode() == "PyMuPDF (PDF only)" else 1,
            horizontal=True,
            help=(
                "**PyMuPDF** — instant, works offline, only picks up selectable "
                "text in native PDFs.  \n"
                "**Azure OCR** — uses prebuilt-read for accurate text from scanned "
                "documents and images; runs once per document and caches the result."
            ),
        )
        st.session_state[_MODE_KEY] = mode
 
    with info_col:
        if mode == "PyMuPDF (PDF only)":
            st.info(
                "⚡ **PyMuPDF** — text is extracted instantly from the PDF layer. "
                "Returns empty for scanned or image-based PDFs."
            )
        else:
            st.info(
                "☁️ **Azure OCR** — run OCR once per document (button appears below the "
                "canvas). After that, every box you draw auto-fills text from the cache."
            )
 
    st.divider()
 
    # ── Top controls ──────────────────────────────────────────────────────────
    ctrl1, ctrl2, ctrl3 = st.columns([2, 1, 1])
 
    with ctrl1:
        sel_idx = (
            filenames.index(st.session_state.anno_pdf)
            if st.session_state.anno_pdf in filenames
            else 0
        )
        selected_pdf = st.selectbox("Document", filenames, index=sel_idx)
        if selected_pdf != st.session_state.anno_pdf:
            st.session_state.anno_pdf    = selected_pdf
            st.session_state.anno_page   = 0
            st.session_state.pending_box = None
            st.session_state.canvas_key += 1
            st.rerun()
 
    pdf_bytes   = st.session_state.uploaded_files[selected_pdf]
    total_pages = get_page_count(pdf_bytes)
 
    with ctrl2:
        page_num = (
            st.number_input(
                "Page", min_value=1, max_value=total_pages,
                value=st.session_state.anno_page + 1,
            ) - 1
        )
        if page_num != st.session_state.anno_page:
            st.session_state.anno_page   = page_num
            st.session_state.pending_box = None
            st.session_state.canvas_key += 1
            st.rerun()
 
    with ctrl3:
        field_idx = st.selectbox(
            "Field to label", range(len(fields)),
            format_func=lambda i: fields[i],
            index=min(st.session_state.anno_field_idx, len(fields) - 1),
        )
        st.session_state.anno_field_idx = field_idx
        active_field = fields[field_idx]
        active_color = field_color(fields, active_field)
 
    # Method badge in the drawing hint
    method_badge = (
        "PyMuPDF 🐍" if mode == "PyMuPDF (PDF only)"
        else "Azure OCR ☁️"
    )
    st.markdown(
        f'<div style="margin:4px 0 10px 0;font-size:14px">'
        f'Drawing: <span class="annotation-pill" style="background:{active_color}">'
        f'{active_field}</span>'
        f'&nbsp;&nbsp;<span style="color:#888;font-size:12px">'
        f'Draw a box → text extracted automatically via {method_badge}'
        f'</span></div>',
        unsafe_allow_html=True,
    )
 
    # ── Azure OCR panel (only in OCR mode) ───────────────────────────────────
    if mode == "Azure OCR (all formats)":
        _render_ocr_panel(selected_pdf, pdf_bytes, di_endpoint, di_key)
        st.divider()
 
    # ── Render page ───────────────────────────────────────────────────────────
    img, img_w, img_h = render_page_pil(pdf_bytes, page_num, dpi=150)
    annotated_bg = draw_annotations_on_img(
        img, st.session_state.annotations.get(selected_pdf, []), fields, page_num,
    )
 
    scale    = CANVAS_W / img_w
    canvas_h = int(img_h * scale)
    bg_img   = annotated_bg.resize((CANVAS_W, canvas_h), Image.LANCZOS)
 
    buf = io.BytesIO()
    bg_img.save(buf, format="PNG")
    bg_data_url = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
 
    saved_anns_for_canvas = [
        {
            "field": a["field"],
            "color": field_color(fields, a["field"]),
            "x":  int(a["x"] * scale), "y": int(a["y"] * scale),
            "w":  int(a["w"] * scale), "h": int(a["h"] * scale),
            "text": a.get("text", ""),
        }
        for a in st.session_state.annotations.get(selected_pdf, [])
        if a["page"] == page_num
    ]
    saved_json = json.dumps(saved_anns_for_canvas)
 
    canvas_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  *{{margin:0;padding:0;box-sizing:border-box;}}
  body{{background:transparent;font-family:sans-serif;}}
  #wrap{{position:relative;width:{CANVAS_W}px;height:{canvas_h}px;
         border:2px solid #e0e0e0;border-radius:4px;cursor:crosshair;
         user-select:none;overflow:hidden;}}
  #bg{{position:absolute;top:0;left:0;width:{CANVAS_W}px;height:{canvas_h}px;
       display:block;pointer-events:none;}}
  #cv{{position:absolute;top:0;left:0;}}
  #statusbar{{margin-top:6px;padding:6px 10px;background:#f8f9fa;
              border:1px solid #dee2e6;border-radius:4px;font-size:13px;
              color:#495057;min-height:32px;display:flex;align-items:center;gap:8px;}}
  .pill{{display:inline-block;padding:2px 8px;border-radius:12px;
         font-size:11px;font-weight:700;color:white;}}
  kbd{{background:#e9ecef;border:1px solid #adb5bd;border-radius:3px;
       padding:1px 5px;font-size:11px;font-family:monospace;}}
</style>
</head><body>
<div id="wrap">
  <img id="bg" src="{bg_data_url}"/>
  <canvas id="cv" width="{CANVAS_W}" height="{canvas_h}"></canvas>
</div>
<div id="statusbar">
  <span id="statustext">🖊️ Click and drag to draw a bounding box — text is extracted automatically</span>
</div>
<script>
(function(){{
  const cv=document.getElementById('cv');
  const ctx=cv.getContext('2d');
  const statusEl=document.getElementById('statustext');
  const FIELD={json.dumps(active_field)};
  const COLOR={json.dumps(active_color)};
  const SAVED={saved_json};
  let drawing=false,committed=false,sx=0,sy=0,ex=0,ey=0,finalBox=null;
 
  function getPos(e){{
    const r=cv.getBoundingClientRect();
    return{{x:(e.touches?e.touches[0].clientX:e.clientX)-r.left,
            y:(e.touches?e.touches[0].clientY:e.clientY)-r.top}};
  }}
  function rgba(hex,a){{
    const r=parseInt(hex.slice(1,3),16),g=parseInt(hex.slice(3,5),16),b=parseInt(hex.slice(5,7),16);
    return `rgba(${{r}},${{g}},${{b}},${{a}})`;
  }}
  function drawLabel(x,y,color,field,text){{
    const label=text?`${{field}}: ${{text.substring(0,22)}}`:field;
    ctx.font='bold 12px sans-serif';
    const tw=ctx.measureText(label).width;
    ctx.fillStyle=color;
    ctx.fillRect(x,Math.max(0,y-20),tw+10,20);
    ctx.fillStyle='#fff';
    ctx.fillText(label,x+5,Math.max(0,y-6));
  }}
  function redraw(){{
    ctx.clearRect(0,0,cv.width,cv.height);
    for(const a of SAVED){{
      ctx.fillStyle=rgba(a.color,0.15);ctx.strokeStyle=a.color;
      ctx.lineWidth=2;ctx.setLineDash([]);
      ctx.fillRect(a.x,a.y,a.w,a.h);ctx.strokeRect(a.x,a.y,a.w,a.h);
      drawLabel(a.x,a.y,a.color,a.field,a.text);
    }}
    if((drawing||committed)&&!(ex===0&&ey===0)){{
      const x=Math.min(sx,ex),y=Math.min(sy,ey);
      const w=Math.abs(ex-sx),h=Math.abs(ey-sy);
      ctx.fillStyle=rgba(COLOR,0.2);ctx.strokeStyle=COLOR;ctx.lineWidth=2;
      ctx.setLineDash(drawing?[5,3]:[]);
      ctx.fillRect(x,y,w,h);ctx.strokeRect(x,y,w,h);
      ctx.setLineDash([]);
      if(!drawing&&w>5&&h>5) drawLabel(x,y,COLOR,FIELD,'');
    }}
  }}
  function setBridge(payload){{
    const inp=window.parent.document.querySelector('input[aria-label="__bbox_bridge__"]');
    if(inp){{
      const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
      s.call(inp,JSON.stringify(payload));
      inp.dispatchEvent(new Event('input',{{bubbles:true}}));
    }}
  }}
  cv.addEventListener('mousedown',e=>{{
    const p=getPos(e);sx=p.x;sy=p.y;ex=p.x;ey=p.y;
    drawing=true;committed=false;finalBox=null;redraw();
  }});
  cv.addEventListener('mousemove',e=>{{
    if(!drawing)return;const p=getPos(e);ex=p.x;ey=p.y;redraw();
  }});
  cv.addEventListener('mouseup',e=>{{
    if(!drawing)return;drawing=false;
    const x=Math.round(Math.min(sx,ex)),y=Math.round(Math.min(sy,ey));
    const w=Math.round(Math.abs(ex-sx)),h=Math.round(Math.abs(ey-sy));
    if(w>5&&h>5){{
      committed=true;finalBox={{x,y,w,h}};redraw();
      setBridge({{x,y,w,h,action:"coords"}});
      statusEl.innerHTML=
        `<span class="pill" style="background:${{COLOR}}">${{FIELD}}</span>`+
        `&nbsp;Box: ${{w}}&times;${{h}}px &nbsp;`+
        `<strong>⚡ Press <kbd>Enter</kbd> to save &amp; extract text</strong>`+
        `&nbsp;|&nbsp;<span style="cursor:pointer;color:#dc3545" onclick="clearBox()">✕ discard</span>`;
    }}
  }});
  cv.addEventListener('touchstart',e=>{{e.preventDefault();
    cv.dispatchEvent(new MouseEvent('mousedown',{{clientX:e.touches[0].clientX,clientY:e.touches[0].clientY}}));}});
  cv.addEventListener('touchmove',e=>{{e.preventDefault();
    cv.dispatchEvent(new MouseEvent('mousemove',{{clientX:e.touches[0].clientX,clientY:e.touches[0].clientY}}));}});
  cv.addEventListener('touchend',e=>{{e.preventDefault();
    cv.dispatchEvent(new MouseEvent('mouseup',{{}}));}});
  window.addEventListener('keydown',e=>{{
    if(e.key==='Enter'&&committed&&finalBox) sendToStreamlit();
  }});
  function clearBox(){{
    committed=false;finalBox=null;ex=0;ey=0;redraw();
    setBridge({{x:0,y:0,w:0,h:0,action:"clear"}});
    statusEl.innerHTML='🖊️ Click and drag to draw a bounding box — text is extracted automatically';
  }}
  function sendToStreamlit(){{
    if(!finalBox)return;
    setBridge({{...finalBox,action:"save"}});
    statusEl.innerHTML='<span style="color:green">✅ Coords sent — click Save button</span>';
    committed=false;finalBox=null;ex=0;ey=0;
    setTimeout(()=>{{statusEl.innerHTML='🖊️ Click and drag to draw a bounding box — text is extracted automatically';}},3000);
  }}
  window.clearBox=clearBox;
  window.sendToSt=sendToStreamlit;
  redraw();
}})();
</script>
</body></html>"""
 
    _components.html(canvas_html, height=canvas_h + 60, scrolling=False)
 
    # ── Hidden bridge input ───────────────────────────────────────────────────
    bridge_raw = st.text_input(
        "__bbox_bridge__",
        value="",
        key=f"bridge_{st.session_state.canvas_key}",
        label_visibility="collapsed",
    )
 
    if bridge_raw and bridge_raw.startswith("{"):
        try:
            coords = json.loads(bridge_raw)
            if coords.get("action") in ("coords", "save") and coords.get("w", 0) > 5:
                st.session_state.pending_box = {
                    "x": int(coords["x"]), "y": int(coords["y"]),
                    "w": int(coords["w"]), "h": int(coords["h"]),
                }
            elif coords.get("action") == "clear":
                st.session_state.pending_box = None
        except Exception:
            pass
 
    pending = st.session_state.pending_box or {}
 
    if pending:
        st.markdown(
            f'<div style="font-size:12px;color:#555;margin-bottom:4px;">'
            f'📐 Pending box: <code>x={pending["x"]}  y={pending["y"]}  '
            f'w={pending["w"]}  h={pending["h"]}</code>'
            f'&nbsp;— edit if needed, then click Save</div>',
            unsafe_allow_html=True,
        )
 
    # ── Coordinate form ───────────────────────────────────────────────────────
    with st.form(key=f"bbox_form_{st.session_state.canvas_key}", border=False):
        fc = st.columns([1, 1, 1, 1, 2])
        with fc[0]: bx = st.number_input("X", min_value=0, max_value=CANVAS_W, value=int(pending.get("x", 0)))
        with fc[1]: by = st.number_input("Y", min_value=0, max_value=canvas_h,  value=int(pending.get("y", 0)))
        with fc[2]: bw = st.number_input("W", min_value=0, max_value=CANVAS_W,  value=int(pending.get("w", 0)))
        with fc[3]: bh = st.number_input("H", min_value=0, max_value=canvas_h,  value=int(pending.get("h", 0)))
        with fc[4]:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            save_clicked = st.form_submit_button(
                f"⏎  Save + Extract Text  「{active_field}」",
                type="primary", use_container_width=True,
            )
 
    # ── AUTO EXTRACT on save ──────────────────────────────────────────────────
    if save_clicked and bw > 5 and bh > 5:
        orig_x = int(bx / scale)
        orig_y = int(by / scale)
        orig_w = int(bw / scale)
        orig_h = int(bh / scale)
 
        spinner_msg = (
            "🔍 Extracting text via PyMuPDF…"
            if mode == "PyMuPDF (PDF only)"
            else "🔍 Extracting text from Azure OCR cache…"
        )
 
        with st.spinner(spinner_msg):
            extracted_text = _extract_text(
                mode, selected_pdf, pdf_bytes,
                page_num, orig_x, orig_y, orig_w, orig_h, img_w, img_h,
            )
 
        # Warn if Azure OCR mode was chosen but OCR hasn't been run yet
        if mode == "Azure OCR (all formats)" and not is_cached(selected_pdf) and not extracted_text:
            st.warning(
                "⚠️ OCR has not been run for this document yet. "
                "Click **Run OCR on this document** above to enable automatic text extraction."
            )
 
        ann = {
            "field":      active_field,
            "page":       page_num,
            "x":          orig_x, "y": orig_y,
            "w":          orig_w, "h": orig_h,
            "img_width":  img_w,
            "img_height": img_h,
            "text":       extracted_text,
        }
        st.session_state.annotations.setdefault(selected_pdf, []).append(ann)
        st.session_state.pending_box = None
        st.session_state.canvas_key += 1
 
        if extracted_text:
            st.success(f"✅ Saved **{active_field}** on page {page_num + 1}")
            st.markdown(
                f'<div class="extracted-text-box">'
                f'🔍 <strong>Auto-extracted ({mode}):</strong>'
                f'&nbsp;"{extracted_text}"</div>',
                unsafe_allow_html=True,
            )
        else:
            st.warning(f"✅ Saved **{active_field}** — no text found in region.")
            st.markdown(
                '<div class="no-text-box">⚠️ <strong>No text detected.</strong> '
                'Use the override below to enter text manually.</div>',
                unsafe_allow_html=True,
            )
        st.rerun()
 
    # ── Manual text override ──────────────────────────────────────────────────
    with st.expander("✏️ Manually override extracted text (last annotation)"):
        saved_list = st.session_state.annotations.get(selected_pdf, [])
        if saved_list:
            last = saved_list[-1]
            new_text = st.text_input(
                f"Text for last annotation ({last['field']}, pg {last['page']+1})",
                value=last.get("text", ""),
                key=f"override_{st.session_state.canvas_key}",
            )
            if st.button("✅ Update text", key=f"upd_{st.session_state.canvas_key}"):
                st.session_state.annotations[selected_pdf][-1]["text"] = new_text
                st.success("Text updated!")
                st.session_state.canvas_key += 1
                st.rerun()
        else:
            st.info("No annotations yet.")
 
    # ── Saved annotations table ───────────────────────────────────────────────
    st.divider()
    saved = st.session_state.annotations.get(selected_pdf, [])
    if saved:
        st.markdown(f"**Annotations for `{selected_pdf}`** — {len(saved)} saved")
        hc = st.columns([2, 1, 3, 3, 1])
        for h, t in zip(hc, ["Field", "Page", "Region (px)", "Extracted Text", ""]):
            h.markdown(f"**{t}**")
        for i, a in enumerate(saved):
            c1, c2, c3, c4, c5 = st.columns([2, 1, 3, 3, 1])
            color    = field_color(fields, a["field"])
            text_val = a.get("text", "")
            c1.markdown(
                f'<span class="annotation-pill" style="background:{color}">{a["field"]}</span>',
                unsafe_allow_html=True,
            )
            c2.markdown(f"pg {a['page']+1}")
            c3.markdown(f"`x={a['x']} y={a['y']} {a['w']}×{a['h']}`")
            if text_val:
                c4.markdown(
                    f'<span style="color:#276749;font-family:monospace;font-size:12px">"{text_val}"</span>',
                    unsafe_allow_html=True,
                )
            else:
                c4.markdown( #  extracted text is empty
                    '<span style="color:#c53030;font-size:12px">⚠ no text</span>',
                    unsafe_allow_html=True,
                )
            if c5.button("✕", key=f"rm_{selected_pdf}_{i}"):
                st.session_state.annotations[selected_pdf].pop(i)
                st.session_state.canvas_key += 1
                st.rerun()
    else:
        st.info("No annotations yet for this document. Draw a box above and save it.")
 
    # ── Live JSON preview ─────────────────────────────────────────────────────
    st.divider()
    with st.expander("🔍 Preview generated JSON files for this document"):
        tab1, tab2 = st.tabs(["labels.json", "fields.json"])
        with tab1:
            if saved:
                st.json(build_labels_json(selected_pdf, saved, pdf_bytes))
            else:
                st.info("No annotations yet.")
        with tab2:
            st.json(build_fields_json(
                st.session_state.fields,
                st.session_state.field_types,
                st.session_state.field_formats,
            ))
 
    # ── Coverage summary ──────────────────────────────────────────────────────
    st.divider()
    st.markdown("**Coverage across all documents:**")
    prog_cols = st.columns(len(filenames))
    all_done  = True
    for i, fname in enumerate(filenames):
        anns_for = st.session_state.annotations.get(fname, [])
        n        = len(anns_for)
        with_txt = sum(1 for a in anns_for if a.get("text"))
        ocr_status = (
            " · OCR ✅" if is_cached(fname)
            else (" · OCR ⏳" if mode == "Azure OCR (all formats)" else "")
        )
        with prog_cols[i]:
            if n == 0:
                all_done = False
                st.markdown(f"❌ `{fname[:18]}`\n\n0 boxes{ocr_status}")
            else:
                st.markdown(f"✅ `{fname[:18]}`\n\n{n} box(es), {with_txt} with text{ocr_status}")
 
    nav1, nav2 = st.columns(2)
    with nav1:
        if st.button("⬅️ Back to Fields"):
            st.session_state.step = 2
            st.rerun()
    with nav2:
        if all_done:
            if st.button("➡️ Train Model", type="primary"):
                st.session_state.step = 4
                st.rerun()
        else:
            st.warning("Add at least 1 annotation per document before training.")
