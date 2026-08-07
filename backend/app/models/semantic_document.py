import uuid
from datetime import datetime
from typing import Any

from app.models.base import Base
try:
    from pgvector.sqlalchemy import Vector as _VectorType
    _PGVECTOR_AVAILABLE = True
except ModuleNotFoundError:
    # pgvector not installed locally (Phase 5 dependency) — use a plain JSON column fallback
    _VectorType = None  # type: ignore[assignment]
    _PGVECTOR_AVAILABLE = False
from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column


class SemanticDocument(Base):
    __tablename__ = "semantic_documents"

    doc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    doc_type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(
        _VectorType(768) if _PGVECTOR_AVAILABLE else JSONB, nullable=True
    )
    doc_metadata: Mapped[Any] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
