"""
Tests for the extraction service. The LLM call itself is mocked --
these tests check the parts we control: schema construction, prompt
content, tool-call parsing, and the missing-field -> null backfill --
without requiring a real GROQ API key or network call in CI.

Mocks are shaped like the OpenAI-compatible chat-completions response
Groq returns (response.choices[0].message.tool_calls[0].function.arguments
as a JSON string), not Anthropic's content-block shape.
"""
import json
from types import SimpleNamespace
from unittest.mock import patch

from app.services import extraction_service
from app.services.extraction_service import (
    _build_tool_schema,
    _fill_missing_fields,
    extract_fields,
)


def _field(value):
    return {"value": value}


def _fake_completion(arguments_dict: dict):
    """Builds a mock matching openai.chat.completions.create()'s response shape."""
    fake_function = SimpleNamespace(name="extract_fields", arguments=json.dumps(arguments_dict))
    fake_tool_call = SimpleNamespace(function=fake_function)
    fake_message = SimpleNamespace(tool_calls=[fake_tool_call])
    fake_choice = SimpleNamespace(message=fake_message)
    return SimpleNamespace(choices=[fake_choice])


def test_build_tool_schema_invoice_uses_line_items_array():
    schema = _build_tool_schema("invoice")
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "extract_fields"
    params = schema["function"]["parameters"]
    assert params["properties"]["line_items"]["type"] == "array"
    assert params["properties"]["invoice_number"]["type"] == "object"
    # Line items must carry their own source_text -- same grounding
    # accountability as top-level fields, not exempted from it.
    line_item_props = params["properties"]["line_items"]["items"]["properties"]
    assert "source_text" in line_item_props
    assert set(params["properties"]["line_items"]["items"]["required"]) == set(line_item_props.keys())


def test_fill_missing_fields_adds_null_entries_for_omitted_fields():
    # Model only returned 2 of the 9 balance_sheet fields.
    partial = {
        "total_assets": {"value": 4030194.26, "confidence": 0.95, "page_number": 1, "source_text": "Total 4,030,194.26"},
        "as_at_date": {"value": "2024-03-31", "confidence": 0.9, "page_number": 1, "source_text": "As at March 31, 2024"},
    }
    result = _fill_missing_fields(partial, "balance_sheet")

    assert result["total_assets"]["value"] == 4030194.26
    assert result["capital"] == {"value": None, "confidence": None, "page_number": None, "source_text": None}
    assert set(result.keys()) == set(extraction_service.FIELD_HINTS["balance_sheet"])


def test_fill_missing_fields_defaults_line_items_to_empty_list():
    result = _fill_missing_fields({}, "invoice")
    assert result["line_items"] == []


def test_extract_fields_parses_mocked_tool_response():
    fake_response = _fake_completion({
        "invoice_number": {"value": "INV-23891", "confidence": 0.99, "page_number": 1, "source_text": "Invoice #: INV-23891"},
    })

    with patch("app.services.extraction_service._get_client") as mock_get_client:
        mock_get_client.return_value.chat.completions.create.return_value = fake_response
        result = extract_fields([{"page_number": 1, "text": "Invoice #: INV-23891"}], "invoice")

    assert result["invoice_number"]["value"] == "INV-23891"
    # Fields the mocked LLM didn't return must still be present as null.
    assert result["total_amount"]["value"] is None
    assert result["line_items"] == []


def test_extract_fields_rejects_unknown_document_type():
    import pytest
    from app.core.exceptions import ExtractionError

    with pytest.raises(ExtractionError):
        extract_fields([], "unknown_type")


def test_extract_fields_raises_when_no_tool_call_returned():
    import pytest
    from app.core.exceptions import ExtractionError

    fake_message = SimpleNamespace(tool_calls=None)
    fake_response = SimpleNamespace(choices=[SimpleNamespace(message=fake_message)])

    with patch("app.services.extraction_service._get_client") as mock_get_client:
        mock_get_client.return_value.chat.completions.create.return_value = fake_response
        with pytest.raises(ExtractionError):
            extract_fields([{"page_number": 1, "text": "irrelevant"}], "invoice")