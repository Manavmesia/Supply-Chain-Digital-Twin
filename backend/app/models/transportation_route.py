import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from app.models.base import Base
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.carrier import Carrier
    from app.models.warehouse import Warehouse


class TransportationRoute(Base):
    __tablename__ = "transportation_routes"

    route_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    carrier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carriers.carrier_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    origin_warehouse_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.warehouse_id", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
    )
    origin_location: Mapped[str] = mapped_column(String, nullable=False)
    destination: Mapped[str] = mapped_column(String, nullable=False)
    freight_mode: Mapped[str] = mapped_column(
        Enum("air", "sea", "road", "rail", "multimodal", name="freight_mode_type", create_type=False),
        nullable=False,
    )
    transit_days: Mapped[int] = mapped_column(Integer, nullable=False)
    base_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    cost_per_kg: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), default=0.0000, nullable=False
    )
    cost_per_m3: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), default=0.0000, nullable=False
    )
    co2_per_tonne_km: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 4), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    route_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    carrier: Mapped["Carrier"] = relationship("Carrier")
    origin_warehouse: Mapped["Warehouse | None"] = relationship("Warehouse")
