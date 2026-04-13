"""
invoice_model.py — Invoice document analysis model
"""

from models.base_model import BaseModel, ModelConfig, AnalysisResult
from services.document_service import analyze_document
from parsers.json_parser import build_json_output
import time


class InvoiceModel(BaseModel):
    """
    Invoice Analysis model.
    Uses 'prebuilt-invoice' Azure model for specialized invoice extraction.
    """
    
    def __init__(self):
        config = ModelConfig(
            model_id="prebuilt-invoice",
            display_name="Invoice",
            description="Extract structured data from invoices: amounts, dates, vendor, items",
            category="prebuilt",
            version="1.0",
        )
        super().__init__(config)
    
    def analyze(self, file_bytes: bytes, filename: str) -> AnalysisResult:
        """
        Analyze invoice document.
        
        Args:
            file_bytes: Raw file bytes
            filename: Original filename
            
        Returns:
            AnalysisResult with invoice data
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
            
            # Extract invoice-specific fields
            parsed = self._enhance_with_invoice_fields(parsed, raw_result)
            
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

    
    def _enhance_with_invoice_fields(self, parsed: dict, raw_result: dict) -> dict:
        """
        Extract invoice-specific fields and add to parsed output.
        
        Args:
            parsed: Standard parsed output
            raw_result: Raw Azure result with invoice fields
            
        Returns:
            Enhanced parsed output with invoice-specific data
        """
        parsed["invoice_details"] = {}
        
        # Extract documents with invoice fields
        for doc in raw_result.get("documents", []):
            fields = doc.get("fields", {})
            parsed["invoice_details"] = {
                "invoice_id": fields.get("InvoiceId", {}).get("value"),
                "invoice_date": fields.get("InvoiceDate", {}).get("value"),
                "due_date": fields.get("DueDate", {}).get("value"),
                "vendor_name": fields.get("VendorName", {}).get("value"),
                "vendor_address": fields.get("VendorAddress", {}).get("value"),
                "customer_name": fields.get("CustomerName", {}).get("value"),
                "customer_address": fields.get("CustomerAddress", {}).get("value"),
                "subtotal": fields.get("SubTotal", {}).get("value"),
                "tax": fields.get("TotalTax", {}).get("value"),
                "total": fields.get("InvoiceTotal", {}).get("value"),
                "currency": fields.get("InvoiceCurrencyCode", {}).get("value"),
            }
        
        return parsed
