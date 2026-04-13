"""
file_handler.py — File validation, saving, and I/O helpers
"""

import os
import json
from pathlib import Path
from datetime import datetime
from utils.config import AppConfig


def validate_file(file_bytes: bytes, filename: str) -> tuple[bool, str]:
    """Validate uploaded file type and size."""
    ext = Path(filename).suffix.lower()
    if ext not in AppConfig.SUPPORTED_EXTENSIONS:
        return False, f"Unsupported file type '{ext}'. Allowed: {AppConfig.SUPPORTED_EXTENSIONS}"

    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > AppConfig.MAX_FILE_SIZE_MB:
        return False, f"File too large ({size_mb:.1f} MB). Max: {AppConfig.MAX_FILE_SIZE_MB} MB"

    return True, "OK"


def save_json_output(data: dict, filename: str) -> str:
    """Save result as JSON file, return path."""
    os.makedirs(f"{AppConfig.OUTPUT_DIR}/json", exist_ok=True)
    stem = Path(filename).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = f"{AppConfig.OUTPUT_DIR}/json/{stem}_{timestamp}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return out_path


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
