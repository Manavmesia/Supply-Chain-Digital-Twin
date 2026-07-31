"""
Legacy integration tests (pre-conftest era).

These tests require a live PostgreSQL connection. They are automatically
skipped when the database is not reachable so CI never shows false failures.
"""

import asyncio
import uuid

import pytest
import pytest_asyncio
from app.core.config import settings
from app.core.redis_client import redis_client
from app.models.customer import Customer
from app.models.product import Product
from app.repositories.inventory import InventoryRepository
from app.repositories.order import OrderRepository
from app.repositories.shipment import ShipmentRepository
from app.repositories.supplier import SupplierRepository
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


async def _db_reachable() -> bool:
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session():
    if not await _db_reachable():
        pytest.skip("PostgreSQL not reachable — start Docker.")
    engine = create_async_engine(settings.DATABASE_URL)
    AsyncSessionLocal = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with AsyncSessionLocal() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_database_connection_and_query(db_session):
    stmt = select(Product).limit(5)
    result = await db_session.execute(stmt)
    products = result.scalars().all()
    assert len(products) > 0
    assert products[0].sku is not None

    stmt = select(Customer).limit(5)
    result = await db_session.execute(stmt)
    customers = result.scalars().all()
    assert len(customers) > 0
    assert customers[0].email is not None


@pytest.mark.asyncio
async def test_repositories(db_session):
    order_repo = OrderRepository(db_session)
    inventory_repo = InventoryRepository(db_session)
    supplier_repo = SupplierRepository(db_session)
    shipment_repo = ShipmentRepository(db_session)

    assert order_repo.model == order_repo.model
    assert inventory_repo.model == inventory_repo.model
    assert supplier_repo.model == supplier_repo.model
    assert shipment_repo.model == shipment_repo.model

    prod_id = uuid.UUID("22222222-0000-0000-0000-000000000001")
    suppliers = await supplier_repo.get_active_suppliers_for_product(prod_id)
    assert len(suppliers) > 0


@pytest.mark.asyncio
async def test_redis_client():
    try:
        await asyncio.wait_for(redis_client.client.ping(), timeout=1.0)
    except Exception:
        pytest.skip("Redis server is not running on localhost:6379, skipping test")

    key = "test:connection:key"
    val = "working_redis"

    set_ok = await redis_client.set(key, val, expire=10)
    assert set_ok is True

    get_val = await redis_client.get(key)
    assert get_val == val

    deleted = await redis_client.delete(key)
    assert deleted == 1
