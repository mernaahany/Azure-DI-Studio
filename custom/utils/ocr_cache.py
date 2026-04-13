"""
ocr_cache.py
─────────────────────────────────────────────────────────────────────────────
Runs Azure prebuilt-read (OCR) on uploaded training documents and caches
the word-level results in st.session_state so the API is only called once
per document per session.

Cached structure per document:
{
  "pages": [
    {
      "page_number": 1,           # 1-based, matches Azure API
      "width":  612.0,            # page width  in points
      "height": 792.0,            # page height in points
      "words": [
        {
          "content":   "Invoice",
          "polygon":   [x0,y0, x1,y1, x2,y2, x3,y3],   # points in page units
          "bbox_norm": [x_min_norm, y_min_norm, x_max_norm, y_max_norm]
        }, ...
      ]
    }, ...
  ]
}

bbox_norm is normalised to [0..1] relative to the page dimensions, which
matches the normalised coordinates stored in each annotation — making
overlap calculations straightforward.

Public API
──────────
  is_cached(doc_name)                      → bool
  get_ocr_data(doc_name)                   → dict | None
  clear_cache(doc_name)                    → None
  run_ocr(doc_name, file_bytes,            → dict
          di_endpoint, di_key)
  get_words_in_box(ocr_data, page_number,  → str
                   box_norm, overlap_threshold)
─────────────────────────────────────────────────────────────────────────────
"""

import streamlit as st
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

_CACHE_KEY = "_ocr_read_cache"   # top-level key in st.session_state


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _get_cache() -> dict:
    """Returns (and lazily creates) the OCR cache dict in session state."""
    if _CACHE_KEY not in st.session_state:
        st.session_state[_CACHE_KEY] = {}
    return st.session_state[_CACHE_KEY]


# ─── Public cache API ─────────────────────────────────────────────────────────

def is_cached(doc_name: str) -> bool:
    """Returns True if OCR results for this document are already cached."""
    return doc_name in _get_cache()


def get_ocr_data(doc_name: str) -> dict | None:
    """Returns cached OCR data for doc_name, or None if not cached yet."""
    return _get_cache().get(doc_name)


def clear_cache(doc_name: str) -> None:
    """Removes cached OCR data for doc_name (no-op if not cached)."""
    _get_cache().pop(doc_name, None)


# ─── OCR runner ───────────────────────────────────────────────────────────────

def run_ocr(
    doc_name: str,
    file_bytes: bytes,
    di_endpoint: str,
    di_key: str,
) -> dict:
    """
    Runs Azure prebuilt-read on file_bytes, parses word-level bounding
    polygons into normalised [0..1] bbox_norm coordinates, stores the
    result in session state, and returns it.

    Parameters
    ----------
    doc_name    : display name / key used for caching (usually the filename)
    file_bytes  : raw bytes of the PDF or image
    di_endpoint : Azure Document Intelligence endpoint URL
    di_key      : Azure Document Intelligence API key

    Returns
    -------
    Parsed OCR dict (see module docstring for structure).

    Raises
    ------
    Any exception raised by the Azure SDK is propagated to the caller.
    """
    client = DocumentIntelligenceClient(
        endpoint=di_endpoint,
        credential=AzureKeyCredential(di_key),
    )

    poller = client.begin_analyze_document(
        model_id="prebuilt-read",
        body=file_bytes,
        content_type="application/octet-stream",
    )
    result = poller.result()

    parsed_pages = []
    for page in result.pages or []:
        page_w = page.width  or 1.0
        page_h = page.height or 1.0
        words  = []

        for word in page.words or []:
            poly = word.polygon or []
            # polygon is a flat list: [x0, y0, x1, y1, x2, y2, x3, y3]
            if len(poly) < 8:
                continue

            xs = [poly[i]   for i in range(0, len(poly), 2)]
            ys = [poly[i+1] for i in range(0, len(poly), 2)]
            x_min, x_max = min(xs), max(xs)
            y_min, y_max = min(ys), max(ys)

            words.append({
                "content":   word.content,
                "polygon":   list(poly),
                "bbox_norm": [
                    x_min / page_w,
                    y_min / page_h,
                    x_max / page_w,
                    y_max / page_h,
                ],
            })

        parsed_pages.append({
            "page_number": page.page_number,   # 1-based
            "width":       page_w,
            "height":      page_h,
            "words":       words,
        })

    data = {"pages": parsed_pages}
    _get_cache()[doc_name] = data
    return data


# ─── Text extraction ──────────────────────────────────────────────────────────

def get_words_in_box(
    ocr_data: dict,
    page_number: int,
    box_norm: tuple[float, float, float, float],
    overlap_threshold: float = 0.30,
) -> str:
    """
    Returns the joined text of all words on `page_number` whose normalised
    bounding box overlaps `box_norm` by at least `overlap_threshold` of the
    word's own area.

    Parameters
    ----------
    ocr_data          : cached OCR dict returned by run_ocr()
    page_number       : 1-based page number (matches Azure convention)
    box_norm          : (x1n, y1n, x2n, y2n) — normalised [0..1] coords of
                        the user-drawn rectangle
    overlap_threshold : fraction of the word's area that must lie inside the
                        drawn box for the word to be included (default 0.30)

    Returns
    -------
    Space-joined string of matching words in reading order (top→bottom,
    left→right), or an empty string if nothing matches.
    """
    bx1, by1, bx2, by2 = box_norm
    matched: list[tuple[float, float, str]] = []   # (top, left, content)

    for page in ocr_data.get("pages", []):
        if page["page_number"] != page_number:
            continue

        for word in page["words"]:
            wx1, wy1, wx2, wy2 = word["bbox_norm"]

            # Intersection rectangle
            ix1 = max(bx1, wx1)
            iy1 = max(by1, wy1)
            ix2 = min(bx2, wx2)
            iy2 = min(by2, wy2)

            if ix2 <= ix1 or iy2 <= iy1:
                continue   # no overlap

            inter_area = (ix2 - ix1) * (iy2 - iy1)
            word_area  = max((wx2 - wx1) * (wy2 - wy1), 1e-9)

            if inter_area / word_area >= overlap_threshold:
                # Sort key: round top coord to group lines, then left coord
                matched.append((round(wy1, 3), wx1, word["content"]))

    matched.sort(key=lambda t: (t[0], t[1]))   # reading order
    return " ".join(w[2] for w in matched)