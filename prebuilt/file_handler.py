"""
utils/file_handler.py — File validation and saving helpers.

Unchanged from original — the logic here was already correct.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from utils.config import AppConfig


def validate_file(file_bytes: bytes, filename: str) -> tuple[bool, str]:
    """Validate uploaded file: checks extension and size."""
    if not file_bytes:
        return False, "File is empty."

    ext = Path(filename).suffix.lower()
    if ext not in AppConfig.SUPPORTED_EXTENSIONS:
        return False, (
            f"Unsupported file type '{ext}'. "
            f"Allowed: {', '.join(AppConfig.SUPPORTED_EXTENSIONS)}"
        )

    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > AppConfig.MAX_FILE_SIZE_MB:
        return False, (
            f"File too large ({size_mb:.1f} MB). "
            f"Max allowed: {AppConfig.MAX_FILE_SIZE_MB} MB."
        )

    return True, "OK"


def save_json_output(data: dict, filename: str) -> str:
    """Save result dict as a JSON file. Returns the saved file path."""
    out_dir = os.path.join(AppConfig.OUTPUT_DIR, "json")
    os.makedirs(out_dir, exist_ok=True)

    stem      = Path(filename).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path  = os.path.join(out_dir, f"{stem}_{timestamp}.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return out_path


def load_json(path: str) -> dict:
    """Load a JSON file from disk."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
