"""Repository for Contract domain queries."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from app.models.contract import Contract
from app.repositories.base import BaseRepository
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class ContractRepository(BaseRepository[Contract]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Contract, session)

    async def get_expiring_soon(self, days: int = 30) -> Sequence[Contract]:
        """Return active contracts whose end_date falls within the next *days* days.

        Drives the Celery ``ContractExpiryChecker`` task (US-65) and the
        Procurement Strategy Agent subscription to ``ContractExpiring`` events.
        """
        today = datetime.now(tz=UTC).date()
        cutoff = today + timedelta(days=days)

        query = select(Contract).where(
            Contract.status.in_(["active", "expiring_soon"]),
            Contract.end_date >= today,
            Contract.end_date <= cutoff,
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_active_by_supplier(
        self, supplier_id: uuid.UUID
    ) -> Sequence[Contract]:
        """Return all active contracts for a specific supplier.

        Used by the Supplier Agent and Procurement Strategy Agent to check
        whether a valid contract exists before creating purchase orders.
        """
        query = select(Contract).where(
            Contract.supplier_id == supplier_id,
            Contract.status.in_(["active", "expiring_soon"]),
        )
        result = await self.session.execute(query)
        return result.scalars().all()
