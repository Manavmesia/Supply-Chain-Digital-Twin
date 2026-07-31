import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from app.models.base import Base
from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.product import Product


class PricingHistory(Base):
    __tablename__ = "pricing_history"

    price_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.product_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    previous_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    recommended_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    approved_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4), nullable=True
    )
    trigger_type: Mapped[str] = mapped_column(
        Enum(
            "demand_spike", "low_inventory", "promotion", "cost_change",
            "competitor_price", "manual", "risk_adjustment", "scheduled",
            name="pricing_trigger",
        ),
        default="manual",
        nullable=False,
    )
    trigger_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    reasoning: Mapped[str | None] = mapped_column(String, nullable=True)
    margin_impact: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 2), nullable=True
    )
    demand_signal: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    approved_by_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product")
