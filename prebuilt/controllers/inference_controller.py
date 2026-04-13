"""
inference_controller.py — Orchestrates: upload → Azure → parse → output
"""
 
from prebuilt.services.document_service import analyze_document
from prebuilt.services.model_router import resolve_model_id
from prebuilt.parsers.json_parser import build_json_output
from utils.file_handler import validate_file, save_json_output
 
 
def run_inference(
    file_bytes: bytes,
    filename: str,
    model_display_name: str,
    endpoint_override: str = "",
    key_override: str = "",
) -> dict:
    """
    Full pipeline:
      1. Validate file
      2. Resolve model display name → Azure model ID
      3. Call Azure Document Intelligence
      4. Parse raw result → clean JSON
      5. Save JSON to disk
      6. Return parsed result dict
 
    Args:
        file_bytes:          Raw bytes of the uploaded document.
        filename:            Original filename (used for metadata and saving).
        model_display_name:  Display name from AppConfig.MODEL_MAP.
        endpoint_override:   Azure DI endpoint from sidebar (overrides .env).
        key_override:        Azure DI key from sidebar (overrides .env).
 
    Returns:
        {
          "success": bool,
          "parsed": dict,          ← clean structured output
          "saved_json_path": str,  ← path to saved JSON file
          "error": str | None,
        }
    """
    # Step 1 — Validate
    valid, msg = validate_file(file_bytes, filename)
    if not valid:
        return {"success": False, "parsed": {}, "saved_json_path": "", "error": msg}
 
    # Step 2 — Resolve model
    try:
        model_id = resolve_model_id(model_display_name)
    except ValueError as e:
        return {"success": False, "parsed": {}, "saved_json_path": "", "error": str(e)}
 
    # Step 3 — Call Azure  (pass sidebar creds if provided, else service reads .env)
    try:
        raw_result = analyze_document(file_bytes,model_id)
    except (RuntimeError, EnvironmentError) as e:
        return {"success": False, "parsed": {}, "saved_json_path": "", "error": str(e)}
 
    # Step 4 — Parse
    parsed = build_json_output(raw_result, filename, model_display_name)
 
    # Step 5 — Save JSON
    try:
        saved_path = save_json_output(parsed, filename)
    except Exception:
        saved_path = ""  # non-fatal, still return result
 
    return {
        "success": True,
        "parsed": parsed,
        "saved_json_path": saved_path,
        "error": None,
    }
 