"""
Thin orchestration layer between the API and app.db.crud, so routes.py
doesn't talk to the ORM directly.
"""
from sqlalchemy.orm import Session

from app.db import crud
from app.core.exceptions import DocumentNotFoundError


def save_processing_result(db: Session, response: dict) -> None:
    crud.save_result(
        db=db,
        document_name=response["document_name"],
        document_type=response["document_type"],
        processing_status=response["processing_status"],
        result_json=response,
    )


def get_result_by_name(db: Session, document_name: str) -> dict:
    record = crud.get_latest_by_name(db, document_name)
    if record is None:
        raise DocumentNotFoundError(f"No result found for '{document_name}'.")
    return record.result_json


def list_results(db: Session) -> list[dict]:
    return [
        {
            "document_name": r.document_name,
            "document_type": r.document_type,
            "processing_status": r.processing_status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in crud.list_all(db)
    ]
