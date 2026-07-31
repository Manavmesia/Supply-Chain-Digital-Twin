import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from app.models.base import Base
from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.shipment import Shipment


class SustainabilityMetric(Base):
    __tablename__ = "sustainability_metrics"

    metric_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    shipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shipments.shipment_id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    co2_emission_kg: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), default=0.0000, nullable=False
    )
    fuel_consumption_l: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True
    )
    distance_km: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    freight_mode: Mapped[str | None] = mapped_column(String, nullable=True)
    sustainability_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    green_alternatives: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    shipment: Mapped["Shipment"] = relationship("Shipment")
