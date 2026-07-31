import uuid
from datetime import datetime
from typing import Any

from app.models.base import Base
from sqlalchemy import DateTime, Enum, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column


class Event(Base):
    __tablename__ = "events"

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    correlation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    source_agent: Mapped[str] = mapped_column(String, nullable=False)
    target_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    priority: Mapped[str] = mapped_column(
        Enum("low", "medium", "high", "critical", name="event_priority"),
        default="medium",
        nullable=False,
    )
    version: Mapped[str] = mapped_column(String, default="1.0", nullable=False)
    payload: Mapped[Any] = mapped_column(JSONB, default=dict, nullable=False)
    event_metadata: Mapped[Any] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    simulation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
