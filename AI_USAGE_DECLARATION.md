# AI / Tool Usage Declaration

This project was built with Claude (Anthropic) as an AI coding assistant
throughout the development process, via Claude's chat interface with code
execution. This document declares specifically where and how it was used.

## Where AI assistance was used

- **Project scaffolding**: initial repository structure, separation of
  concerns across `services/`, `api/`, `core/`, `db/`, `models/`.
- **Backend implementation**: file validation, OCR pipeline, LLM extraction
  service, financial validation rule sets, persistence layer, and the
  FastAPI route layer were all written with Claude, iterated across
  multiple rounds as real bugs were found against the actual dataset.
- **OCR pipeline design and tuning**: the perspective-correction
  (document-boundary detection + warp) approach, EXIF-orientation handling,
  and the decision to use Tesseract's "best" tier language model over the
  default "fast" tier were all arrived at by testing directly against this
  project's dataset (not from general knowledge alone) — specific before/
  after comparisons are documented in the README's "Known limitations"
  section and in the git history/conversation log.
- **LLM provider selection and integration**: research into free-tier LLM
  options (Groq vs. Gemini vs. OpenRouter) and the extraction_service.py
  implementation (tool-calling schema, prompt design, anti-hallucination
  rules) were done with Claude.
- **Frontend**: the dashboard/detail-view redesign (HTML/CSS/JS, no
  framework) was designed and implemented with Claude, then verified with
  a real headless-browser test against the live backend and database
  before being considered complete.
- **Deployment**: the Dockerfile, Render deployment steps, CORS
  configuration, and Postgres connection-string handling were written with
  Claude's assistance, including debugging real deployment failures
  (Tesseract missing on PATH, a leaked API key caught by GitHub's push
  protection, EXIF-orientation bugs found via live testing).
- **Documentation**: this README, the architecture diagram, and this
  declaration itself were drafted with Claude.

## What was NOT auto-generated without verification

Every significant claim about system behavior in this project (OCR
accuracy comparisons, the financial validation formulas, the extraction
schema) was verified by actually running the code against the provided
dataset — not accepted from the AI's output without testing. Specific
examples:

- The Tesseract "best" vs "fast" model comparison was run directly against
  the dataset's hardest test document, with before/after outputs compared
  line by line.
- The financial validation formulas (e.g. the bank-specific balance sheet
  check) were verified against the actual 2024 figures in the provided
  dataset, not assumed from a generic template.
- The frontend redesign was tested end-to-end with a real backend, a
  seeded database, and a headless browser — not just visually reviewed as
  generated code.
- Deployment issues (missing Tesseract binary, leaked secret blocked by
  GitHub, EXIF rotation bug) were diagnosed from real error output/logs
  during actual deployment attempts, not anticipated in the abstract.

## Model/tool versions

- AI assistant: Claude (Anthropic), via claude.ai chat interface with code
  execution enabled.
- No other AI code-generation tools (Copilot, Cursor, etc.) were used.
