import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from app.models.base import Base
from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    FetchedValue,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.supplier import Supplier
    from app.models.warehouse import Warehouse


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    po_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.supplier_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.product_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.warehouse_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    total_cost: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), server_default=FetchedValue(), nullable=False
    )
    currency: Mapped[str] = mapped_column(String, default="USD", nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(
            "draft", "approved", "sent", "acknowledged", "in_transit",
            "partially_received", "received", "cancelled",
            name="purchase_order_status",
        ),
        default="draft",
        nullable=False,
    )
    requested_delivery: Mapped[date | None] = mapped_column(Date, nullable=True)
    confirmed_delivery: Mapped[date | None] = mapped_column(Date, nullable=True)
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    triggered_by_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
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
    supplier: Mapped["Supplier"] = relationship("Supplier")
    product: Mapped["Product"] = relationship("Product")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
