Sample processed-document responses matching the mandatory API schema.

`invoice_batch1-1109_sample_response.json` — generated end-to-end through
the real pipeline (file validation → OCR → extraction → financial
validation → persistence → API response) against
`New Dataset/Invoices/batch1-1109.jpg`. The LLM call itself was mocked
with plausible extracted values to produce this sample without requiring
a live API key; replace with a real run's output once `LLM_API_KEY` is
set, using this as the shape/format reference in the meantime.
