import uuid
from datetime import datetime
from typing import Any

from app.models.base import Base
from sqlalchemy import BigInteger, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column


class Report(Base):
    __tablename__ = "reports"

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    report_type: Mapped[str] = mapped_column(
        Enum(
            "executive_summary", "operational_kpi", "financial", "risk",
            "sustainability", "quality", "audit", "workflow", "custom",
            name="report_type",
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("generating", "ready", "failed", "archived", name="report_status"),
        default="generating",
        nullable=False,
    )
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    correlation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    generated_by_agent: Mapped[str] = mapped_column(
        String, default="ADS-18", nullable=False
    )
    storage_url: Mapped[str | None] = mapped_column(String, nullable=True)
    payload_summary: Mapped[Any] = mapped_column(
        JSONB, default=dict, nullable=False
    )
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
