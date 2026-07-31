"""
Tests for core infrastructure: config, database, and Redis client.
"""

import asyncio

import pytest
import pytest_asyncio
from app.core.config import settings
from app.core.redis_client import redis_client
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def _postgres_reachable() -> bool:
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
    finally:
        await engine.dispose()


@pytest.fixture
def skip_if_no_postgres():
    """Skip test when PostgreSQL is not running."""
    import asyncio
    try:
        reachable = asyncio.run(_postgres_reachable())
    except RuntimeError:
        # If there's already a running loop (e.g. in some async contexts), try a new one
        reachable = False
    if not reachable:
        pytest.skip("PostgreSQL not reachable — start Docker.")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class TestSettings:
    def test_api_prefix(self):
        assert settings.API_V1_STR.startswith("/")

    def test_project_name_non_empty(self):
        assert len(settings.PROJECT_NAME) > 0

    def test_database_url_scheme(self):
        assert settings.DATABASE_URL.startswith("postgresql+asyncpg://")

    def test_database_url_contains_db_name(self):
        assert settings.POSTGRES_DB in settings.DATABASE_URL

    def test_redis_url_scheme(self):
        assert settings.REDIS_URL.startswith("redis://")

    def test_rabbitmq_url_scheme(self):
        assert settings.RABBITMQ_URL.startswith("amqp://")

    def test_environment_is_set(self):
        assert settings.ENVIRONMENT in ("development", "staging", "production")

    def test_postgres_port_default(self):
        assert isinstance(settings.POSTGRES_PORT, int)
        assert settings.POSTGRES_PORT > 0


# ---------------------------------------------------------------------------
# Database connectivity
# ---------------------------------------------------------------------------

class TestDatabaseConnection:
    @pytest.mark.asyncio
    async def test_engine_connects(self, skip_if_no_postgres):
        from sqlalchemy.ext.asyncio import create_async_engine
        engine = create_async_engine(settings.DATABASE_URL)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_session_factory_works(self, skip_if_no_postgres):
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            assert db_name == settings.POSTGRES_DB

    @pytest.mark.asyncio
    async def test_pgvector_extension_enabled(self, skip_if_no_postgres):
        engine = create_async_engine(settings.DATABASE_URL)
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT extname FROM pg_extension WHERE extname='vector'")
            )
            ext = result.scalar()
            assert ext == "vector", "pgvector extension is not installed"
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_all_expected_tables_exist(self, skip_if_no_postgres):
        engine = create_async_engine(settings.DATABASE_URL)
        expected_tables = {
            "orders", "order_items", "products", "customers",
            "inventory", "warehouses", "suppliers", "supplier_products",
            "shipments", "carriers", "transportation_routes",
            "manufacturing_orders", "purchase_orders", "demand_forecasts",
            "finance_transactions", "risk_assessments", "pricing_history",
            "contracts", "contract_products", "promotions", "promotion_products",
            "quality_inspections", "support_tickets", "sustainability_metrics",
            "reports", "events", "audit_logs", "agent_runtime", "semantic_documents",
        }
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname='public'")
            )
            actual_tables = {r[0] for r in result.fetchall()}
        await engine.dispose()
        missing = expected_tables - actual_tables
        assert not missing, f"Missing tables in DB: {missing}"

    @pytest.mark.asyncio
    async def test_all_expected_enums_exist(self, skip_if_no_postgres):
        engine = create_async_engine(settings.DATABASE_URL)
        expected_enums = {
            "order_status", "order_priority", "shipment_status",
            "supplier_status", "warehouse_status", "manufacturing_status",
            "risk_mitigation_status", "transaction_type", "agent_status",
            "event_priority", "inspection_result", "carrier_status",
            "ticket_status", "ticket_category", "pricing_trigger",
            "promotion_status", "report_type", "report_status",
            "risk_entity_type", "freight_mode_type", "contract_status",
        }
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT typname FROM pg_type WHERE typtype='e'")
            )
            actual_enums = {r[0] for r in result.fetchall()}
        await engine.dispose()
        missing = expected_enums - actual_enums
        assert not missing, f"Missing DB enums: {missing}"

    @pytest.mark.asyncio
    async def test_seed_data_products(self, skip_if_no_postgres):
        engine = create_async_engine(settings.DATABASE_URL)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT COUNT(*) FROM products"))
            count = result.scalar()
        await engine.dispose()
        assert count >= 10, "Expected at least 10 seed products"

    @pytest.mark.asyncio
    async def test_seed_data_inventory(self, skip_if_no_postgres):
        engine = create_async_engine(settings.DATABASE_URL)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT COUNT(*) FROM inventory"))
            count = result.scalar()
        await engine.dispose()
        assert count >= 22, "Expected at least 22 seed inventory records"


# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------

def _redis_available() -> bool:
    async def _check():
        try:
            await asyncio.wait_for(redis_client.client.ping(), timeout=1.0)
            return True
        except Exception:
            return False
    return asyncio.get_event_loop().run_until_complete(_check())


@pytest.fixture
def skip_if_no_redis():
    """Skip the test if Redis is not reachable."""
    try:
        loop = asyncio.get_event_loop()
        reachable = loop.run_until_complete(
            asyncio.wait_for(redis_client.client.ping(), timeout=1.0)
        )
        if not reachable:
            pytest.skip("Redis unavailable")
    except Exception:
        pytest.skip("Redis unavailable")


class TestRedisClient:
    @pytest.mark.asyncio
    async def test_set_and_get(self, skip_if_no_redis):
        key = f"test:core:{__name__}:set_get"
        await redis_client.set(key, "hello", expire=10)
        value = await redis_client.get(key)
        assert value == "hello"
        await redis_client.delete(key)

    @pytest.mark.asyncio
    async def test_get_missing_key_returns_none(self, skip_if_no_redis):
        result = await redis_client.get(f"test:core:nonexistent:{__name__}")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_existing_key(self, skip_if_no_redis):
        key = f"test:core:{__name__}:delete"
        await redis_client.set(key, "value", expire=30)
        deleted = await redis_client.delete(key)
        assert deleted == 1
        assert await redis_client.get(key) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key(self, skip_if_no_redis):
        deleted = await redis_client.delete(f"test:core:nokey:{__name__}")
        assert deleted == 0

    @pytest.mark.asyncio
    async def test_overwrite_key(self, skip_if_no_redis):
        key = f"test:core:{__name__}:overwrite"
        await redis_client.set(key, "first", expire=10)
        await redis_client.set(key, "second", expire=10)
        value = await redis_client.get(key)
        assert value == "second"
        await redis_client.delete(key)

    @pytest.mark.asyncio
    async def test_set_returns_true(self, skip_if_no_redis):
        key = f"test:core:{__name__}:bool"
        result = await redis_client.set(key, "ok", expire=5)
        assert result is True
        await redis_client.delete(key)
