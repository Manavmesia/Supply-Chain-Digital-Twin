import uuid
from datetime import datetime
from decimal import Decimal

from app.models.base import Base
from sqlalchemy import DateTime, Enum, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class Supplier(Base):
    __tablename__ = "suppliers"

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String, nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String, nullable=True)
    country: Mapped[str | None] = mapped_column(String, nullable=True)
    rating: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), default=3.00, nullable=False
    )
    reliability_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=80.00, nullable=False
    )
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_terms_days: Mapped[int] = mapped_column(
        Integer, default=30, nullable=False
    )
    status: Mapped[str] = mapped_column(
        Enum("active", "inactive", "blacklisted", "under_review", name="supplier_status"),
        default="active",
        nullable=False,
    )
    blacklist_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
