import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from app.models.base import Base
from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.order import Order
    from app.models.shipment import Shipment


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.customer_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.order_id", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
    )
    shipment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shipments.shipment_id", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
    )
    category: Mapped[str] = mapped_column(
        Enum(
            "order_inquiry", "delivery_delay", "shipment_tracking",
            "return_request", "billing_issue", "product_quality", "other",
            name="ticket_category",
        ),
        default="other",
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Enum(
            "open", "in_progress", "pending_customer", "escalated", "resolved", "closed",
            name="ticket_status",
        ),
        default="open",
        nullable=False,
    )
    subject: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    resolution: Mapped[str | None] = mapped_column(String, nullable=True)
    assigned_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    sla_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    escalated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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
    customer: Mapped["Customer"] = relationship("Customer")
    order: Mapped["Order | None"] = relationship("Order")
    shipment: Mapped["Shipment | None"] = relationship("Shipment")
