"""
Shared pytest fixtures for the entire test suite.

All DB fixtures create rows inside a transaction that is rolled back
after each test, so tests are fully isolated from one another and
from the persistent seed data.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


# ---------------------------------------------------------------------------
# Engine / Session — lazy: engine is only created when a test actually needs it
# ---------------------------------------------------------------------------

def _make_engine():
    return create_async_engine(settings.DATABASE_URL, echo=False, pool_pre_ping=True)


async def _db_reachable() -> bool:
    """Return True if PostgreSQL is currently reachable."""
    from sqlalchemy import text
    engine = _make_engine()
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
    """
    Provide a rolled-back AsyncSession for each test.

    Automatically skips with a clear message when PostgreSQL is not running,
    so the test suite never shows misleading ERROR/FAIL states just because
    Docker is down.
    """
    if not await _db_reachable():
        pytest.skip("PostgreSQL is not reachable — start Docker and run again.")

    engine = _make_engine()
    try:
        async with engine.connect() as conn:
            await conn.begin()
            session = AsyncSession(bind=conn, expire_on_commit=False)
            yield session
            await session.close()
            await conn.rollback()
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# Pre-built seed UUIDs (already in DB from 03_seed.sql)
# ---------------------------------------------------------------------------

CUSTOMER_ID = uuid.UUID("11111111-0000-0000-0000-000000000001")  # Acme Corp
PRODUCT_LAPTOP_ID = uuid.UUID("22222222-0000-0000-0000-000000000001")  # ELEC-LAP-001
PRODUCT_MONITOR_ID = uuid.UUID("22222222-0000-0000-0000-000000000002")
WAREHOUSE_EAST_ID = uuid.UUID("33333333-0000-0000-0000-000000000001")  # WH-EAST-01
WAREHOUSE_WEST_ID = uuid.UUID("33333333-0000-0000-0000-000000000002")
SUPPLIER_TECHCORE_ID = uuid.UUID("44444444-0000-0000-0000-000000000001")  # TechCore


# ---------------------------------------------------------------------------
# Model factory helpers
# ---------------------------------------------------------------------------

def make_order(customer_id: uuid.UUID = CUSTOMER_ID, **kwargs):
    from app.models.order import Order
    return Order(
        order_id=uuid.uuid4(),
        customer_id=customer_id,
        status=kwargs.get("status", "pending"),
        priority=kwargs.get("priority", "standard"),
        total_amount=kwargs.get("total_amount", Decimal("1000.00")),
        currency=kwargs.get("currency", "USD"),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def make_shipment(order_id: uuid.UUID, **kwargs):
    from app.models.shipment import Shipment
    return Shipment(
        shipment_id=uuid.uuid4(),
        order_id=order_id,
        status=kwargs.get("status", "pending"),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def make_carrier(**kwargs):
    from app.models.carrier import Carrier
    return Carrier(
        carrier_id=uuid.uuid4(),
        name=kwargs.get("name", "Test Carrier"),
        code=kwargs.get("code", f"TC-{uuid.uuid4().hex[:6].upper()}"),
        freight_modes=kwargs.get("freight_modes", ["air"]),
        reliability_score=kwargs.get("reliability_score", Decimal("90.00")),
        avg_delay_days=kwargs.get("avg_delay_days", Decimal("0.50")),
        status=kwargs.get("status", "active"),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def make_transportation_route(carrier_id: uuid.UUID, **kwargs):
    from app.models.transportation_route import TransportationRoute
    return TransportationRoute(
        route_id=uuid.uuid4(),
        carrier_id=carrier_id,
        origin_location=kwargs.get("origin_location", "Newark, US"),
        destination=kwargs.get("destination", "Los Angeles, US"),
        freight_mode=kwargs.get("freight_mode", "road"),
        transit_days=kwargs.get("transit_days", 3),
        base_cost=kwargs.get("base_cost", Decimal("500.00")),
        cost_per_kg=kwargs.get("cost_per_kg", Decimal("0.50")),
        cost_per_m3=kwargs.get("cost_per_m3", Decimal("10.00")),
        is_active=kwargs.get("is_active", True),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def make_purchase_order(
    supplier_id: uuid.UUID = SUPPLIER_TECHCORE_ID,
    product_id: uuid.UUID = PRODUCT_LAPTOP_ID,
    warehouse_id: uuid.UUID = WAREHOUSE_EAST_ID,
    **kwargs,
):
    from app.models.purchase_order import PurchaseOrder
    qty = kwargs.get("quantity", 10)
    unit_cost = kwargs.get("unit_cost", Decimal("72000.00"))
    return PurchaseOrder(
        po_id=uuid.uuid4(),
        supplier_id=supplier_id,
        product_id=product_id,
        warehouse_id=warehouse_id,
        quantity=qty,
        unit_cost=unit_cost,
        currency=kwargs.get("currency", "USD"),
        status=kwargs.get("status", "draft"),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def make_support_ticket(customer_id: uuid.UUID = CUSTOMER_ID, **kwargs):
    from app.models.support_ticket import SupportTicket
    return SupportTicket(
        ticket_id=uuid.uuid4(),
        customer_id=customer_id,
        category=kwargs.get("category", "other"),
        status=kwargs.get("status", "open"),
        subject=kwargs.get("subject", "Test ticket"),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def make_contract(supplier_id: uuid.UUID = SUPPLIER_TECHCORE_ID, **kwargs):
    from app.models.contract import Contract
    return Contract(
        contract_id=uuid.uuid4(),
        supplier_id=supplier_id,
        contract_reference=kwargs.get("contract_reference", f"REF-{uuid.uuid4().hex[:8].upper()}"),
        title=kwargs.get("title", "Test Contract"),
        status=kwargs.get("status", "active"),
        currency=kwargs.get("currency", "USD"),
        auto_renew=kwargs.get("auto_renew", False),
        start_date=kwargs.get("start_date", date(2025, 1, 1)),
        end_date=kwargs.get("end_date", date(2026, 12, 31)),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
