#  Azure Document Intelligence App

One Streamlit app, two workflows:
- **Prebuilt Models** — instant analysis with 5 Azure-built models
- **Custom Model** — guided 5-step trainer for your own document type

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create .env with your Azure credentials
cp .env.example .env
# Then fill in AZURE_DI_ENDPOINT and AZURE_DI_KEY

# 3. Run
streamlit run Home.py
```

---

## Directory Structure

```
unified_app/
│
├── Home.py                        ← Landing page (workflow selector)
│
├── pages/
│   ├── 1_Prebuilt_Models.py       ← Prebuilt model analysis page
│   └── 2_Custom_Model.py          ← Custom model trainer page
│
├── steps/                         ← Custom model 5-step workflow
│   ├── step1_upload.py
│   ├── step2_fields.py
│   ├── step3_annotate.py
│   ├── step4_train.py
│   └── step5_test.py
│
├── controllers/
│   └── inference_controller.py    ← EDITED: added endpoint/key override params
│
├── models/                        ← Prebuilt model definitions (unchanged)
│   ├── base_model.py
│   ├── model_factory.py
│   ├── ocr_model.py
│   ├── layout_model.py
│   ├── general_doc_model.py
│   ├── invoice_model.py
│   └── receipt_model.py
│
├── parsers/                       ← (unchanged)
│   ├── json_parser.py
│   └── table_parser.py
│
├── services/                      ← (unchanged)
│   ├── document_service.py
│   └── model_router.py
│
├── ui/
│   ├── theme.py                   ← NEW: shared CSS + design tokens
│   ├── display.py                 ← see migration note below
│   └── layout.py                  ← see migration note below
│
├── utils/
│   ├── config.py                  ← REPLACED: merged both configs
│   ├── file_handler.py            ← (unchanged from prebuilt)
│   ├── pdf_utils.py               ← (unchanged from custom)
│   ├── azure_utils.py             ← (unchanged from custom)
│   ├── schema_builders.py         ← (unchanged from custom)
│   └── ocr_cache.py               ← (unchanged from custom)
│
├── outputs/
│   ├── json/
│   └── tables/
│
├── requirements.txt               ← REPLACED: merged dependencies
└── .env.example
```

---

## Migration Checklist

### Files to COPY unchanged from each original project

**From prebuilt project** (copy as-is):
- `models/` — all 7 files
- `parsers/json_parser.py`, `parsers/table_parser.py`
- `services/document_service.py`, `services/model_router.py`
- `utils/file_handler.py`

**From custom project** (copy as-is):
- `steps/` — all 5 step files
- `utils/pdf_utils.py`
- `utils/azure_utils.py`
- `utils/schema_builders.py`
- `utils/ocr_cache.py`

### Files to REPLACE (provided in this repo):
| File | Change |
|------|--------|
| `utils/config.py` | Merged both configs — replaces both originals |
| `controllers/inference_controller.py` | Added `endpoint_override` / `key_override` params |
| `requirements.txt` | Merged dependencies |

### Files that are NO LONGER needed (do NOT copy):
| Old file | Replaced by |
|----------|-------------|
| prebuilt `main.py` | `Home.py` + `pages/1_Prebuilt_Models.py` |
| custom `app.py` | `pages/2_Custom_Model.py` |
| prebuilt `ui/layout.py` | `ui/theme.py` (shared) + inline page layout |
| prebuilt `ui/display.py` | Inline display code in `pages/1_Prebuilt_Models.py` |

> **Note on `ui/display.py` and `ui/layout.py`:** The prebuilt display logic has been
> inlined directly into `pages/1_Prebuilt_Models.py` so the theme is fully consistent.
> You can keep the old display.py for reference but it is not imported anywhere in the
> unified app.

---

## Environment Variables (.env.example)

```env
# Azure Document Intelligence
AZURE_DI_ENDPOINT=https://<your-resource>.cognitiveservices.azure.com/
AZURE_DI_KEY=<your-key>

# Azure Blob Storage (custom model training only)
AZURE_BLOB_CONN_STR=DefaultEndpointsProtocol=https;AccountName=...
AZURE_BLOB_CONTAINER=training-docs
AZURE_BLOB_SAS_URL=https://<account>.blob.core.windows.net/<container>?<sas-token>
```

All credentials can also be entered live in the sidebar on each page —
sidebar values override `.env` values.