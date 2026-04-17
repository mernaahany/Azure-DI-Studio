"""
models/enhancers.py — Model-specific field extraction added on top of base parsed output.

"""


def enhance(parsed: dict, raw_result: dict, model_id: str) -> dict: # parser is json_parser.build_json_output's output, raw_result is azure_client.analyze_document's output
    """
    Entry point — call the correct enhancer based on model_id.
    Returns parsed unchanged if no enhancer exists for this model.
    """
    if model_id == "prebuilt-invoice":
        return _enhance_invoice(parsed, raw_result)
    if model_id == "prebuilt-receipt":
        return _enhance_receipt(parsed, raw_result)
    return parsed


# ── Invoice ────────────────────────────────────────────────────────────────────

def _enhance_invoice(parsed: dict, raw_result: dict) -> dict:
    """Add invoice_details block to parsed output."""
    parsed["invoice_details"] = {}

    for doc in raw_result.get("documents", []):
        fields = doc.get("fields", {})
        parsed["invoice_details"] = {
            "invoice_id":       _val(fields, "InvoiceId"),
            "invoice_date":     _val(fields, "InvoiceDate"),
            "due_date":         _val(fields, "DueDate"),
            "vendor_name":      _val(fields, "VendorName"),
            "vendor_address":   _val(fields, "VendorAddress"),
            "customer_name":    _val(fields, "CustomerName"),
            "customer_address": _val(fields, "CustomerAddress"),
            "subtotal":         _val(fields, "SubTotal"),
            "tax":              _val(fields, "TotalTax"),
            "total":            _val(fields, "InvoiceTotal"),
            "currency":         _val(fields, "InvoiceCurrencyCode"),
        }

    return parsed


# ── Receipt ────────────────────────────────────────────────────────────────────

def _enhance_receipt(parsed: dict, raw_result: dict) -> dict:
    """Add receipt_details block (including line items) to parsed output."""
    parsed["receipt_details"] = {}

    for doc in raw_result.get("documents", []):
        fields = doc.get("fields", {})
        parsed["receipt_details"] = {
            "merchant_name":    _val(fields, "MerchantName"),
            "merchant_phone":   _val(fields, "MerchantPhoneNumber"),
            "merchant_address": _val(fields, "MerchantAddress"),
            "transaction_date": _val(fields, "TransactionDate"),
            "transaction_time": _val(fields, "TransactionTime"),
            "subtotal":         _val(fields, "Subtotal"),
            "tax":              _val(fields, "Tax"),
            "tip":              _val(fields, "Tip"),
            "total":            _val(fields, "Total"),
            "currency":         _val(fields, "CurrencyCode"),
            "items":            _extract_items(fields),
        }

    return parsed


def _extract_items(fields: dict) -> list:
    """
    Extract receipt line items.

    Fix: azure_client._serialize_field now stores Items as a real list[dict],
    NOT a comma-joined string, so we can iterate it correctly here.
    """
    items = []
    raw_items = fields.get("Items", {}).get("value", [])

    if not isinstance(raw_items, list):
        return items  # nothing to extract if it's still a string (shouldn't happen)

    for item in raw_items:
        # Each item is a dict produced by _serialize_field for an "object" field
        if isinstance(item, dict):
            items.append({
                "name":        item.get("Description"),
                "quantity":    item.get("Quantity"),
                "price":       item.get("Price"),
                "total_price": item.get("TotalPrice"),
            })

    return items


# ── Helper ─────────────────────────────────────────────────────────────────────

def _val(fields: dict, key: str):
    """Safely get the 'value' of a field. Returns None if missing."""
    return fields.get(key, {}).get("value")
