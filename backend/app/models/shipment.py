import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from app.models.base import Base
from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.carrier import Carrier
    from app.models.order import Order
    from app.models.warehouse import Warehouse


class Shipment(Base):
    __tablename__ = "shipments"

    shipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.order_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    warehouse_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.warehouse_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=True,
    )
    carrier: Mapped[str | None] = mapped_column(String, nullable=True)
    carrier_tracking_id: Mapped[str | None] = mapped_column(
        String, nullable=True
    )
    route: Mapped[str | None] = mapped_column(String, nullable=True)
    freight_mode: Mapped[str | None] = mapped_column(String, nullable=True)
    eta: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_delivery: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        Enum(
            "pending", "assigned", "dispatched", "in_transit",
            "delivered", "delayed", "failed", "returned",
            name="shipment_status",
        ),
        default="pending",
        nullable=False,
    )
    delay_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    carrier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carriers.carrier_id", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
    )
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
    order: Mapped["Order"] = relationship("Order")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    carrier_relation: Mapped["Carrier | None"] = relationship(
        "Carrier", foreign_keys=[carrier_id]
    )
