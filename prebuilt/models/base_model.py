"""
base_model.py — Abstract base class for all document analysis models
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ModelConfig:
    """Configuration for a model."""
    model_id: str
    display_name: str
    description: str
    category: str  # 'prebuilt'
    version: str = "1.0"
    supported_formats: List[str] = None
    
    def __post_init__(self):
        if self.supported_formats is None:
            self.supported_formats = [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"]


@dataclass
class AnalysisResult:
    """Standard result from model analysis."""
    model_id: str
    display_name: str
    filename: str
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None
    confidence: Optional[float] = None
    processed_at: str = None
    processing_time_ms: float = 0.0
    
    def __post_init__(self):
        if self.processed_at is None:
            self.processed_at = datetime.now().isoformat()


class BaseModel(ABC):
    """
    Abstract base class for all document analysis models.
    
    All models (prebuilt) must inherit from this and implement:
    - analyze(file_bytes, filename)
    - get_config()
    
    Shared validation logic is provided by validate_input() (non-abstract).
    """
    
    def __init__(self, config: ModelConfig):
        """Initialize model with configuration."""
        self.config = config
    
    @abstractmethod
    def analyze(self, file_bytes: bytes, filename: str) -> AnalysisResult:
        """
        Analyze a document and return structured results.
        
        Args:
            file_bytes: Raw file bytes
            filename: Original filename for context
            
        Returns:
            AnalysisResult with parsed data
        """
        pass
    
    def validate_input(self, file_bytes: bytes, filename: str) -> tuple[bool, str]:
        """
        Validate if the input is suitable for this model.
        Shared implementation for all models - checks size, format, and emptiness.
        
        Args:
            file_bytes: Raw file bytes
            filename: Original filename
            
        Returns:
            (is_valid, error_message)
        """
        # Check empty
        valid, msg = self._validate_file_not_empty(file_bytes)
        if not valid:
            return valid, msg
        
        # Check extension
        valid, msg = self._validate_file_extension(filename)
        if not valid:
            return valid, msg
        
        # Check size
        valid, msg = self._validate_file_size(file_bytes)
        if not valid:
            return valid, msg
        
        return True, ""
    
    def get_config(self) -> ModelConfig:
        """Return model configuration."""
        return self.config
    
    def get_metadata(self) -> Dict[str, Any]:
        """Return model metadata as dict."""
        return {
            "model_id": self.config.model_id,
            "display_name": self.config.display_name,
            "description": self.config.description,
            "category": self.config.category,
            "version": self.config.version,
            "supported_formats": self.config.supported_formats,
        }
    
    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename."""
        import os
        _, ext = os.path.splitext(filename)
        return ext.lower()
    
    def _validate_file_extension(self, filename: str) -> tuple[bool, str]:
        """Check if file extension is supported."""
        ext = self._get_file_extension(filename)
        if ext not in self.config.supported_formats:
            msg = (
                f"Unsupported file format {ext}. "
                f"Supported: {', '.join(self.config.supported_formats)}"
            )
            return False, msg
        return True, ""
    
    def _validate_file_size(
        self, file_bytes: bytes, max_size_mb: int = 50
    ) -> tuple[bool, str]:
        """Check if file size is within limits."""
        size_mb = len(file_bytes) / (1024 * 1024)
        if size_mb > max_size_mb:
            return False, f"File size {size_mb:.2f} MB exceeds {max_size_mb} MB limit"
        return True, ""
    
    def _validate_file_not_empty(self, file_bytes: bytes) -> tuple[bool, str]:
        """Check if file is not empty."""
        if not file_bytes or len(file_bytes) == 0:
            return False, "File is empty"
        return True, ""
