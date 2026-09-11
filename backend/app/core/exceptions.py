"""
Custom exception types + a FastAPI exception handler registrar.
Every raised exception here is mapped to a controlled JSON error
response with an appropriate HTTP status code -- no raw stack traces
are ever returned to the client.
"""
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.logging_config import logger


class DocumentIntelligenceError(Exception):
    """Base class for all application-raised errors."""
    status_code = 500
    message = "An unexpected error occurred."

    def __init__(self, message: Optional[str] = None):
        self.message = message or self.message
        super().__init__(self.message)


class UnsupportedFileTypeError(DocumentIntelligenceError):
    status_code = 400
    message = "Unsupported file type."


class InvalidFileError(DocumentIntelligenceError):
    status_code = 400
    message = "File is empty, corrupted, or exceeds the page limit."


class OCRProcessingError(DocumentIntelligenceError):
    status_code = 502
    message = "OCR/parsing failed for the supplied document."


class ExtractionError(DocumentIntelligenceError):
    status_code = 502
    message = "Field extraction failed."


class DocumentNotFoundError(DocumentIntelligenceError):
    status_code = 404
    message = "No processed document found with that name."


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DocumentIntelligenceError)
    async def handle_app_error(request: Request, exc: DocumentIntelligenceError):
        logger.warning(f"{exc.__class__.__name__}: {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"status": "error", "detail": exc.message},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "detail": "Internal server error."},
        )
