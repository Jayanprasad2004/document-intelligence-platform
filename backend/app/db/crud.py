"""
Persistence access functions. Keeps raw SQLAlchemy queries out of the
API/service layers. If the same document_name is processed again, the
new row becomes the one returned by get_latest_by_name (prior rows
are kept for history but are optional to expose).
"""
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.db_models import ProcessedDocument


def save_result(db: Session, document_name: str, document_type: str,
                 processing_status: str, result_json: dict) -> ProcessedDocument:
    record = ProcessedDocument(
        document_name=document_name,
        document_type=document_type,
        processing_status=processing_status,
        result_json=result_json,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_latest_by_name(db: Session, document_name: str) -> Optional[ProcessedDocument]:
    return (
        db.query(ProcessedDocument)
        .filter(ProcessedDocument.document_name == document_name)
        .order_by(desc(ProcessedDocument.created_at))
        .first()
    )


def list_all(db: Session) -> list[ProcessedDocument]:
    return (
        db.query(ProcessedDocument)
        .order_by(desc(ProcessedDocument.created_at))
        .all()
    )
