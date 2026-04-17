"""
services/azure_client.py — Azure Document Intelligence client & serialization.

Replaces: document_service.py
Fix: _serialize_field now handles nested list/dict fields recursively,
     so Items in receipts are stored as list[dict] instead of a flat string.
"""

from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from utils.config import azure


def get_client() -> DocumentAnalysisClient:
    """Build and return an authenticated Azure Document Analysis client."""
    if not azure.is_configured():
        raise EnvironmentError(
            "Azure credentials not set. "
            "Please add AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and "
            "AZURE_DOCUMENT_INTELLIGENCE_KEY to your .env file."
        )
    return DocumentAnalysisClient(
        endpoint=azure.endpoint,
        credential=AzureKeyCredential(azure.key),
    )


def analyze_document(file_bytes: bytes, model_id: str) -> dict:
    """
    Send document bytes to Azure and return a clean serializable dict.

    Args:
        file_bytes: Raw bytes of the uploaded document.
        model_id:   Azure model identifier (e.g. 'prebuilt-invoice').

    Returns:
        dict with keys: model_id, pages, tables, key_value_pairs, documents
    """
    client = get_client()

    try:
        poller = client.begin_analyze_document(model_id=model_id, document=file_bytes)
        result = poller.result()
    except HttpResponseError as e:
        raise RuntimeError(f"Azure API error: {e.message}") from e

    return _serialize_result(result, model_id)


# ── Serialization ──────────────────────────────────────────────────────────────

def _serialize_result(result, model_id: str) -> dict:
    """Convert Azure AnalyzeResult SDK object into a plain Python dict."""
    output = {
        "model_id": model_id,
        "pages": [],
        "tables": [], 
        "key_value_pairs": [], # cause not all models return tables or kv pairs, so default to empty lists to avoid KeyErrors in display code.
        "documents": [],
    }

    # Pages & text lines
    for page in (result.pages or []):
        output["pages"].append({
            "page_number": page.page_number,
            "width":       page.width,
            "height":      page.height,
            "unit":        page.unit,
            "lines":  [{"content": l.content} for l in (page.lines or [])],
            "words":  [
                {"content": w.content, "confidence": round(w.confidence, 4) if w.confidence else None}
                for w in (page.words or [])
            ],
        })

    # Tables
    for table in (result.tables or []):
        rows: dict[int, dict[int, str]] = {}
        for cell in table.cells:
            rows.setdefault(cell.row_index, {})[cell.column_index] = cell.content
        output["tables"].append({
            "row_count":    table.row_count,
            "column_count": table.column_count,
            "rows":         rows,
        })

    # Key-value pairs
    for kv in (result.key_value_pairs or []):
        output["key_value_pairs"].append({
            "key":        kv.key.content if kv.key else "",
            "value":      kv.value.content if kv.value else "",
            "confidence": round(kv.confidence, 4) if kv.confidence else None,
        })

    # Prebuilt document fields (invoice, receipt, etc.)
    for doc in (result.documents or []):
        doc_data = {
            "doc_type":   doc.doc_type,
            "confidence": round(doc.confidence, 4) if doc.confidence else None,
            "fields":     {},
        }
        for field_name, field in (doc.fields or {}).items():
            doc_data["fields"][field_name] = {
                "value":      _serialize_field(field),   # ← recursive, preserves lists
                "content":    field.content or None,
                "confidence": round(field.confidence, 4) if field.confidence else None,
            }
        output["documents"].append(doc_data)

    return output


def _serialize_field(field) -> any: 
    """
    Recursively convert any DocumentField value to a plain Python value.

    Handles:
      - CurrencyValue  → "$12.50"
      - date / time    → ISO string
      - list           → list of serialized values  (fixes the Items bug) 
      - dict           → dict of serialized values
      - everything else → str
    """
    if field is None:
        return None

    val = field.value

    if val is None:
        return field.content or ""

    # Currency (has .amount and .symbol)
    if hasattr(val, "amount"):
        return f"{val.symbol or ''}{val.amount}"

    # Date / datetime
    if hasattr(val, "isoformat"):
        return val.isoformat()

    # List (e.g. Items in receipt) — recurse into each element
    if isinstance(val, list):
        return [_serialize_field(item) for item in val]

    # Dict (e.g. Address object) — recurse into each sub-field
    if isinstance(val, dict):
        return {k: _serialize_field(v) for k, v in val.items()}

    return str(val)
