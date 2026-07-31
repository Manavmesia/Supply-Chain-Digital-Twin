import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from app.models.base import Base
from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.contract import Contract
    from app.models.product import Product


class ContractProduct(Base):
    __tablename__ = "contract_products"

    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contracts.contract_id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.product_id", onupdate="CASCADE", ondelete="RESTRICT"),
        primary_key=True,
    )
    contracted_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    min_volume: Mapped[int | None] = mapped_column(Integer, default=0, nullable=True)
    max_volume: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    contract: Mapped["Contract"] = relationship(
        "Contract", back_populates="contract_products"
    )
    product: Mapped["Product"] = relationship("Product")
