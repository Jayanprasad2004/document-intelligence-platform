"""
SQLAlchemy ORM models. A ProcessedDocument row stores the full
structured response as JSON, keyed by document_name, so the
GET-by-name endpoint can return the latest result.
"""
from sqlalchemy import Column, Integer, String, DateTime, JSON, func
from app.db.database import Base


class ProcessedDocument(Base):
    __tablename__ = "processed_documents"

    id = Column(Integer, primary_key=True, index=True)
    document_name = Column(String, index=True, nullable=False)
    document_type = Column(String, nullable=False)
    processing_status = Column(String, nullable=False)
    result_json = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
