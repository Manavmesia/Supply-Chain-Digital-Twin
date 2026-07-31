from typing import Any

from app.models.order import Order
from app.repositories.base import BaseRepository
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class OrderRepository(BaseRepository[Order]):
    def __init__(self, session: AsyncSession):
        super().__init__(Order, session)

    async def get_with_items(self, order_id: Any) -> Order | None:
        query = (
            select(Order)
            .where(Order.order_id == order_id)
            .options(selectinload(Order.items))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_by_status(self, status: str) -> list[Order]:
        query = select(Order).where(Order.status == status)
        result = await self.session.execute(query)
        return list(result.scalars().all())
