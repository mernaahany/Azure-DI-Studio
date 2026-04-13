import fitz  # PyMuPDF


def build_labels_json(filename: str, annotations: list, pdf_bytes: bytes) -> dict:
    """
    Produces a <pdf>.labels.json matching the Azure DI 2021-03-01 schema.

    Key fixes vs. the previous version:
      1. "labelType": "region" is ONLY set when there is no extractable text
         in the box (scanned / image region).  For all normal text fields it
         must be absent — if you set it on a text field Azure DI treats the
         box as a raw image region and cannot match OCR tokens to it, which
         causes the field to be silently dropped or returned empty at inference.

      2. "key": null is required by the schema.  Omitting it causes some SDK
         versions to silently discard the label.

      3. boundingBoxes uses normalised 0-1 coords (correct for this schema).
         Coords: [x0,y0, x1,y0, x1,y1, x0,y1]  (TL → TR → BR → BL).
    """
    doc    = fitz.open(stream=pdf_bytes, filetype="pdf")
    labels = []

    for ann in annotations:
        page_obj = doc[ann["page"]]
        iw = ann.get("img_width",  1)
        ih = ann.get("img_height", 1)

        # Normalised corner coords (0–1 relative to page dimensions)
        x0n = ann["x"]               / iw
        y0n = ann["y"]               / ih
        x1n = (ann["x"] + ann["w"])  / iw
        y1n = (ann["y"] + ann["h"])  / ih

        # Clamp to [0, 1]
        x0n, y0n = max(0.0, x0n), max(0.0, y0n)
        x1n, y1n = min(1.0, x1n), min(1.0, y1n)

        # Skip degenerate boxes
        if (x1n - x0n) < 0.001 or (y1n - y0n) < 0.001:
            continue

        # Flat 8-element clockwise polygon: TL TR BR BL
        bbox = [x0n, y0n,  x1n, y0n,  x1n, y1n,  x0n, y1n]

        text = ann.get("text", "").strip()

        label_entry: dict = {
            "label": ann["field"],
            "key":   None,           # ← required by schema, must be present
            "value": [
                {
                    "page":          ann["page"] + 1,   # 1-based
                    "text":          text,
                    "boundingBoxes": [bbox],
                }
            ],
        }

        # Only add labelType="region" when there is genuinely no OCR text
        # (e.g. a logo, stamp, or area in a scanned PDF with no selectable text).
        # For any field that has text, omit labelType entirely.
        if not text:
            label_entry["labelType"] = "region"

        labels.append(label_entry)

    doc.close()

    return {
        "$schema":  "https://schema.cognitiveservices.azure.com/formrecognizer/2021-03-01/labels.json",
        "document": filename,
        "labels":   labels,
    }


def build_fields_json(fields: list, field_types: dict, field_formats: dict) -> dict:
    """
    Produces the shared fields.json for a training set.
    Keeps the same structure as before — this part was correct.
    """
    return {
        "$schema": "https://schema.cognitiveservices.azure.com/formrecognizer/2021-03-01/fields.json",
        "fields": [
            {
                "fieldKey":    f,
                "fieldType":   field_types.get(f, "string"),
                "fieldFormat": field_formats.get(f, "not-specified"),
            }
            for f in fields
        ],
        "definitions": {},
    }