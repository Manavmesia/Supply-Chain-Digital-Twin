from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from app.models.base import Base
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    def __init__(self, model: type[T], session: AsyncSession):
        self.model = model
        self.session = session

    async def get(self, id_: Any) -> T | None:
        return await self.session.get(self.model, id_)

    async def list(self, skip: int = 0, limit: int = 100) -> Sequence[T]:
        query = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def create(self, entity: T) -> T:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def delete(self, entity: T) -> None:
        await self.session.delete(entity)
        await self.session.flush()
