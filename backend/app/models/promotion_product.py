import uuid
from typing import TYPE_CHECKING

from app.models.base import Base
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.promotion import Promotion


class PromotionProduct(Base):
    __tablename__ = "promotion_products"

    promotion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("promotions.promotion_id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.product_id", onupdate="CASCADE", ondelete="RESTRICT"),
        primary_key=True,
    )

    # Relationships
    promotion: Mapped["Promotion"] = relationship(
        "Promotion", back_populates="promotion_products"
    )
    product: Mapped["Product"] = relationship("Product")
