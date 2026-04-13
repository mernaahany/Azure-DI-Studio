import os
from dotenv import load_dotenv

load_dotenv()


class AzureConfig:
    """Azure Document Intelligence credentials."""
    ENDPOINT: str = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    KEY: str = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

    @classmethod
    def is_configured(cls) -> bool:
        return bool(cls.ENDPOINT and cls.KEY)


class AppConfig:
    """General app settings."""
    ENV: str = os.getenv("APP_ENV", "development")
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "outputs")

    # Supported prebuilt Azure model IDs
    MODEL_MAP: dict = {
        "Layout Analyzer": "prebuilt-layout",
        "OCR (Read)": "prebuilt-read",
        "General Document": "prebuilt-document",
        "Invoice": "prebuilt-invoice",
        "Receipt": "prebuilt-receipt",
    }

    SUPPORTED_EXTENSIONS: list = [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"]
    MAX_FILE_SIZE_MB: int = 50
