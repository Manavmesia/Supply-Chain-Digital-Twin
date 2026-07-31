import uuid

from app.models.inventory import Inventory
from app.repositories.base import BaseRepository
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class InventoryRepository(BaseRepository[Inventory]):
    def __init__(self, session: AsyncSession):
        super().__init__(Inventory, session)

    async def get_by_product_and_warehouse(
        self, product_id: uuid.UUID, warehouse_id: uuid.UUID
    ) -> Inventory | None:
        query = select(Inventory).where(
            Inventory.product_id == product_id,
            Inventory.warehouse_id == warehouse_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def check_availability(
        self, product_id: uuid.UUID, warehouse_id: uuid.UUID, quantity: int
    ) -> bool:
        inv = await self.get_by_product_and_warehouse(product_id, warehouse_id)
        if not inv:
            return False
        return (inv.available_qty - inv.reserved_qty) >= quantity
