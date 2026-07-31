import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from app.models.base import Base
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.contract_product import ContractProduct
    from app.models.supplier import Supplier


class Contract(Base):
    __tablename__ = "contracts"

    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.supplier_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    contract_reference: Mapped[str] = mapped_column(
        String, unique=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(
            "draft", "active", "expiring_soon", "expired", "terminated", "under_review",
            name="contract_status",
        ),
        default="draft",
        nullable=False,
    )
    contract_type: Mapped[str | None] = mapped_column(String, nullable=True)
    total_value: Mapped[Decimal | None] = mapped_column(
        Numeric(16, 2), nullable=True
    )
    currency: Mapped[str] = mapped_column(String, default="USD", nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    auto_renew: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    notice_period_days: Mapped[int] = mapped_column(
        Integer, default=30, nullable=False
    )
    payment_terms_days: Mapped[int] = mapped_column(
        Integer, default=30, nullable=False
    )
    terms: Mapped[str | None] = mapped_column(String, nullable=True)
    document_url: Mapped[str | None] = mapped_column(String, nullable=True)
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
    contract_products: Mapped[list["ContractProduct"]] = relationship(
        "ContractProduct", back_populates="contract", cascade="all, delete-orphan"
    )
