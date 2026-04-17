"""
parsers/json_parser.py — Transform raw Azure result dict into a clean, export-ready dict.

Unchanged from original — the logic here was already correct and clean.
"""

from datetime import datetime


def build_json_output(raw: dict, filename: str, model_display_name: str) -> dict:
    """
    Convert the serialized Azure result into a structured output dict.

    Output shape:
    {
      "meta":               { filename, model, azure_model_id, analyzed_at },
      "summary":            { total_pages, total_tables, total_kv_pairs, total_fields, total_words },
      "pages":              [ { page_number, dimensions, line_count, word_count, lines } ],
      "tables":             [ { table_index, row_count, column_count, rows } ],
      "key_value_pairs":    [ { key, value, confidence } ],
      "extracted_fields":   { field_name: { value, content, confidence } },
      "raw_text":           "full concatenated text",
    }
    """
    output = {
        "meta": {
            "filename":       filename,
            "model":          model_display_name,
            "azure_model_id": raw.get("model_id", ""),
            "analyzed_at":    datetime.now().isoformat(),
        },
        "summary":           {},
        "pages":             [],
        "tables":            [],
        "key_value_pairs":   raw.get("key_value_pairs", []),
        "extracted_fields":  {},
        "raw_text":          "",
    }

    # ── Pages ──────────────────────────────────────────────────────────────────
    all_lines = []
    for page in raw.get("pages", []): 
        page_out = {
            "page_number": page["page_number"],
            "dimensions":  f"{page.get('width', '?')} x {page.get('height', '?')} {page.get('unit', '')}", 
            "line_count":  len(page.get("lines", [])),
            "word_count":  len(page.get("words", [])),
            "lines":       [l["content"] for l in page.get("lines", [])],
        } #dict for 1 page of output .
        output["pages"].append(page_out)
        all_lines.extend(page_out["lines"])

    output["raw_text"] = "\n".join(all_lines)  # concatenate all the content from the lines into a single raw_text string for easier display and export.

    # ── Tables ─────────────────────────────────────────────────────────────────
    for idx, table in enumerate(raw.get("tables", [])):
        rows_out = []
        raw_rows = table.get("rows", {}) 
        for row_idx in sorted(raw_rows.keys(), key=int): 
            row = raw_rows[row_idx]
            cells = [row.get(str(col), row.get(col, "")) for col in range(table["column_count"])]
            rows_out.append(cells)
        output["tables"].append({
            "table_index":  idx + 1,
            "row_count":    table["row_count"],
            "column_count": table["column_count"], # matrix of table cell contents.
            "rows":         rows_out,
        })

    # ── Prebuilt document fields ────────────────────────────────────────────────
    for doc in raw.get("documents", []):
        for field_name, field_data in doc.get("fields", {}).items():
            output["extracted_fields"][field_name] = {
                "value":      field_data.get("value", ""),
                "content":    field_data.get("content", ""),
                "confidence": field_data.get("confidence"), 
            }

    # ── Summary ────────────────────────────────────────────────────────────────
    output["summary"] = {
        "total_pages":   len(output["pages"]),
        "total_tables":  len(output["tables"]),
        "total_kv_pairs":  len(output["key_value_pairs"]),
        "total_fields":  len(output["extracted_fields"]),
        "total_words":   sum(p["word_count"] for p in output["pages"]),
    }

    return output
