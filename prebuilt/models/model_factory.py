"""
model_factory.py — Factory for creating model instances on-demand.
Note: Model configuration sourced from utils/config.py to maintain single source of truth.
"""

from typing import Dict, Optional
from models.base_model import BaseModel, ModelConfig
from models.ocr_model import OCRModel
from models.layout_model import LayoutModel
from models.general_doc_model import GeneralDocModel
from models.invoice_model import InvoiceModel
from models.receipt_model import ReceiptModel
from utils.config import AppConfig


class ModelFactory:
    """Factory for creating and managing document analysis models.
    Uses AppConfig.MODEL_MAP as the single source of truth for model mappings.
    """
    
    # Registry of model ID → class mapping (single source of truth: config.py)
    PREBUILT_MODELS: Dict[str, type] = {
        "prebuilt-read": OCRModel,
        "prebuilt-layout": LayoutModel,
        "prebuilt-document": GeneralDocModel,
        "prebuilt-invoice": InvoiceModel,
        "prebuilt-receipt": ReceiptModel,
    }
    
    @staticmethod
    def create_model(model_id: str) -> Optional[BaseModel]:
        """
        Create a model instance by ID.
        
        Args:
            model_id: Azure model identifier (e.g., 'prebuilt-invoice')
            
        Returns:
            BaseModel instance or None if not found
        """
        model_class = ModelFactory.PREBUILT_MODELS.get(model_id)
        if model_class:
            try:
                return model_class()
            except Exception as e:
                print(f"Warning: Failed to create model {model_id}: {str(e)}")
                return None
        return None
    
    @staticmethod
    def get_model_config(model_id: str) -> Optional[ModelConfig]:
        """
        Get configuration for a model without full instantiation.
        
        Args:
            model_id: Model identifier
            
        Returns:
            ModelConfig or None if not found
        """
        model = ModelFactory.create_model(model_id)
        if model:
            return model.get_config()
        return None
