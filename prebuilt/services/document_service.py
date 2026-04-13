"""
document_service.py — Azure Document Intelligence client & analysis runner
"""

from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from utils.config import azure

def get_client() -> DocumentAnalysisClient:
    """Build and return an authenticated Azure Document Analysis client."""
    if not azure.is_configured():
        raise EnvironmentError(
            "Azure credentials not set. Please fill in AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT "
            "and AZURE_DOCUMENT_INTELLIGENCE_KEY in your .env file."
        )
    return DocumentAnalysisClient(
        endpoint=azure.endpoint,
        credential=AzureKeyCredential(azure.key),
    )


def analyze_document(file_bytes: bytes, model_id: str) -> dict:
    """
    Send file bytes to Azure and analyze using the given model_id.
    Returns a structured dict of the raw result.

    Args:
        file_bytes: Raw bytes of the uploaded document.
        model_id:   Azure model identifier (e.g. 'prebuilt-invoice').

    Returns:
        dict with keys: model_id, pages, tables, key_value_pairs, documents, styles
    """
    client = get_client()

    try:
        # Note: Do NOT pass content_type explicitly - SDK handles it automatically for bytes
        poller = client.begin_analyze_document(
            model_id=model_id,
            document=file_bytes,
        )
        result = poller.result()
    except HttpResponseError as e:
        raise RuntimeError(f"Azure API error: {e.message}") from e

    return _serialize_result(result, model_id)


def _serialize_result(result, model_id: str) -> dict:
    """Convert Azure AnalyzeResult into a clean serializable dict."""
    output = {
        "model_id": model_id,
        "pages": [],
        "tables": [],
        "key_value_pairs": [],
        "documents": [],
        "styles": [],
    }

    # ── Pages & Words ──────────────────────────────────────────────────────────
    for page in (result.pages or []):
        page_data = {
            "page_number": page.page_number,
            "width": page.width,
            "height": page.height,
            "unit": page.unit,
            "lines": [],
            "words": [],
        }
        for line in (page.lines or []):
            page_data["lines"].append({
                "content": line.content,
                "polygon": _poly(line.polygon),
            })
        for word in (page.words or []):
            page_data["words"].append({
                "content": word.content,
                "confidence": round(word.confidence, 4) if word.confidence else None,
            })
        output["pages"].append(page_data)

    # ── Tables ─────────────────────────────────────────────────────────────────
    for table in (result.tables or []):
        rows: dict[int, dict[int, str]] = {}
        for cell in table.cells:
            rows.setdefault(cell.row_index, {})[cell.column_index] = cell.content
        output["tables"].append({
            "row_count": table.row_count,
            "column_count": table.column_count,
            "rows": rows,
        })

    # ── Key-Value Pairs ────────────────────────────────────────────────────────
    for kv in (result.key_value_pairs or []):
        key_text = kv.key.content if kv.key else ""
        val_text = kv.value.content if kv.value else ""
        output["key_value_pairs"].append({
            "key": key_text,
            "value": val_text,
            "confidence": round(kv.confidence, 4) if kv.confidence else None,
        })

    # ── Prebuilt Documents (invoice, receipt, etc.) ────────────────────────────
    for doc in (result.documents or []):
        doc_data = {
            "doc_type": doc.doc_type,
            "confidence": round(doc.confidence, 4) if doc.confidence else None,
            "fields": {},
        }
        for field_name, field in (doc.fields or {}).items():
            doc_data["fields"][field_name] = {
                "value": _safe_value(field),
                "value_type": field.value_type if field.value_type else None,
                "confidence": round(field.confidence, 4) if field.confidence else None,
                "content": field.content if field.content else None,
            }
        output["documents"].append(doc_data)

    return output


def _poly(polygon) -> list:
    """Convert polygon points to list of [x, y] pairs."""
    if not polygon:
        return []
    return [[p.x, p.y] for p in polygon]


def _safe_value(field) -> str:
    """Safely extract a display-friendly value from any field type."""
    if field is None:
        return ""
    try:
        val = field.value
        if val is None:
            return field.content or ""
        if hasattr(val, "amount"):          # currency
            return f"{val.symbol or ''}{val.amount}"
        if hasattr(val, "isoformat"):       # date/time
            return val.isoformat()
        if isinstance(val, dict):
            return str({k: _safe_value(v) for k, v in val.items()})
        if isinstance(val, list):
            return ", ".join(_safe_value(i) for i in val)
        return str(val)
    except Exception:
        return field.content or ""


