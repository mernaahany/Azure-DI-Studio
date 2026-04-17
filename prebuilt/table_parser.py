"""
parsers/table_parser.py — Convert parsed JSON output into pandas DataFrames.

Now actually used by ui/display.py (was dead code in the original project).
"""

import re
import pandas as pd


def get_summary_df(parsed: dict) -> pd.DataFrame:
    """One overview table: file info + counts."""
    s = parsed.get("summary", {})
    m = parsed.get("meta", {})
    rows = [
        {"Metric": "File",            "Value": m.get("filename", "")},
        {"Metric": "Model",           "Value": m.get("model", "")},
        {"Metric": "Analyzed At",     "Value": m.get("analyzed_at", "")},
        {"Metric": "Total Pages",     "Value": s.get("total_pages", 0)},
        {"Metric": "Total Words",     "Value": s.get("total_words", 0)},
        {"Metric": "Tables Found",    "Value": s.get("total_tables", 0)},
        {"Metric": "Key-Value Pairs", "Value": s.get("total_kv_pairs", 0)},
        {"Metric": "Extracted Fields","Value": s.get("total_fields", 0)},
    ]
    return pd.DataFrame(rows)


def get_fields_df(parsed: dict) -> pd.DataFrame | None:
    """Extracted fields table (Invoice, Receipt, General Document)."""
    fields = parsed.get("extracted_fields", {})
    if not fields:
        return None
    rows = [
        {
            "Field":      _to_title(name),
            "Value":      _display_value(data.get("value")),
            "Confidence": _fmt_confidence(data.get("confidence")),
        }
        for name, data in fields.items()
    ]
    return pd.DataFrame(rows)


def get_kv_df(parsed: dict) -> pd.DataFrame | None:
    """Key-value pairs table (General Document / Layout models)."""
    kvs = parsed.get("key_value_pairs", [])
    if not kvs:
        return None
    rows = [
        {
            "Key":        kv.get("key", ""),
            "Value":      kv.get("value", ""),
            "Confidence": _fmt_confidence(kv.get("confidence")),
        }
        for kv in kvs
    ]
    return pd.DataFrame(rows)


def get_tables_dfs(parsed: dict) -> list[pd.DataFrame]:
    """One DataFrame per detected table. First row used as header."""
    dfs = []
    for table in parsed.get("tables", []):
        rows = table.get("rows", [])
        if not rows:
            continue
        header = [str(c) if c else f"Col {i+1}" for i, c in enumerate(rows[0])]
        data   = rows[1:] if len(rows) > 1 else rows
        dfs.append(pd.DataFrame(data, columns=header))
    return dfs


def get_pages_df(parsed: dict) -> pd.DataFrame | None:
    """Summary table of pages: page number, dimensions, lines, words."""
    pages = parsed.get("pages", [])
    if not pages:
        return None
    rows = [
        {
            "Page":       p.get("page_number"),
            "Dimensions": p.get("dimensions", ""),
            "Lines":      p.get("line_count", 0),
            "Words":      p.get("word_count", 0),
        }
        for p in pages
    ]
    return pd.DataFrame(rows)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _to_title(name: str) -> str:
    """Convert PascalCase / camelCase field names to 'Title Case With Spaces'."""
    s = re.sub(r"([A-Z])", r" \1", name).strip()
    return s.title()


def _fmt_confidence(conf) -> str:
    if conf is None:
        return "—"
    return f"{conf * 100:.1f}%"


def _display_value(val) -> str:
    """Convert any value type to a readable string for table display."""
    if val is None:
        return "—"
    if isinstance(val, list):
        return f"[{len(val)} items]"
    if isinstance(val, dict):
        return str(val)
    return str(val)
