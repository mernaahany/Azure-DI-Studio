"""
models/registry.py — Single source of truth for all model definitions.

"""

from dataclasses import dataclass


@dataclass
class ModelDefinition:
    """All info needed to identify and use a model."""
    model_id: str           # Azure model ID sent to the API
    display_name: str       # Shown in the UI dropdown
    description: str        # Tooltip / help text
    has_enhancer: bool = False  # True for Invoice and Receipt (extra field extraction)


# ── All models defined once, in one place ─────────────────────────────────────
MODELS: dict[str, ModelDefinition] = {
    "OCR (Read)": ModelDefinition(
        model_id="prebuilt-read",
        display_name="OCR (Read)",
        description="Fast text extraction — extracts all raw text, lines, and words.",
    ),
    "Layout Analyzer": ModelDefinition(
        model_id="prebuilt-layout",
        display_name="Layout Analyzer",
        description="Extracts text, tables, and document structure. No field extraction.",
    ),
    "General Document": ModelDefinition(
        model_id="prebuilt-document",
        display_name="General Document",
        description="Extracts key-value pairs and text from any document type.",
    ),
    "Invoice": ModelDefinition(
        model_id="prebuilt-invoice",
        display_name="Invoice",
        description="Extracts vendor, customer, line items, totals, and dates from invoices.",
        has_enhancer=True,
    ),
    "Receipt": ModelDefinition(
        model_id="prebuilt-receipt",
        display_name="Receipt",
        description="Extracts merchant, items, subtotals, tax, and total from receipts.",
        has_enhancer=True,
    ),
}


# ── Public helpers ─────────────────────────────────────────────────────────────

def get_model(display_name: str) -> ModelDefinition:
    """Return ModelDefinition by display name. Raises ValueError if not found."""
    if display_name not in MODELS:
        raise ValueError(
            f"Model '{display_name}' not found. "
            f"Available: {list(MODELS.keys())}"
        )
    return MODELS[display_name]


def get_display_names() -> list[str]:
    """Return the list of display names for the UI dropdown."""
    return list(MODELS.keys())


def get_description(display_name: str) -> str:
    """Return description for a given display name (safe — returns '' if not found)."""
    model = MODELS.get(display_name)
    return model.description if model else ""
