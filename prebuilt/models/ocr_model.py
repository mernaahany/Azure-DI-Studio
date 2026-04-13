"""
ocr_model.py — OCR (Read) model for text recognition
"""

from models.base_model import BaseModel, ModelConfig, AnalysisResult
from services.document_service import analyze_document
from parsers.json_parser import build_json_output
import time


class OCRModel(BaseModel):
    """
    OCR (Optical Character Recognition) model.
    Uses 'prebuilt-read' Azure model for text extraction from images/PDFs.
    """
    
    def __init__(self):
        config = ModelConfig(
            model_id="prebuilt-read",
            display_name="OCR (Read)",
            description="Extract all visible text from documents and images",
            category="prebuilt",
            version="1.0",
        )
        super().__init__(config)
    
    def analyze(self, file_bytes: bytes, filename: str) -> AnalysisResult:
        """
        Analyze document using OCR model.
        
        Args:
            file_bytes: Raw file bytes
            filename: Original filename
            
        Returns:
            AnalysisResult with extracted text
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
            
            processing_time = (time.time() - start_time) * 1000  # Convert to ms
            
            return AnalysisResult(
                model_id=self.config.model_id,
                display_name=self.config.display_name,
                filename=filename,
                success=True,
                data=parsed,
                confidence=None,  # OCR doesn't have overall confidence
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

