"""Standby in-memory session provider for resilient multi-agent execution when PostgreSQL is offline."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import structlog

logger = structlog.get_logger(__name__)


# ── Standby Domain Objects ───────────────────────────────────────────────────

STANDBY_CUSTOMERS: dict[str, tuple[str, str]] = {
    "50000000-0000-0000-0000-000000000001": ("Siemens Global Automations", "enterprise"),
    "50000000-0000-0000-0000-000000000002": ("Tesla Energy & Storage", "premium"),
    "50000000-0000-0000-0000-000000000003": ("Schneider Electric Grid", "enterprise"),
    "50000000-0000-0000-0000-000000000004": ("Honeywell Aerospace", "standard"),
    "00000000-0000-0000-0000-000000000001": ("Siemens Global Automations", "enterprise"),
    "cust0000-0000-0000-0000-000000000001": ("Tesla Energy Solutions", "enterprise"),
    "cust0000-0000-0000-0000-000000000002": ("Siemens Robotics Global", "premium"),
    "cust0000-0000-0000-0000-000000000003": ("Schneider Power Grid", "enterprise"),
    "cust0000-0000-0000-0000-000000000004": ("Honeywell Industrial", "standard"),
}

STANDBY_PRODUCT_DATA: dict[str, tuple[str, str, Decimal]] = {
    "30000000-0000-0000-0000-000000000001": ("Industrial Sensor Module", "ELEC-001", Decimal("150.00")),
    "30000000-0000-0000-0000-000000000002": ("High-Torque Servo Motor", "ELEC-002", Decimal("280.00")),
    "30000000-0000-0000-0000-000000000003": ("IoT Gateway Device", "ELEC-003", Decimal("1249.99")),
    "30000000-0000-0000-0000-000000000004": ("Precision Ball Bearing Set", "MECH-001", Decimal("95.00")),
    "30000000-0000-0000-0000-000000000005": ("Hydraulic Actuator Cylinder", "MECH-002", Decimal("3450.00")),
    "30000000-0000-0000-0000-000000000006": ("Stainless Steel Valve Assembly", "MECH-003", Decimal("575.00")),
    "30000000-0000-0000-0000-000000000007": ("Industrial Lubricant (20L)", "CHEM-001", Decimal("185.00")),
    "30000000-0000-0000-0000-000000000008": ("Epoxy Adhesive Kit", "CHEM-002", Decimal("95.00")),
    "30000000-0000-0000-0000-000000000009": ("Safety Relay Module", "SAFE-001", Decimal("120.00")),
    "30000000-0000-0000-0000-000000000010": ("Emergency Stop Assembly", "SAFE-002", Decimal("145.00")),
    "00000000-0000-0000-0000-000000000002": ("Industrial IoT Sensor Hub v2", "ELEC-001", Decimal("150.00")),
}


class StandbyCustomer:
    def __init__(
        self,
        customer_id: Any = None,
        name: str | None = None,
        tier: str | None = None,
        is_active: bool = True,
    ) -> None:
        if isinstance(customer_id, str):
            try:
                self.customer_id = uuid.UUID(customer_id)
            except Exception:
                self.customer_id = customer_id
        else:
            self.customer_id = customer_id or uuid.UUID("50000000-0000-0000-0000-000000000001")
        resolved = STANDBY_CUSTOMERS.get(str(self.customer_id))
        self.name = name or (resolved[0] if resolved else "Enterprise Customer")
        self.customer_tier = tier or (resolved[1] if resolved else "enterprise")
        self.is_active = is_active
        self.email = f"procure@{self.name.lower().replace(' ', '')}.com"


class StandbyProduct:
    def __init__(
        self,
        product_id: Any = None,
        name: str | None = None,
        sku: str | None = None,
        price: Decimal | None = None,
        active: bool = True,
    ) -> None:
        if isinstance(product_id, str):
            try:
                self.product_id = uuid.UUID(product_id)
            except Exception:
                self.product_id = product_id
        else:
            self.product_id = product_id or uuid.UUID("30000000-0000-0000-0000-000000000001")
        resolved = STANDBY_PRODUCT_DATA.get(str(self.product_id))
        self.name = name or (resolved[0] if resolved else "Industrial Sensor Module")
        self.sku = sku or (resolved[1] if resolved else "ELEC-001")
        self.unit_price = price or (resolved[2] if resolved else Decimal("150.00"))
        self.active = active


class StandbyInventory:
    def __init__(
        self,
        product_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        available: int = 5000,
        reserved: int = 150,
        safety: int = 200,
    ) -> None:
        self.inventory_id = uuid.uuid4()
        self.product_id = product_id
        self.warehouse_id = warehouse_id
        self.available_qty = available
        self.reserved_qty = reserved
        self.safety_stock = safety


class StandbyWarehouse:
    def __init__(
        self,
        warehouse_id: uuid.UUID | None = None,
        name: str = "Pacific Northwest MegaHub",
        city: str = "Seattle",
        country: str = "US",
        capacity: int = 50000,
        load: int = 12500,
    ) -> None:
        self.warehouse_id = warehouse_id or uuid.UUID("22222222-0000-0000-0000-000000000001")
        self.name = name
        self.city = city
        self.country = country
        self.location = f"{city}, {country}"
        self.capacity_units = capacity
        self.current_load = load
        self.status = "active"


class StandbySupplier:
    def __init__(
        self,
        supplier_id: uuid.UUID | None = None,
        name: str = "Apex Microelectronics Inc.",
        lead_time: int = 4,
        reliability: Decimal = Decimal("96.5"),
    ) -> None:
        self.supplier_id = supplier_id or uuid.UUID("33333333-0000-0000-0000-000000000001")
        self.name = name
        self.lead_time_days = lead_time
        self.reliability_score = reliability
        self.rating = Decimal("4.9")
        self.status = "active"


class StandbySupplierProduct:
    def __init__(
        self,
        supplier_id: uuid.UUID,
        product_id: uuid.UUID,
        price: Decimal = Decimal("110.00"),
        min_qty: int = 1,
    ) -> None:
        self.supplier_id = supplier_id
        self.product_id = product_id
        self.contract_price = price
        self.minimum_order_qty = min_qty


class StandbyCarrier:
    def __init__(
        self,
        carrier_id: uuid.UUID | None = None,
        name: str = "Global Intermodal Logistics",
        modes: list[str] | None = None,
        reliability: Decimal = Decimal("95.0"),
    ) -> None:
        self.carrier_id = carrier_id or uuid.UUID("44444444-0000-0000-0000-000000000001")
        self.name = name
        self.code = "GIL-01"
        self.freight_modes = modes or ["road", "air", "ocean"]
        self.reliability_score = reliability
        self.status = "active"


class StandbyRoute:
    def __init__(
        self,
        carrier_id: uuid.UUID,
        mode: str = "road",
        transit: int = 3,
        cost: Decimal = Decimal("350.00"),
    ) -> None:
        self.route_id = uuid.uuid4()
        self.carrier_id = carrier_id
        self.origin_location = "Seattle, US"
        self.destination = "Dallas, US"
        self.freight_mode = mode
        self.transit_days = transit
        self.base_cost = cost
        self.is_active = True


# ── Database Connectivity Check ──────────────────────────────────────────────

async def is_database_connected() -> bool:
    """Quick probe to determine if the PostgreSQL engine is reachable."""
    try:
        import asyncio
        from app.core.database import engine
        from sqlalchemy import text
        async with asyncio.timeout(1.0):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


# ── Standby Session Factory ──────────────────────────────────────────────────

def create_standby_session(
    customer_id: uuid.UUID | None = None,
    items: list[dict[str, Any]] | None = None,
) -> AsyncMock:
    """Create a mock AsyncSession that gracefully resolves domain queries in dev mode."""
    session = AsyncMock()

    cust = StandbyCustomer(customer_id=customer_id)
    wh = StandbyWarehouse()
    carrier = StandbyCarrier()
    route = StandbyRoute(carrier_id=carrier.carrier_id)
    supplier = StandbySupplier()

    def _scalar(val: Any) -> MagicMock:
        m = MagicMock()
        m.scalar.return_value = val
        m.scalar_one.return_value = val
        m.scalar_one_or_none.return_value = val
        m.scalars.return_value.all.return_value = [val] if val is not None else []
        m.scalars.return_value.first.return_value = val
        m.all.return_value = [(val,)] if val is not None else []
        m.one.return_value = (val, val) if val is not None else (0, 0)
        return m

    def _scalars(vals: list[Any]) -> MagicMock:
        m = MagicMock()
        m.scalars.return_value.all.return_value = list(vals)
        m.scalars.return_value.first.return_value = vals[0] if vals else None
        m.scalar_one.return_value = vals[0] if vals else None
        m.scalar_one_or_none.return_value = vals[0] if vals else None
        m.scalar.return_value = vals[0] if vals else None
        m.all.return_value = [(v,) for v in vals]
        return m

    def mock_execute(query: Any, *args: Any, **kwargs: Any) -> MagicMock:
        q = str(query).lower()

        if "from customers" in q or "customers." in q or "customer_id" in q:
            return _scalar(cust)

        if "from transportation_routes" in q or "transportation_routes." in q:
            return _scalars([route])

        if "from carriers" in q or "carriers." in q:
            return _scalars([carrier])

        if "from warehouses" in q or "warehouses." in q:
            return _scalar(wh)

        if "from inventory" in q or "inventory." in q:
            inv = StandbyInventory(product_id=uuid.uuid4(), warehouse_id=wh.warehouse_id)
            return _scalars([inv])

        if "from supplier" in q or "supplier." in q:
            sp = StandbySupplierProduct(supplier.supplier_id, uuid.uuid4())
            m = MagicMock()
            m.all.return_value = [(sp, supplier)]
            m.scalars.return_value.all.return_value = [supplier]
            m.scalar_one_or_none.return_value = supplier
            m.scalar_one.return_value = supplier
            return m

        if "from promotions" in q or "promotions." in q:
            return _scalar(None)

        if "coalesce" in q or "avg" in q or "sum" in q or "count" in q:
            return _scalar(25)

        if "from products" in q or "products." in q or "product_id" in q:
            # Check if any known product ID appears in query string
            for pid, (pname, psku, pprice) in STANDBY_PRODUCT_DATA.items():
                if str(pid).lower() in q:
                    return _scalar(StandbyProduct(pid, pname, psku, pprice))
            # If items were provided in workflow request, resolve matching item
            if items:
                for it in items:
                    pid_str = str(it.get("product_id", "")).lower()
                    if pid_str in q or len(items) == 1:
                        try:
                            uid = uuid.UUID(pid_str)
                            return _scalar(StandbyProduct(uid))
                        except Exception:
                            pass
            return _scalar(StandbyProduct())

        return _scalar(None)

    session.execute = AsyncMock(side_effect=mock_execute)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    return session
