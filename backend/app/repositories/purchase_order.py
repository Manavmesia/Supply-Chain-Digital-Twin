"""Repository for PurchaseOrder domain queries."""

import uuid
from collections.abc import Sequence
from datetime import UTC, date

from app.models.purchase_order import PurchaseOrder
from app.repositories.base import BaseRepository
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class PurchaseOrderRepository(BaseRepository[PurchaseOrder]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(PurchaseOrder, session)

    async def get_by_supplier(
        self, supplier_id: uuid.UUID
    ) -> Sequence[PurchaseOrder]:
        """Return all purchase orders for a given supplier, newest first."""
        query = (
            select(PurchaseOrder)
            .where(PurchaseOrder.supplier_id == supplier_id)
            .order_by(PurchaseOrder.created_at.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_status(self, status: str) -> Sequence[PurchaseOrder]:
        """Return all purchase orders matching a specific status."""
        query = (
            select(PurchaseOrder)
            .where(PurchaseOrder.status == status)
            .order_by(PurchaseOrder.created_at.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_pending_delivery(
        self, as_of: date | None = None
    ) -> Sequence[PurchaseOrder]:
        """Return POs that are in flight (sent / acknowledged / in_transit /
        partially_received) and whose requested_delivery date is on or before
        *as_of* (defaults to today).

        Useful for the Supplier Agent to surface overdue deliveries.
        """
        from datetime import datetime

        cutoff = as_of or datetime.now(tz=UTC).date()

        query = select(PurchaseOrder).where(
            PurchaseOrder.status.in_(
                ["sent", "acknowledged", "in_transit", "partially_received"]
            ),
            PurchaseOrder.requested_delivery <= cutoff,
        )
        result = await self.session.execute(query)
        return result.scalars().all()
