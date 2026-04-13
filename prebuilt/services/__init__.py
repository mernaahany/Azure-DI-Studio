"""
services/__init__.py — Services package
"""

from prebuilt.services.document_service import analyze_document, get_client
from prebuilt.services.model_router import resolve_model_id

__all__ = [
    "analyze_document",
    "get_client",
    "resolve_model_id",
]
