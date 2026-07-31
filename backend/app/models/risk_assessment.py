import uuid
from datetime import datetime
from decimal import Decimal

from app.models.base import Base
from sqlalchemy import DateTime, Enum, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    risk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    entity_type: Mapped[str] = mapped_column(
        Enum(
            "order", "supplier", "warehouse", "shipment",
            "manufacturing_order", "route", "product",
            name="risk_entity_type",
        ),
        nullable=False,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    risk_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    risk_category: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    mitigation_plan: Mapped[str | None] = mapped_column(String, nullable=True)
    mitigation_status: Mapped[str] = mapped_column(
        Enum(
            "detected", "under_review", "mitigated", "escalated", "resolved", "ignored",
            name="risk_mitigation_status",
        ),
        default="detected",
        nullable=False,
    )
    assessed_by_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
