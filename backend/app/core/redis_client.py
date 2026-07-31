from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from app.core.config import settings

# Create connection pool
pool = aioredis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)


async def get_redis_client() -> AsyncGenerator[aioredis.Redis, None]:
    client = aioredis.Redis(connection_pool=pool)
    try:
        yield client
    finally:
        await client.close()


class RedisClient:
    def __init__(self):
        self.client = aioredis.Redis(connection_pool=pool)

    async def get(self, key: str) -> str | None:
        return await self.client.get(key)

    async def set(self, key: str, value: str, expire: int | None = None) -> bool:
        return await self.client.set(key, value, ex=expire)

    async def delete(self, key: str) -> int:
        return await self.client.delete(key)

    async def close(self) -> None:
        await self.client.close()


redis_client = RedisClient()
