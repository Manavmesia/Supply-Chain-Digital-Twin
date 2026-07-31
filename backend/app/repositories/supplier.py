import uuid

from app.models.supplier import Supplier
from app.models.supplier_product import SupplierProduct
from app.repositories.base import BaseRepository
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class SupplierRepository(BaseRepository[Supplier]):
    def __init__(self, session: AsyncSession):
        super().__init__(Supplier, session)

    async def get_active_suppliers_for_product(
        self, product_id: uuid.UUID
    ) -> list[Supplier]:
        query = (
            select(Supplier)
            .join(SupplierProduct, Supplier.supplier_id == SupplierProduct.supplier_id)
            .where(
                SupplierProduct.product_id == product_id,
                Supplier.status == "active",
            )
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
