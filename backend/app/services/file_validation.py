"""
Input-control layer (case study 4.1). Validates file type, readability,
page count and basic integrity BEFORE any OCR/extraction is attempted.
This is deliberately NOT document-type classification.
"""
import fitz  # PyMuPDF

from app.core.config import settings
from app.core.exceptions import UnsupportedFileTypeError, InvalidFileError
from app.models.schemas import FileValidationResult


def validate_file(file_bytes: bytes, content_type: str) -> FileValidationResult:
    if content_type not in settings.allowed_file_types_list:
        raise UnsupportedFileTypeError(f"'{content_type}' is not a supported file type.")

    if not file_bytes:
        raise InvalidFileError("Uploaded file is empty.")

    page_count = _get_page_count(file_bytes, content_type)

    if page_count > settings.max_page_count:
        raise InvalidFileError(
            f"Document has {page_count} pages; the limit is {settings.max_page_count}."
        )

    return FileValidationResult(
        file_type=content_type,
        is_supported=True,
        is_readable=True,
        page_count=page_count,
        status="PASS",
    )


def _get_page_count(file_bytes: bytes, content_type: str) -> int:
    if content_type == "application/pdf":
        # PyMuPDF reads page count from the PDF structure directly, so
        # this works the same whether or not the PDF has a text layer --
        # relevant here since none of the dataset's PDFs do (see
        # ocr_service.py). A cash-flow statement legitimately runs to
        # 2 pages, so this must stay a real count, not assume 1.
        try:
            with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                return doc.page_count
        except Exception as exc:
            raise InvalidFileError(f"PDF could not be opened: {exc}") from exc
    # JPG/PNG are always single-page.
    return 1
