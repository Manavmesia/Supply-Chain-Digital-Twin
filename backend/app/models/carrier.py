import uuid
from datetime import datetime
from decimal import Decimal

from app.models.base import Base
from sqlalchemy import DateTime, Enum, Numeric, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

# Carrier freight modes use a custom PG enum type in the DB.
# We store as ARRAY of that enum; SQLAlchemy maps to list[str] cleanly.
_FREIGHT_MODE_ENUM = Enum(
    "air", "sea", "road", "rail", "multimodal",
    name="freight_mode_type",
    create_type=False,  # already created by DDL
)


class Carrier(Base):
    __tablename__ = "carriers"

    carrier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    freight_modes: Mapped[list[str]] = mapped_column(ARRAY(_FREIGHT_MODE_ENUM), nullable=False)
    tracking_url: Mapped[str | None] = mapped_column(String, nullable=True)
    api_endpoint: Mapped[str | None] = mapped_column(String, nullable=True)
    reliability_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=80.00, nullable=False
    )
    avg_delay_days: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), default=0.00, nullable=False
    )
    status: Mapped[str] = mapped_column(
        Enum("active", "inactive", "blacklisted", name="carrier_status"),
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
