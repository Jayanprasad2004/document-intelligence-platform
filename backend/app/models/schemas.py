"""
Pydantic schemas defining the mandatory API response contract
(see case study section 5.2). All extraction/validation services
should return data already shaped to these models.
"""
from typing import Any, Optional
from pydantic import BaseModel


class FileValidationResult(BaseModel):
    file_type: str
    is_supported: bool
    is_readable: bool
    page_count: Optional[int] = None
    status: str  # PASS | FAIL


class ExtractedField(BaseModel):
    value: Optional[Any] = None
    confidence: Optional[float] = None
    page_number: Optional[int] = None
    source_text: Optional[str] = None


class LineItem(BaseModel):
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None


class ValidationCheck(BaseModel):
    name: str
    formula: str
    operands: dict[str, Any]
    calculated_value: Optional[float] = None
    reported_value: Optional[float] = None
    variance: Optional[float] = None
    status: str  # PASS | FAIL | NOT_APPLICABLE


class ValidationResult(BaseModel):
    checks: list[ValidationCheck]
    overall_status: str
    issues: list[str] = []


class ProcessingMetadata(BaseModel):
    ocr_used: bool
    processed_at: str
    processing_time_ms: int


class DocumentProcessingResponse(BaseModel):
    document_name: str
    document_type: str
    processing_status: str  # PASS | FAIL
    overall_confidence: Optional[float] = None
    file_validation: FileValidationResult
    extracted_data: dict[str, Any]
    validation: ValidationResult
    processing_metadata: ProcessingMetadata
