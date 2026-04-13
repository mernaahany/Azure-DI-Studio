# Azure DI Studio

A detailed documentation of the `azure_di_studio` project: a Streamlit-based demo and custom training workflow for Azure Document Intelligence, plus an optional FastAPI backend.

## Overview

This folder contains a complete demo app for Azure Document Intelligence with two main workflows:

- **Prebuilt Models** — upload documents and analyse them with Azure's pretrained DI models.
- **Custom Model Trainer** — label documents in a guided 5-step workflow, upload assets to Azure Blob Storage, train a custom Azure DI model, then test it.

Additionally, the repository includes a FastAPI backend in `back_app.py` for programmatic document analysis.

## What this folder contains

- `Home_app.py` — main Streamlit homepage and workflow selector.
- `pages/1_Prebuilt_Models.py` — prebuilt model analysis UI.
- `pages/2_Custom_Model.py` — custom model training UI and workflow.
- `back_app.py` — FastAPI backend for `/analyze` and `/health`.
- `custom/steps/` — five guided training steps for uploading, labelling, annotating, training, and testing.
- `prebuilt/` — shared prebuilt model controllers, logic, parsers, services, and UI helpers.
- `utils/` — shared helpers, configuration, PDF utilities, schema builders, OCR caching, and Azure helpers.
- `outputs/` — generated JSON and table outputs for prebuilt model analysis.
- `.env.example` — environment variable template.
- `requirements.txt` — Python dependencies.

`utils/config.py` contains environment loading via `python-dotenv`, Azure configuration dataclass, app settings, supported file types, and session defaults for custom training.

`utils/pdf_utils.py` handles PDF and image rendering, page extraction, bounding box coordinate conversion, and image thumbnails.

`utils/ocr_cache.py` caches Azure OCR results locally so repeated annotation sessions do not rerun OCR unnecessarily.

`utils/schema_builders.py` constructs the `labels.json` and `fields.json` payloads required by Azure custom model training.

`utils/azure_utils.py` contains helper functions for uploading files to Azure Blob Storage and generating OCR sidecars.

## Detailed Workflow

### Streamlit app (`Home_app.py`)

The Streamlit app starts with a landing page that lets you choose between:

- **Prebuilt Models** — analyze documents immediately.
- **Custom Model** — go through a guided custom model creation workflow.

The landing page uses `prebuilt.ui.theme` for consistent styling.

---

### Prebuilt Models page (`pages/1_Prebuilt_Models.py`)

This page provides:

- Azure DI endpoint and key entry in the sidebar.
- Model selection from:
  - `OCR (Read)`
  - `Layout Analysis`
  - `General Document`
  - `Invoice`
  - `Receipt`
- Supported formats: `.pdf`, `.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp`.
- File upload and document analysis.
- Full JSON output display.
- Structured tabs for:
  - extracted tables
  - key-value pairs
  - extracted fields
  - raw text
- Excel export for tables.
- Saves parsed output to `outputs/json` and rendered tables under `outputs/tables` when configured.
- Status messages for successful inference and saved result path.

The analysis flow is implemented by `prebuilt.controllers.inference_controller.run_inference`, which calls Azure DI, parses Azure SDK responses, and normalises field values and table payloads for UI rendering.

This page also uses `prebuilt.ui.theme` helper functions such as `render_header`, `render_summary_metrics`, `render_metadata`, `render_json_view`, `render_tables_view`, and `render_extracted_fields_view`.

---

### Custom Model Trainer page (`pages/2_Custom_Model.py`)

This page is a 5-step guided workflow:

1. **Upload Documents** (`custom/steps/step1_upload.py`)
   - Upload multiple PDF or image files.
   - Files are previewed using thumbnails.
   - Requires at least 5 documents before continuing.

2. **Define Fields** (`custom/steps/step2_fields.py`)
   - Specify field names to extract.
   - Choose field types and formats.
   - Quick-add presets are available for invoice-style fields.

3. **Annotate Documents** (`custom/steps/step3_annotate.py`)
   - Draw bounding boxes on documents to label fields using an interactive HTML canvas.
   - Supports two extraction methods:
     - **PyMuPDF** — instant PDF text extraction from the native text layer in vector PDFs.
     - **Azure OCR** — prebuilt-read OCR for scanned documents and images.
   - Uses a hidden Streamlit bridge input to pass drawn box coordinates from browser JavaScript back into Python.
   - Auto-extracts text from each box and stores annotations in `st.session_state`.
   - Manual override is available for extracted text.
   - Live preview of generated `labels.json` and `fields.json`.
   - Tracks annotation coverage per document and prevents training until every document has at least one labelled field.

4. **Train Custom Model** (`custom/steps/step4_train.py`)
   - Upload documents and annotation sidecars to Blob storage.
   - Generate and upload `labels.json` per document and shared `fields.json` for field schema.
   - Run OCR sidecars (`.ocr.json`) when required, then upload them alongside PDFs.
   - Submit a `BuildDocumentModelRequest` to Azure DI using `AzureBlobContentSource` and `build_mode='template'`.
   - Displays progress status, training completion, and model readiness.
   - Requires Azure DI credentials plus a valid Blob SAS URL or storage connection string.

5. **Test Model** (`custom/steps/step5_test.py`)
   - Upload PDF documents for inference.
   - Specify the custom model ID trained in Step 4.
   - Set a confidence threshold for display.
   - View extracted fields, confidence bars, and annotated page images.
   - Download annotated PNG/PDF files and JSON/CSV results.
   - Compares actual model output against the field schema defined during training.

The custom workflow uses `st.session_state` to preserve step state, uploaded files, annotations, model IDs, and test results across reruns.

---

### FastAPI backend (`back_app.py`)

This optional backend exposes an API for document analysis.

- `POST /analyze` — accepts file upload, model type, endpoint, and key.
- `GET /health` — returns service health and Azure configuration status.

The backend is useful if you want to separate the Streamlit UI from API-driven workflows.

#### Run the backend

```bash
uvicorn back_app:app --host 0.0.0.0 --port 8000 --reload
```

Open `http://localhost:8000/docs` for Swagger UI.

The backend is implemented with FastAPI and uses `azure.ai.documentintelligence.DocumentIntelligenceClient` for inference. It supports both prebuilt model types and custom model IDs via the `model_type` and `custom_model_id` parameters.

---

## Environment Configuration

Copy `.env.example` to `.env` and populate the values:

```env
AZURE_DI_ENDPOINT=https://<your-resource>.cognitiveservices.azure.com/
AZURE_DI_KEY=<your-key>

# Azure Blob Storage (custom model training only)
CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net
CONTAINER=<your-container-name>
AZURE_BLOB_SAS_URL=https://<account>.blob.core.windows.net/<container>?<sas-token>
AZURE_BLOB_SAS_TOKEN=<sas-token>
ACCOUNT_URL=https://<account>.blob.core.windows.net
SAS_TOKEN=<sas-token>
```

### Notes on environment variables

- `AZURE_DI_ENDPOINT` and `AZURE_DI_KEY` are required for all Azure Document Intelligence operations.
- Blob storage settings are used by the custom trainer to upload PDFs, OCR results, and training label files.
- The app reads environment variables through `utils/config.py`.

---

## Directory Structure

```text
azure_di_studio/
├── Home_app.py                    # Streamlit landing page and workflow selector
├── back_app.py                    # FastAPI backend API
├── .env.example                   # Example environment variables
├── .gitignore                     # Project ignores
├── pages/
│   ├── 1_Prebuilt_Models.py       # Prebuilt model analysis UI
│   └── 2_Custom_Model.py          # Custom model training workflow UI
├── custom/
│   ├── steps/                     # Custom training steps
│   │   ├── step1_upload.py
│   │   ├── step2_fields.py
│   │   ├── step3_annotate.py
│   │   ├── step4_train.py
│   │   └── step5_test.py
│   └── utils/                     # Custom workflow helpers (if present)
├── prebuilt/
│   ├── controllers/               # Prebuilt inference controller
│   ├── models/                    # Model wrappers and definitions
│   ├── parsers/                   # Parsers for JSON and tables
│   ├── services/                  # Document service and routing logic
│   ├── ui/                        # Theme and shared UI helpers
│   └── utils/                     # Prebuilt-only utilities
├── outputs/                       # Generated outputs and export files
├── requirements.txt              # Python dependencies
├── utils/                         # Shared helpers and config
└── README.md                      # This documentation file
```

## Dependencies

Install required packages with:

```bash
pip install -r requirements.txt
```

The app depends on:

- `streamlit`
- `azure-ai-documentintelligence`
- `azure-ai-formrecognizer`
- `azure-storage-blob`
- `azure-core`
- `python-dotenv`
- `fastapi`
- `uvicorn`
- `pandas`
- `openpyxl`
- `PyMuPDF`
- `Pillow`
- `requests`
- `plotly`

---

## Usage Tips

- Use the sidebar credentials in both pages to enter Azure DI settings without editing `.env`.
- For the custom trainer, prefer native PDFs when using PyMuPDF, and use Azure OCR for scanned/image-based documents.
- Keep at least one annotation per uploaded document before training.
- Use the custom test page to verify model output and download annotated results.
- The `outputs/` folder stores exported JSON and Excel files generated by the prebuilt workflow.

## Troubleshooting

- If Streamlit cannot connect to Azure, verify the endpoint and key values.
- If training fails, check that `AZURE_BLOB_SAS_URL` points to a valid container with upload permissions.
- If custom test analysis returns no fields, confirm the `model_id` matches the one shown after training.

---

## Recommended Next Steps

1. Fill `.env` with Azure DI and Blob storage values.
2. Start the Streamlit app:

```bash
streamlit run Home_app.py
```

3. Try the Prebuilt Models workflow first.
4. Then use the Custom Model workflow and follow the 5-step guided training flow.
5. Optionally run `back_app.py` for API access.

---

## Contribution Notes

If you extend this app, keep the following patterns in mind:

- `Home_app.py` remains the main entrypoint.
- `pages/1_Prebuilt_Models.py` is the prebuilt inference page.
- `pages/2_Custom_Model.py` is the custom training page.
- `custom/steps/` contains the training stage implementations.
- `utils/config.py` centralizes environment and session defaults.
- `prebuilt/ui/theme.py` contains shared UI styling and rendering helpers.
