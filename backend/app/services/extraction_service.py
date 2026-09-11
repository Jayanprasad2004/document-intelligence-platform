"""
LLM-based structured extraction layer. Takes OCR/parsed text blocks
and a document_type, calls the LLM with a forced tool-call so the
response is guaranteed-shape JSON (not free text we'd have to parse),
and returns extracted_data shaped to app.models.schemas.

Uses Groq (free tier, no credit card) via its OpenAI-compatible
endpoint -- same `openai` SDK as OpenAI itself, pointed at Groq's
base_url. Model defaults to openai/gpt-oss-120b: llama-3.3-70b-versatile
and llama-3.1-8b-instant (older recommendations) were deprecated by
Groq on 2026-08-16, so don't fall back to those if this needs
changing later -- check console.groq.com/docs/models first, model
availability shifts.

Must return null (never invent) for any value not actually evidenced
in text_blocks -- this is enforced by instruction in the prompt, not
by code, so the prompt wording matters as much as the schema.
"""
import json

import openai

from app.core.config import settings
from app.core.exceptions import ExtractionError
from app.core.logging_config import logger

DOCUMENT_TYPES = ["invoice", "balance_sheet", "profit_loss", "cash_flow"]

# Field names each prompt should target, matching what
# financial_validation.py expects to find in extracted_data.
# Populated per the dataset's actual source layout (a bank's
# consolidated statements) -- extend if a differently-shaped
# statement needs to be supported.
FIELD_HINTS = {
    "invoice": [
        "invoice_number", "invoice_date", "vendor_name", "currency",
        "subtotal", "tax_amount", "discount", "total_amount", "line_items",
    ],
    "balance_sheet": [
        "as_at_date", "total_capital_and_liabilities", "total_assets",
        "capital", "reserves_and_surplus", "deposits", "borrowings",
        "advances", "investments", "fixed_assets",
    ],
    "profit_loss": [
        "period_end_date", "interest_earned", "other_income", "total_income",
        "interest_expended", "operating_expenses", "provisions_and_contingencies",
        "total_expenditure", "net_profit_before_minority_interest",
    ],
    "cash_flow": [
        "period_end_date", "net_cash_from_operating_activities",
        "net_cash_from_investing_activities", "net_cash_from_financing_activities",
        "effect_of_fx_fluctuation", "net_increase_in_cash",
        "opening_cash_and_equivalents", "cash_acquired_on_amalgamation",
        "closing_cash_and_equivalents",
    ],
}

# Fields whose "value" is a line-items array rather than a scalar --
# built into the tool schema as an array-of-objects instead of the
# standard {value, confidence, page_number, source_text} shape.
_LINE_ITEM_FIELDS = {"line_items"}

_FIELD_SCHEMA = {
    "type": "object",
    "properties": {
        "value": {"description": "The extracted value, or null if not present in the document."},
        "confidence": {"type": ["number", "null"], "description": "0-1, optional."},
        "page_number": {"type": ["integer", "null"]},
        "source_text": {"type": ["string", "null"], "description": "Short quote evidencing this value."},
    },
    "required": ["value"],
}

_LINE_ITEM_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "description": {"type": ["string", "null"]},
            "quantity": {"type": ["number", "null"]},
            "unit_price": {"type": ["number", "null"]},
            "amount": {"type": ["number", "null"]},
            "source_text": {
                "type": ["string", "null"],
                "description": "Verbatim snippet from the page evidencing this row -- "
                "required so line items are held to the same grounding standard as "
                "top-level fields, not exempted from it.",
            },
        },
        # All 5 keys must be present on every row (each individually
        # nullable) -- forces the model to make an explicit decision on
        # every field instead of silently omitting ones it's unsure
        # about, which is indistinguishable from "not found" once
        # rendered but is a different failure mode worth being able to
        # tell apart when debugging extraction quality.
        "required": ["description", "quantity", "unit_price", "amount", "source_text"],
    },
}

_client = None


def _get_client() -> openai.OpenAI:
    global _client
    if _client is None:
        if not settings.llm_api_key:
            raise ExtractionError("LLM_API_KEY is not configured.")
        _client = openai.OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)
    return _client


def _build_tool_schema(document_type: str) -> dict:
    """OpenAI/Groq function-calling shape: {"type": "function", "function": {...}} --
    note this nests "parameters" one level deeper than Anthropic's flatter
    {"name", "input_schema"} shape."""
    fields = FIELD_HINTS.get(document_type, [])
    properties = {
        field: (_LINE_ITEM_SCHEMA if field in _LINE_ITEM_FIELDS else _FIELD_SCHEMA)
        for field in fields
    }
    return {
        "type": "function",
        "function": {
            "name": "extract_fields",
            "description": "Extract structured field data from the OCR'd document text.",
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": fields,
            },
        },
    }


def _build_prompt(text_blocks: list[dict], document_type: str) -> str:
    pages_text = "\n\n".join(
        f"--- Page {block['page_number']} ---\n{block['text']}" for block in text_blocks
    )
    fields = ", ".join(FIELD_HINTS.get(document_type, []))
    rules = [
        "- Use null for any field not actually present in the text above. "
        "Never guess, infer, or carry over a typical/expected value.",
        "- CRITICAL: every source_text you provide MUST be an exact, verbatim "
        "substring copied from the OCR text above -- character for character, "
        "including whatever errors/garbling it contains. If you cannot find a "
        "real substring to quote, that is a signal the value itself is not "
        "actually evidenced -- return null instead of inventing both a value "
        "and a matching-looking quote for it. This applies to line_items "
        "fields exactly as much as top-level fields -- do not leave a line "
        "item's amount null while inventing a quantity or unit_price for the "
        "same row; if one number in a row is genuinely illegible, null just "
        "that number, not the whole row, and never fabricate a different "
        "number to fill the gap. IMPORTANT: source_text for a line item does "
        "NOT need to cover every field in that row in one quote -- a single "
        "short snippet (e.g. just the amount, or just the row's start) is "
        "enough to justify the row. Never null out a quantity, unit_price, or "
        "amount that is genuinely visible in the text just because you can't "
        "fit one quote around all of them at once.",
        "- OCR text may contain recognition errors (misread digits/characters); "
        "use surrounding context to judge plausibility, but do not silently "
        "'correct' a value you are not confident about -- prefer null over "
        "a guess.",
        "- page_number should be the page the source_text came from.",
        "- For line_items, include every line item row found, in order. Many "
        "receipts/invoices print a leading item code or SKU number directly "
        "before the description (e.g. '013 SUMMER CUP...' or '489 TIGER "
        "BEER...') -- that leading number is a product code, NOT the "
        "quantity, unless the text separately confirms it as a quantity.",
    ]
    if document_type == "invoice":
        rules.append(
            "- Invoices name (at least) two parties: the seller/issuer and the "
            "buyer/client (sometimes labeled 'Bill To', 'Ship To', or 'Client'). "
            "vendor_name is the seller/issuer ONLY -- never merge or concatenate "
            "text from both parties into one value."
        )
        rules.append(
            "- currency is often shown only as a symbol ($, \u20ac, \u00a3, \u20b9, etc.) "
            "next to amounts, not as an explicit currency code or word. A symbol "
            "counts as valid evidence -- infer the currency from it (e.g. '$' -> "
            "'USD') rather than returning null just because no code/word appears. "
            "But a currency symbol must appear directly beside a monetary amount "
            "to count as evidence -- a stray '$' elsewhere (e.g. OCR noise from "
            "a misread letter like 'S' in a company name/registration number) "
            "is NOT currency evidence. If an explicit currency abbreviation "
            "(RM, USD, INR, MYR, etc.) appears next to amounts anywhere in the "
            "text, that takes priority over any ambiguous symbol."
        )

    return (
        f"The following is OCR-extracted text from a {document_type.replace('_', ' ')} "
        f"document, {len(text_blocks)} page(s).\n\n{pages_text}\n\n"
        f"Extract these fields using the extract_fields tool: {fields}.\n"
        "Rules:\n" + "\n".join(rules)
    )


def extract_fields(text_blocks: list[dict], document_type: str) -> dict:
    if document_type not in FIELD_HINTS:
        raise ExtractionError(f"Unknown document_type '{document_type}'.")

    tool_schema = _build_tool_schema(document_type)
    prompt = _build_prompt(text_blocks, document_type)

    try:
        response = _get_client().chat.completions.create(
            model=settings.llm_model,
            max_tokens=4096,
            tools=[tool_schema],
            tool_choice={"type": "function", "function": {"name": "extract_fields"}},
            messages=[{"role": "user", "content": prompt}],
            # gpt-oss models are reasoning models on Groq -- reasoning
            # output must be suppressed/separated when tool calls are
            # in play, or it can interfere with getting a clean
            # tool_calls response. See console.groq.com/docs/reasoning.
            extra_body={"reasoning_effort": "low"},
        )
    except openai.APIError as exc:
        logger.error(f"LLM API call failed: {exc}")
        raise ExtractionError(f"LLM API call failed: {exc}") from exc

    tool_calls = response.choices[0].message.tool_calls
    if not tool_calls:
        raise ExtractionError("LLM response did not include a tool call.")

    try:
        extracted = json.loads(tool_calls[0].function.arguments)
    except json.JSONDecodeError as exc:
        raise ExtractionError(f"LLM returned malformed tool-call arguments: {exc}") from exc

    return _fill_missing_fields(extracted, document_type)


def _fill_missing_fields(extracted: dict, document_type: str) -> dict:
    """
    Guarantees every field listed in FIELD_HINTS is present in the
    output (as an explicit null entry if the model omitted it),
    rather than silently missing keys -- the case study requires
    missing values to be returned as null, not left out entirely.
    """
    result = dict(extracted)
    for field in FIELD_HINTS.get(document_type, []):
        if field in result and result[field] is not None:
            continue
        result[field] = [] if field in _LINE_ITEM_FIELDS else {
            "value": None, "confidence": None, "page_number": None, "source_text": None,
        }
    return result