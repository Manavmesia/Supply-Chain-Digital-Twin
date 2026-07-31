import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from app.models.base import Base
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.warehouse import Warehouse


class DemandForecast(Base):
    __tablename__ = "demand_forecasts"

    forecast_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.product_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    warehouse_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.warehouse_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=True,
    )
    forecast_period: Mapped[date] = mapped_column(Date, nullable=False)
    forecast_qty: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    lower_bound: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    upper_bound: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    model_used: Mapped[str | None] = mapped_column(String, nullable=True)
    mape: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    is_anomaly: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    anomaly_description: Mapped[str | None] = mapped_column(
        String, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product")
    warehouse: Mapped["Warehouse | None"] = relationship("Warehouse")
