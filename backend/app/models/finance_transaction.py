import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from app.models.base import Base
from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.supplier import Supplier


class FinanceTransaction(Base):
    __tablename__ = "finance_transactions"

    txn_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.order_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=True,
    )
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.supplier_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=True,
    )
    transaction_type: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String, default="USD", nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    approved_by_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    order: Mapped["Order | None"] = relationship("Order")
    supplier: Mapped["Supplier | None"] = relationship("Supplier")
