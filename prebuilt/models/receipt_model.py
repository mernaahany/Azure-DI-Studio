"""
receipt_model.py — Receipt document analysis model
"""

from models.base_model import BaseModel, ModelConfig, AnalysisResult
from services.document_service import analyze_document
from parsers.json_parser import build_json_output
import time


class ReceiptModel(BaseModel):
    """
    Receipt Analysis model.
    Uses 'prebuilt-receipt' Azure model for specialized receipt extraction.
    """
    
    def __init__(self):
        config = ModelConfig(
            model_id="prebuilt-receipt",
            display_name="Receipt",
            description="Extract data from receipts: items, amounts, dates, merchant",
            category="prebuilt",
            version="1.0",
        )
        super().__init__(config)
    
    def analyze(self, file_bytes: bytes, filename: str) -> AnalysisResult:
        """
        Analyze receipt document.
        
        Args:
            file_bytes: Raw file bytes
            filename: Original filename
            
        Returns:
            AnalysisResult with receipt data
        """
        start_time = time.time()
        
        # Validate input
        is_valid, error_msg = self.validate_input(file_bytes, filename)
        if not is_valid:
            return AnalysisResult(
                model_id=self.config.model_id,
                display_name=self.config.display_name,
                filename=filename,
                success=False,
                data={},
                error=error_msg,
            )
        
        try:
            # Call Azure service
            raw_result = analyze_document(file_bytes, self.config.model_id)
            
            # Parse result
            parsed = build_json_output(raw_result, filename, self.config.display_name)
            
            # Extract receipt-specific fields
            parsed = self._enhance_with_receipt_fields(parsed, raw_result)
            
            processing_time = (time.time() - start_time) * 1000
            
            return AnalysisResult(
                model_id=self.config.model_id,
                display_name=self.config.display_name,
                filename=filename,
                success=True,
                data=parsed,
                processing_time_ms=processing_time,
            )
        
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            return AnalysisResult(
                model_id=self.config.model_id,
                display_name=self.config.display_name,
                filename=filename,
                success=False,
                data={},
                error=str(e),
                processing_time_ms=processing_time,
            )

    
    def _enhance_with_receipt_fields(self, parsed: dict, raw_result: dict) -> dict:
        """
        Extract receipt-specific fields and add to parsed output.
        
        Args:
            parsed: Standard parsed output
            raw_result: Raw Azure result with receipt fields
            
        Returns:
            Enhanced parsed output with receipt-specific data
        """
        parsed["receipt_details"] = {}
        
        # Extract documents with receipt fields
        for doc in raw_result.get("documents", []):
            fields = doc.get("fields", {})
            parsed["receipt_details"] = {
                "merchant_name": fields.get("MerchantName", {}).get("value"),
                "merchant_phone": fields.get("MerchantPhoneNumber", {}).get("value"),
                "merchant_address": fields.get("MerchantAddress", {}).get("value"),
                "transaction_date": fields.get("TransactionDate", {}).get("value"),
                "transaction_time": fields.get("TransactionTime", {}).get("value"),
                "items": [],
                "subtotal": fields.get("Subtotal", {}).get("value"),
                "tax": fields.get("Tax", {}).get("value"),
                "tip": fields.get("Tip", {}).get("value"),
                "total": fields.get("Total", {}).get("value"),
                "currency": fields.get("CurrencyCode", {}).get("value"),
            }
            
            # Extract line items if available
            if "Items" in fields:
                items_field = fields.get("Items", {}).get("value", [])
                for item in items_field:
                    if isinstance(item, dict):
                        parsed["receipt_details"]["items"].append({
                            "name": item.get("Description"),
                            "quantity": item.get("Quantity"),
                            "price": item.get("Price"),
                            "total_price": item.get("TotalPrice"),
                        })
        
        return parsed
