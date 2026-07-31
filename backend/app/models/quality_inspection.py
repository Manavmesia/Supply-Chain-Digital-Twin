import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from app.models.base import Base
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.manufacturing_order import ManufacturingOrder
    from app.models.product import Product
    from app.models.supplier import Supplier


class QualityInspection(Base):
    __tablename__ = "quality_inspections"

    inspection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.product_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    manufacturing_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("manufacturing_orders.mo_id", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
    )
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.supplier_id", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
    )
    inspection_result: Mapped[str] = mapped_column(
        Enum("pass", "fail", "partial_pass", "pending", name="inspection_result"),
        default="pending",
        nullable=False,
    )
    defect_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    defect_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    sample_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    corrective_action: Mapped[str | None] = mapped_column(String, nullable=True)
    inspector_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    inspected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product")
    manufacturing_order: Mapped["ManufacturingOrder | None"] = relationship(
        "ManufacturingOrder"
    )
    supplier: Mapped["Supplier | None"] = relationship("Supplier")
