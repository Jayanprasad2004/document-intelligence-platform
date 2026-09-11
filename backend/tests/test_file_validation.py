"""
Basic tests for the file-validation layer (case study section 11).
"""
import pytest
from app.core.exceptions import UnsupportedFileTypeError, InvalidFileError
from app.services.file_validation import validate_file


def test_rejects_unsupported_file_type():
    with pytest.raises(UnsupportedFileTypeError):
        validate_file(b"dummy", "application/zip")


def test_rejects_empty_file():
    with pytest.raises(InvalidFileError):
        validate_file(b"", "image/png")

# TODO: test_rejects_corrupted_pdf, test_rejects_page_count_over_limit
