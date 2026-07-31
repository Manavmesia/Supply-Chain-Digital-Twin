"""Repository for Carrier domain queries."""

from collections.abc import Sequence
from decimal import Decimal

from app.models.carrier import Carrier
from app.repositories.base import BaseRepository
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class CarrierRepository(BaseRepository[Carrier]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Carrier, session)

    async def get_available(self, freight_mode: str) -> Sequence[Carrier]:
        """Return all active (non-blacklisted, non-inactive) carriers that
        support the requested *freight_mode*.

        The freight_modes column is a PostgreSQL ARRAY, so we use the ``@>``
        (contains) operator via SQLAlchemy's ``Carrier.freight_modes.contains``.
        """
        query = select(Carrier).where(
            Carrier.status == "active",
            Carrier.freight_modes.contains([freight_mode]),
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_reliability_threshold(
        self, min_score: Decimal | float
    ) -> Sequence[Carrier]:
        """Return active carriers whose reliability_score is at or above
        *min_score*.

        The Transportation Agent uses a default floor of 70 (per AIS-06),
        but callers may supply a stricter threshold for high-value shipments.
        """
        query = select(Carrier).where(
            Carrier.status == "active",
            Carrier.reliability_score >= Decimal(str(min_score)),
        )
        result = await self.session.execute(query)
        return result.scalars().all()
