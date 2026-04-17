"""
services/analyzer.py — The single analysis pipeline.

Replaces: inference_controller.py + base_model.py (analyze method)

Flow:
    validate → resolve model → call Azure → parse → enhance → save → return
"""

import time
from dataclasses import dataclass, field
from datetime import datetime

from utils.config import AppConfig
from prebuilt.registry import get_model
from prebuilt.enhancers import enhance
from prebuilt.azure_client import analyze_document
from prebuilt.json_parser import build_json_output
from prebuilt.file_handler import validate_file, save_json_output


@dataclass
class AnalysisResult:
    """Returned by run_analysis() — everything the UI needs."""
    success: bool
    parsed: dict = field(default_factory=dict) #the parsed result from Azure, structured as a clean dict ready for display 
    saved_path: str = ""
    error: str = ""
    processing_time_ms: float = 0.0


def run_analysis(file_bytes: bytes, filename: str, display_name: str) -> AnalysisResult:
    """
    Full pipeline from raw file bytes to structured JSON output.

    Args:
        file_bytes:    Raw uploaded file bytes.
        filename:      Original filename (used for format validation & output naming).
        display_name:  Model display name chosen in the UI (e.g. "Invoice").

    Returns:
        AnalysisResult with success flag, parsed data, saved path, and timing.
    """
    start = time.time()

    # 1 — Validate file
    valid, msg = validate_file(file_bytes, filename)
    if not valid:
        return AnalysisResult(success=False, error=msg)

    # 2 — Resolve model
    try:
        model = get_model(display_name)
    except ValueError as e:
        return AnalysisResult(success=False, error=str(e))

    # 3 — Call Azure
    try:
        raw_result = analyze_document(file_bytes, model.model_id)
    except (RuntimeError, EnvironmentError) as e:
        return AnalysisResult(success=False, error=str(e))

    # 4 — Parse raw result into clean JSON structure
    parsed = build_json_output(raw_result, filename, model.display_name)

    # 5 — Enhance with model-specific fields (Invoice / Receipt only)
    if model.has_enhancer:
        parsed = enhance(parsed, raw_result, model.model_id)

    # 6 — Save to disk (non-fatal if it fails)
    saved_path = ""
    try:
        saved_path = save_json_output(parsed, filename)
    except Exception:
        pass  # saving is best-effort; analysis result is still returned

    ms = (time.time() - start) * 1000
    return AnalysisResult(
        success=True,
        parsed=parsed,
        saved_path=saved_path,
        processing_time_ms=ms,
    )
