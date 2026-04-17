import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class AzureConfig:
    endpoint: str = field(default_factory=lambda: os.getenv("AZURE_DI_ENDPOINT", ""))
    key: str      = field(default_factory=lambda: os.getenv("AZURE_DI_KEY", ""))

    # Blob Storage (custom model)
    conn_string:  str = field(default_factory=lambda: os.getenv("CONNECTION_STRING", ""))
    container: str = field(default_factory=lambda: os.getenv("BLOB_CONTAINER", ""))
    blob_sas_url:   str = field(default_factory=lambda: os.getenv("AZURE_BLOB_SAS_URL", ""))
    blob_sas_token: str = field(default_factory=lambda: os.getenv("AZURE_BLOB_SAS_TOKEN", ""))
    account_url:   str = field(default_factory=lambda: os.getenv("ACCOUNT_URL", ""))
    sas_token:     str = field(default_factory=lambda: os.getenv("SAS_TOKEN", ""))
    



    def is_configured(self) -> bool:
        return bool(self.endpoint and self.key)

    def is_blob_configured(self) -> bool:
        return bool(self.conn_string and self.container)


# Singleton – import and use directly
azure = AzureConfig()

# Convenience aliases kept for backward compat with existing prebuilt code
endpoint = azure.endpoint
ENDPOINT = azure.endpoint
KEY      = azure.key
key      = azure.key

# Aliases kept for backward compat with existing custom-model code
di_endpoint                         = azure.endpoint
di_key                              = azure.key
blob_sas_url                        = azure.blob_sas_url
blob_sas_token                      = azure.blob_sas_token
conn_string                         = azure.conn_string
container                           = azure.container
account_url                         = azure.account_url
sas_token                           = azure.sas_token




# Prebuilt model map


@dataclass
class AppConfig:
    ENV: str = os.getenv("APP_ENV", "development")
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "outputs")

    SUPPORTED_EXTENSIONS: tuple = (".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp")
    MAX_FILE_SIZE_MB: int        = 50

    OUTPUT_DIR_JSON:   str = "outputs/json"
    OUTPUT_DIR_TABLES: str = "outputs/tables"


app_config = AppConfig()



# Custom model — session state defaults

SESSION_DEFAULTS: dict = {
    "step":            1,
    "uploaded_files":  {},
    "fields":          [],
    "field_types":     {},
    "field_formats":   {},
    "annotations":     {},
    "model_id":        "",
    "training_done":   False,
    "anno_pdf":        None,
    "anno_page":       0,
    "anno_field_idx":  0,
    "canvas_key":      0,
    "pending_box":     None,
}



FIELD_COLORS: list[str] = [
    "#E53935","#1E88E5","#43A047","#FB8C00","#8E24AA",
    "#00ACC1","#F4511E","#6D4C41","#D81B60","#546E7A","#FFB300","#00897B",
]
