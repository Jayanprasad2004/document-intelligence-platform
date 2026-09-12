# Document Intelligence Platform

Document extraction, financial validation, and REST API platform for invoices
and financial statements (AI Engineer Internship case study).

## Live deployment

| | |
|---|---|
| **Public GitHub repository** | [`https://github.com/Jayanprasad2004/document-intelligence-platform`](https://github.com/Jayanprasad2004/document-intelligence-platform) |
| **Frontend (live app)** | [`https://document-intelligence-platform-frontend.onrender.com`](https://document-intelligence-platform-frontend.onrender.com) |
| **Backend API** | [`https://document-intelligence-platform-regp.onrender.com`](https://document-intelligence-platform-regp.onrender.com) |
| **Swagger / OpenAPI docs** | [`https://document-intelligence-platform-regp.onrender.com/docs`](https://document-intelligence-platform-regp.onrender.com/docs) |

> The backend is on Render's free tier and spins down after 15 minutes of
> inactivity — the first request after idle time takes 30-60 seconds to wake
> up. This is expected, not a bug.

## Status

Fully functional end-to-end: file validation → OCR → LLM extraction →
financial validation → persistence → API → frontend, all implemented and
tested, deployed to Render.

## Architecture

See [`docs/architecture.svg`](./docs/architecture.svg) for the full diagram.

```
Frontend (HTML/CSS/JS)
        │
        ▼
REST API (FastAPI, Swagger docs at /docs)
        │
        ▼
File validation  →  OCR/parsing  →  LLM extraction  →  Financial validation
        │
        ▼
Persistence (SQLite locally / Postgres in production)
```

- **File validation** (`services/file_validation.py`) — type, size, page count
  (max 3 pages), using PyMuPDF, before any OCR is attempted.
- **OCR** (`services/ocr_service.py`) — every PDF page is OCR'd via Tesseract;
  none of the source financial-statement PDFs in the target dataset have an
  embedded text layer, so this is the primary path, not a fallback. Photographed
  documents (as opposed to flat scans) go through a document-boundary
  detection + perspective-correction step first, to flatten skew/rotation and
  crop background before OCR.
- **Extraction** (`services/extraction_service.py`) — calls an LLM (Groq, see
  below) with a forced tool-call so the response is guaranteed-shape JSON.
  Prompted to return `null` rather than invent any value not actually
  evidenced in the OCR text, with a `source_text` requirement enforced down
  to the individual line-item level.
- **Financial validation** (`services/financial_validation.py`) — formula
  checks dispatched by `document_type`; each returns `NOT_APPLICABLE` rather
  than `FAIL` when a required field isn't present, given a $0.01 tolerance.
- **Persistence** (`db/`) — SQLAlchemy, keyed by `document_name`.

## Tech stack & rationale

| Layer | Choice | Why |
|---|---|---|
| API framework | FastAPI | Async, automatic OpenAPI/Swagger docs, Pydantic validation built in |
| OCR | Tesseract (local) | Free, no API key/quota, works offline |
| LLM extraction | Groq (`openai/gpt-oss-120b`) | Genuinely free tier (no credit card), OpenAI-compatible tool-calling API |
| Database | SQLite (dev) / Postgres (prod) | SQLAlchemy abstracts the swap; Postgres needed in production since most hosts wipe local disk on restart |
| Hosting | Render | One of the few platforms with an actual ongoing free tier as of 2026 (Railway/Fly.io have both moved to paid-only) |
| Image preprocessing | OpenCV | Perspective correction for photographed (non-scanned) documents |

## Document types supported

`invoice`, `balance_sheet`, `profit_loss`, `cash_flow` — see
`extraction_service.FIELD_HINTS` for the exact field set targeted per type,
and `financial_validation.py` for the formula each type is checked against
(the balance sheet check in particular is written for a bank's layout —
`total_capital_and_liabilities == total_assets` — not the generic
Assets = Liabilities + Equity formula, since that's what the target dataset
actually contains).

## Local setup

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # fill in LLM_API_KEY (get one free at console.groq.com/keys)
uvicorn app.main:app --reload
```

Open `frontend/index.html` via a static server (e.g. `python -m http.server`
from `frontend/`) — don't just double-click it, since `API_BASE_URL` in
`frontend/js/app.js` needs to be reachable. Set that constant to your
backend's local (`http://localhost:8000/api`) or deployed URL.

Run tests: `pytest -v` from `backend/` (16 tests, LLM calls mocked — no API
key required to run the suite).

## Deploying your own copy

See [`DEPLOYMENT.md`](./DEPLOYMENT.md) for the full Render deployment guide
(Postgres → backend Docker web service → frontend static site → lock down
CORS).

## Assumptions

- The dataset's balance sheet source documents are a **bank's** consolidated
  statements, so the balance sheet check is `total_capital_and_liabilities
  == total_assets`, not the generic Assets = Liabilities + Equity formula —
  this was an explicit choice based on inspecting the actual provided
  documents, not a generic assumption.
- `document_type` is supplied by the caller (not auto-classified) per the
  brief's requirement of manual type selection.
- A $0.01 absolute tolerance is used for all financial PASS/FAIL checks,
  to absorb floating-point rounding without being loose enough to mask
  real discrepancies.
- Re-processing a document with the same `document_name` creates a new
  row rather than overwriting; `GET /api/documents/{name}` returns the
  most recent one. Full history is retained but not currently exposed via
  a dedicated endpoint.
- OCR is assumed to be the bottleneck on accuracy, not the LLM extraction
  step — this was verified directly (see Known Limitations) rather than
  assumed.

## API examples

`POST /api/documents/process` (multipart form: `file` + `document_type`):

```bash
curl -X POST "https://document-intelligence-platform-regp.onrender.com/api/documents/process" \
  -F "file=@invoice.jpg" \
  -F "document_type=invoice"
```

`GET /api/documents/{document_name}` — retrieve the latest result for a
specific processed document:

```bash
curl "https://document-intelligence-platform-regp.onrender.com/api/documents/invoice.jpg"
```

`GET /api/documents` — list all processed documents (used by the dashboard):

```bash
curl "https://document-intelligence-platform-regp.onrender.com/api/documents"
```

Full request/response schemas are in the interactive docs at `/docs`. See
[`sample_outputs/`](./sample_outputs/) for a complete real response —
`invoice_batch1-1109_sample_response.json` includes extracted fields with
`source_text`/`page_number` grounding, line items, and financial validation
check results.

## AI coding assistants used

Claude (Anthropic) was used throughout as an AI coding assistant — see
[`AI_USAGE_DECLARATION.md`](./AI_USAGE_DECLARATION.md) for the full,
specific breakdown of where and how.

## Known limitations

- **OCR quality on photographed (not scanned) documents is uneven.**
  Perspective correction and EXIF-orientation handling measurably help, but
  low-resolution source photos, handwriting overlapping printed text, and
  cursive/stylized fonts still produce real misreads that no amount of
  prompt engineering fully recovers from — this is a ceiling of free local
  OCR, not a logic bug. Verified against the dataset's hardest case (a
  skewed, handwritten-over phone photo).
- **Extraction is an LLM call and is not deterministic** — the same document
  processed twice may return slightly different `confidence` values or, in
  rare cases, a differently-phrased `source_text`. Financial validation
  results (the actual pass/fail determination) have been more stable in
  testing than incidental fields like `confidence`.
- **`overall_confidence`** is defined in the schema but not currently
  computed/populated — it's always `null`. Would need an aggregation rule
  (e.g. mean of per-field confidences) to be meaningful.
- **Groq free-tier rate limits** (~30 req/min, ~1,000 req/day on
  `openai/gpt-oss-120b`) apply in production identically to testing — fine
  for demo/evaluation traffic, not for real production volume.
- **No automated CI** — tests are run manually, not on push.

## Possible next steps / production hardening

- Add CI (GitHub Actions) running `pytest` on every push before deploy.
- Compute `overall_confidence` from per-field confidence values.
- Add monitoring/alerting — the free Render tier has none built in.
- Consider a paid LLM tier or a second provider fallback if Groq rate limits
  become a real constraint.
- Revisit OCR preprocessing per document type rather than one pipeline for
  all (e.g. the SROIE-style small receipts might benefit from upscaling
  before OCR, which wasn't tested).
