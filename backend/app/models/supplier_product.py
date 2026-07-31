import uuid
from datetime import date, datetime
from decimal import Decimal

from app.models.base import Base
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class SupplierProduct(Base):
    __tablename__ = "supplier_products"

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.supplier_id", onupdate="CASCADE", ondelete="RESTRICT"),
        primary_key=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.product_id", onupdate="CASCADE", ondelete="RESTRICT"),
        primary_key=True,
    )
    contract_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    minimum_order_qty: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )
    max_order_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lead_time_override: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    contract_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    contract_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_preferred: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
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
