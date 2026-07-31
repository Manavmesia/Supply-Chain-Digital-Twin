import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from app.models.base import Base
from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.warehouse import Warehouse


class Inventory(Base):
    __tablename__ = "inventory"

    inventory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
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
    available_qty: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    reserved_qty: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    safety_stock: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    reorder_point: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    reorder_qty: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    last_counted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
