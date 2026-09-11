# Document Intelligence Platform

Intelligent document extraction, financial validation, and REST API platform for
invoices and financial statements (AI Engineer Internship case study).

## Status

Project skeleton — layered architecture is scaffolded, core service stubs are in
place with `TODO`s marking where OCR/LLM integration and remaining business logic
need to be implemented.

## Repository structure

```
document-intelligence-platform/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── api/routes.py           # HTTP routes, orchestrates the service layer
│   │   ├── core/                   # config, logging, exception handling
│   │   ├── models/                 # Pydantic response schemas + SQLAlchemy models
│   │   ├── services/                # file_validation, ocr_service, extraction_service,
│   │   │                            #   financial_validation, persistence_service
│   │   └── db/                     # engine/session setup + CRUD
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/                       # HTML/CSS/JS client (upload, dashboard, detail view)
├── docs/                           # architecture diagram, etc.
├── sample_outputs/                 # sample processed-document JSON for submission
└── README.md
```

## Local setup

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in LLM_API_KEY / OCR_API_KEY as needed
uvicorn app.main:app --reload
```

Open `frontend/index.html` in a browser (or serve it statically) and set
`API_BASE_URL` in `frontend/js/app.js` to the backend's local/deployed URL.

## Next steps

- Implement `services/file_validation._get_page_count` (PyMuPDF).
- Implement `services/ocr_service.extract_text` (native text + Tesseract/hosted OCR fallback).
- Implement `services/extraction_service.extract_fields` (LLM structured-output call).
- Extend `services/financial_validation.run_validations` for the remaining document types.
- Build out `frontend/js/app.js` dashboard/detail rendering.
- Fill in remaining README sections required by the case study (deployment URLs,
  tech-stack rationale, API examples, known limitations, etc.) once deployed.
