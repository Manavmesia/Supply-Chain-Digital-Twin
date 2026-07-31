"""Repository for Promotion domain queries."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from app.models.promotion import Promotion
from app.models.promotion_product import PromotionProduct
from app.repositories.base import BaseRepository
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class PromotionRepository(BaseRepository[Promotion]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Promotion, session)

    async def get_active_promotions(self) -> Sequence[Promotion]:
        """Return all promotions whose status is 'active'.

        These are promotions that the Celery ``PromotionActivationChecker``
        task (US-65) has already started and not yet ended.  The Demand
        Forecast Agent uses this list to apply demand lift adjustments.
        """
        query = (
            select(Promotion)
            .where(Promotion.status == "active")
            .order_by(Promotion.starts_at.asc())
            .options(selectinload(Promotion.promotion_products))
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_product(self, product_id: uuid.UUID) -> Sequence[Promotion]:
        """Return all non-cancelled promotions that include *product_id*.

        Performs a JOIN through the ``promotion_products`` association table
        so callers do not need to know the join logic.
        """
        now = datetime.now(tz=UTC)
        query = (
            select(Promotion)
            .join(
                PromotionProduct,
                PromotionProduct.promotion_id == Promotion.promotion_id,
            )
            .where(
                PromotionProduct.product_id == product_id,
                Promotion.status.in_(["scheduled", "active"]),
                Promotion.ends_at >= now,
            )
            .order_by(Promotion.starts_at.asc())
            .options(selectinload(Promotion.promotion_products))
        )
        result = await self.session.execute(query)
        return result.scalars().unique().all()
