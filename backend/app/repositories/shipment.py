import uuid

from app.models.shipment import Shipment
from app.repositories.base import BaseRepository
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class ShipmentRepository(BaseRepository[Shipment]):
    def __init__(self, session: AsyncSession):
        super().__init__(Shipment, session)

    async def get_by_order_id(self, order_id: uuid.UUID) -> Shipment | None:
        query = select(Shipment).where(Shipment.order_id == order_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_by_status(self, status: str) -> list[Shipment]:
        query = select(Shipment).where(Shipment.status == status)
        result = await self.session.execute(query)
        return list(result.scalars().all())
