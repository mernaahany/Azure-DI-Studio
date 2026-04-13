"""
back_app.py — Production-ready FastAPI backend for Azure Document Intelligence.

Run with:
    uvicorn back_app:app --host 0.0.0.0 --port 8000 --reload
    http://localhost:8000/docs for interactive API docs.
    http://localhost:8000/health 

Example request (curl):
    curl -X POST "http://localhost:8000/analyze" \
         -H "accept: application/json" \
         -F "file=@invoice.pdf" \
         -F "model_type=invoice" \
         -F "endpoint=https://<resource>.cognitiveservices.azure.com/" \
         -F "key=<your-key>"

Example response:
    {
      "filename": "invoice.pdf",
      "model_used": "prebuilt-invoice",
      "raw": { ... },          ← full Azure SDK dict
      "fields": {              ← clean extracted fields
        "VendorName":   { "value": "Contoso Ltd", "confidence": 0.98 },
        "InvoiceTotal": { "value": "1200.00",     "confidence": 0.97 }
      }
    }
"""

import os
import logging
from datetime import datetime
from typing import Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Azure Document Intelligence SDK (v3 GA)
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#  App init 
app = FastAPI(
    title="Azure Document Intelligence API",
    description="Upload documents and extract structured data using Azure DI prebuilt or custom models.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

#  allow Streamlit (localhost:8501) and any origin in dev
#  tighten CORS  to only allow frontend domain(s)
#  see https://fastapi.tiangolo.com/tutorial/cors/ for details
#  Note: CORS is only relevant if you call this API from a browser-based frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten to ["http://localhost:8501"] or  frontend URL 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#  Supported model types 
ModelType = Literal["layout", "read", "general_document", "invoice", "receipt", "custom"]

PREBUILT_MODEL_MAP: dict[str, str] = {
    "layout":           "prebuilt-layout",
    "read":             "prebuilt-read",
    "general_document": "prebuilt-document",
    "invoice":          "prebuilt-invoice",
    "receipt":          "prebuilt-receipt",
}

SUPPORTED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/tiff",
    "image/bmp",
}


#  Pydantic response schemas

class FieldValue(BaseModel):
    value: Optional[str]   = None
    confidence: Optional[float] = None
    content: Optional[str] = None


class AnalyzeResponse(BaseModel):
    filename:   str
    model_used: str
    analyzed_at: str
    raw:    dict                        # full Azure SDK output as dict
    fields: dict[str, FieldValue]       #  extracted fields


class HealthResponse(BaseModel):
    status: str
    azure_configured: bool
    timestamp: str


# Helpers 
# These internal functions handle model resolution, client creation, and result parsing.


def _resolve_model_id(model_type: ModelType, custom_model_id: str = "") -> str:
    """Map a user-facing model_type string to the Azure model ID."""
    if model_type == "custom":
        if not custom_model_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="custom_model_id is required when model_type is 'custom'.",
            )
        return custom_model_id
    return PREBUILT_MODEL_MAP[model_type]


def _build_client(endpoint: str, key: str) -> DocumentIntelligenceClient:
    """Create and return an authenticated Azure DI client."""
    if not endpoint or not key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Azure credentials are missing. "
                "Pass 'endpoint' and 'key' in the request, "
                "or set AZURE_DI_ENDPOINT / AZURE_DI_KEY in your .env file."
            ),
        )
    return DocumentIntelligenceClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(key),
    )


def _extract_fields(result) -> dict[str, dict]:
    """
    Walk the Azure result and build a clean {field_name: {value, confidence}} dict.
    Works for prebuilt models that return result.documents[].fields
    and layout/read models that return only pages (no fields).
    """
    fields: dict[str, dict] = {}

    documents = getattr(result, "documents", None) or []
    for doc in documents:
        for field_name, field_val in (doc.fields or {}).items():
            if field_val is None:
                fields[field_name] = {"value": None, "confidence": None, "content": None}
                continue

            # Try the most common value attributes in priority order
            value = None
            for attr in (
                "value_string", "value_number", "value_date",
                "value_time", "value_integer", "value_selection_mark", "content",
            ):
                raw = getattr(field_val, attr, None)
                if raw is not None:
                    value = str(raw)
                    break

            fields[field_name] = {
                "value":      value,
                "confidence": getattr(field_val, "confidence", None),
                "content":    getattr(field_val, "content", None),
            }

    return fields


def _result_to_dict(result) -> dict:
    """
    Convert the Azure AnalyzeResult object to a plain JSON-serialisable dict.
    Uses the SDK's built-in as_dict() if available, otherwise falls back to
    a manual extraction of the most important fields.
    """
    try:
        # azure-ai-documentintelligence  exposes as_dict()
        return result.as_dict()
    except AttributeError:
        pass

    # Fallback: build a representative dict manually
    out: dict = {
        "api_version":  getattr(result, "api_version",  None),
        "model_id":     getattr(result, "model_id",     None),
        "content":      getattr(result, "content",      None),
        "pages":        [],
        "tables":       [],
        "key_value_pairs": [],
        "documents":    [],
    }

    # Pages
    for page in (getattr(result, "pages", None) or []):
        out["pages"].append({
            "page_number": page.page_number,
            "width":       getattr(page, "width",  None),
            "height":      getattr(page, "height", None),
            "lines": [
                {"content": ln.content}
                for ln in (getattr(page, "lines", None) or [])
            ],
        })

    # Tables
    for tbl in (getattr(result, "tables", None) or []):
        cells: list[dict] = []
        for cell in (getattr(tbl, "cells", None) or []):
            cells.append({
                "row_index":    cell.row_index,
                "column_index": cell.column_index,
                "content":      cell.content,
                "kind":         getattr(cell, "kind", None),
            })
        out["tables"].append({
            "row_count":    tbl.row_count,
            "column_count": tbl.column_count,
            "cells":        cells,
        })

    # Key-value pairs
    for kv in (getattr(result, "key_value_pairs", None) or []):
        key_content = (kv.key.content   if kv.key   else None)
        val_content = (kv.value.content if kv.value else None)
        out["key_value_pairs"].append({
            "key":        key_content,
            "value":      val_content,
            "confidence": getattr(kv, "confidence", None),
        })

    # Documents (structured field extraction)
    for doc in (getattr(result, "documents", None) or []):
        doc_dict: dict = {
            "doc_type":   getattr(doc, "doc_type",   None),
            "confidence": getattr(doc, "confidence", None),
            "fields":     {},
        }
        for fname, fval in (doc.fields or {}).items():
            doc_dict["fields"][fname] = {
                "content":    getattr(fval, "content",    None),
                "confidence": getattr(fval, "confidence", None),
            }
        out["documents"].append(doc_dict)

    return out


#  Endpoints 
# 1) Health check
# 2) Analyze document
# 3) List available models
# Each endpoint handler validates input, interacts with Azure DI as needed, and returns a structured response.

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    Health check endpoint.
    Returns service status and whether Azure credentials are present in the environment.
    """
    env_endpoint = os.getenv("AZURE_DI_ENDPOINT", "")
    env_key      = os.getenv("AZURE_DI_KEY", "")
    return HealthResponse(
        status="ok",
        azure_configured=bool(env_endpoint and env_key),
        timestamp=datetime.utcnow().isoformat(timespec="seconds") + "Z",
    )


@app.post("/analyze", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_document(
    file: UploadFile = File(..., description="PDF or image file to analyse"),
    model_type: ModelType = Form(
        ...,
        description="One of: layout | read | general_document | invoice | receipt | custom",
    ),
    endpoint: str = Form(
        default="",
        description="Azure DI endpoint (overrides AZURE_DI_ENDPOINT env var)",
    ),
    key: str = Form(
        default="",
        description="Azure DI key (overrides AZURE_DI_KEY env var)",
    ),
    custom_model_id: str = Form(
        default="",
        description="Required only when model_type='custom'",
    ),
):
    """
    Analyse a document with the selected Azure DI model.

    - **file**: PDF, PNG, JPG, TIFF, or BMP
    - **model_type**: prebuilt shorthand or 'custom'
    - **endpoint** / **key**: Azure credentials (fall back to .env if omitted)
    - **custom_model_id**: your trained model ID (required for custom only)

    Returns the full raw Azure response plus a clean `fields` dict.
    """
    # 1) Resolve credentials — form params override .env
    resolved_endpoint = endpoint or os.getenv("AZURE_DI_ENDPOINT", "")
    resolved_key      = key      or os.getenv("AZURE_DI_KEY", "")

    # 2) Validate file type
    if file.content_type not in SUPPORTED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file type '{file.content_type}'. "
                f"Supported: {sorted(SUPPORTED_CONTENT_TYPES)}"
            ),
        )

    # 3) Read file bytes
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # 4) Resolve model ID
    model_id = _resolve_model_id(model_type, custom_model_id)

    # 5) Build Azure client
    client = _build_client(resolved_endpoint, resolved_key)

    # 6) Call Azure Document Intelligence
    logger.info("Analysing '%s' with model '%s'", file.filename, model_id)
    try:
        poller = client.begin_analyze_document(
            model_id=model_id,
            content_type=file.content_type,
            body=file_bytes )
        result = poller.result()
    except HttpResponseError as exc:
        logger.error("Azure DI error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Azure Document Intelligence error: {exc.message or str(exc)}",
        )
    except Exception as exc:
        logger.exception("Unexpected error during analysis")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(exc)}",
        )

    # 7) Build response
    raw_dict    = _result_to_dict(result)
    clean_fields = _extract_fields(result)

    return AnalyzeResponse(
        filename=file.filename or "unknown",
        model_used=model_id,
        analyzed_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
        raw=raw_dict,
        fields={k: FieldValue(**v) for k, v in clean_fields.items()},
    )


@app.get("/models", tags=["System"])
async def list_models():
    """
    List all available prebuilt model types and their Azure model IDs.
    Custom models are identified by the model_id you supply at analysis time.
    """
    return {
        "prebuilt": PREBUILT_MODEL_MAP,
        "custom": "Pass model_type='custom' and provide your custom_model_id.",
    }


# Dev entry-point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("back_app:app", host="0.0.0.0", port=8000, reload=True)
