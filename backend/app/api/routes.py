"""
REST API routes. Orchestrates: file_validation -> ocr_service ->
extraction_service -> financial_validation -> persistence_service.
Keeps HTTP concerns (status codes, request/response models) separate
from business logic, which lives in app.services.*.
"""
import time
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, Form, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services import (
    file_validation,
    ocr_service,
    extraction_service,
    financial_validation,
    persistence_service,
)
from app.models.schemas import DocumentProcessingResponse, ProcessingMetadata
from app.core.logging_config import logger

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.post("/documents/process", response_model=DocumentProcessingResponse)
async def process_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    db: Session = Depends(get_db),
):
    started = time.time()
    file_bytes = await file.read()

    validation_result = file_validation.validate_file(file_bytes, file.content_type)

    text_blocks = ocr_service.extract_text(file_bytes, file.content_type)
    extracted_data = extraction_service.extract_fields(text_blocks, document_type)
    validation = financial_validation.run_validations(extracted_data, document_type)

    response = DocumentProcessingResponse(
        document_name=file.filename,
        document_type=document_type,
        processing_status="PASS" if validation.overall_status != "FAIL" else "FAIL",
        file_validation=validation_result,
        extracted_data=extracted_data,
        validation=validation,
        processing_metadata=ProcessingMetadata(
            ocr_used=True,
            processed_at=datetime.now(timezone.utc).isoformat(),
            processing_time_ms=int((time.time() - started) * 1000),
        ),
    ).model_dump()

    persistence_service.save_processing_result(db, response)
    logger.info(f"Processed document '{file.filename}' -> {response['processing_status']}")
    return response


@router.get("/documents/{document_name}")
def get_document(document_name: str, db: Session = Depends(get_db)):
    return persistence_service.get_result_by_name(db, document_name)


@router.get("/documents")
def list_documents(db: Session = Depends(get_db)):
    return persistence_service.list_results(db)
