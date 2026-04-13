"""
table_parser.py — Convert parsed JSON output into pandas DataFrames for Streamlit
"""

import pandas as pd


def get_fields_dataframe(parsed: dict) -> pd.DataFrame | None:
    """
    Build a DataFrame from extracted_fields (prebuilt models: invoice, receipt, document).
    Returns None if no fields extracted.
    """
    fields = parsed.get("extracted_fields", {})
    if not fields:
        return None

    rows = []
    for field_name, data in fields.items():
        rows.append({
            "Field": _format_field_name(field_name),
            "Value": data.get("value") or data.get("content") or "—",
            "Confidence": _format_confidence(data.get("confidence")),
        })

    return pd.DataFrame(rows)


def get_kv_dataframe(parsed: dict) -> pd.DataFrame | None:
    """
    Build a DataFrame from key-value pairs (general document / layout models).
    Returns None if empty.
    """
    kvs = parsed.get("key_value_pairs", [])
    if not kvs:
        return None

    rows = []
    for kv in kvs:
        rows.append({
            "Key": kv.get("key", ""),
            "Value": kv.get("value", ""),
            "Confidence": _format_confidence(kv.get("confidence")),
        })

    return pd.DataFrame(rows)


def get_table_dataframes(parsed: dict) -> list[pd.DataFrame]:
    """
    Return a list of DataFrames, one per detected table.
    First row is used as column headers if it looks like a header row.
    """
    dfs = []
    for table in parsed.get("tables", []):
        rows = table.get("rows", [])
        if not rows:
            continue
        # Use first row as header
        header = [str(c) if c else f"Col {i+1}" for i, c in enumerate(rows[0])]
        data = rows[1:] if len(rows) > 1 else rows
        df = pd.DataFrame(data, columns=header)
        dfs.append(df)
    return dfs


def get_pages_dataframe(parsed: dict) -> pd.DataFrame | None:
    """Summary table of pages: page number, dimensions, word count, line count."""
    pages = parsed.get("pages", [])
    if not pages:
        return None

    rows = []
    for p in pages:
        rows.append({
            "Page": p.get("page_number"),
            "Dimensions": p.get("dimensions", ""),
            "Lines": p.get("line_count", 0),
            "Words": p.get("word_count", 0),
        })
    return pd.DataFrame(rows)


def get_summary_dataframe(parsed: dict) -> pd.DataFrame:
    """One-row summary of the analysis result."""
    s = parsed.get("summary", {})
    meta = parsed.get("meta", {})
    rows = [
        {"Metric": "File", "Value": meta.get("filename", "")},
        {"Metric": "Model Used", "Value": meta.get("model", "")},
        {"Metric": "Analyzed At", "Value": meta.get("analyzed_at", "")},
        {"Metric": "Total Pages", "Value": s.get("total_pages", 0)},
        {"Metric": "Total Words", "Value": s.get("total_words", 0)},
        {"Metric": "Tables Found", "Value": s.get("total_tables", 0)},
        {"Metric": "Key-Value Pairs", "Value": s.get("total_key_value_pairs", 0)},
        {"Metric": "Extracted Fields", "Value": s.get("total_extracted_fields", 0)},
    ]
    return pd.DataFrame(rows)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _format_field_name(name: str) -> str:
    """Convert camelCase or PascalCase to Title Case with spaces."""
    import re
    s = re.sub(r"([A-Z])", r" \1", name).strip()
    return s.title()


def _format_confidence(conf) -> str:
    if conf is None:
        return "—"
    return f"{conf * 100:.1f}%"
