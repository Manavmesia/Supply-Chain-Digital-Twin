"""Standby in-memory session provider for resilient multi-agent execution when PostgreSQL is offline."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import structlog

from app.core import persistence

logger = structlog.get_logger(__name__)


# ── Standby Domain Objects ───────────────────────────────────────────────────

from app.core.catalog import CUSTOMER_MAP as STANDBY_CUSTOMERS, PRODUCT_MAP as STANDBY_PRODUCT_DATA


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
        inventory_id: uuid.UUID | None = None,
    ) -> None:
        self.inventory_id = inventory_id or uuid.uuid4()
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

        # Extract any bound parameters / UUIDs
        param_uuids: set[str] = set()
        if hasattr(query, "compile"):
            try:
                for v in query.compile().params.values():
                    if isinstance(v, uuid.UUID):
                        param_uuids.add(str(v).lower())
                    elif isinstance(v, str):
                        param_uuids.add(v.lower())
            except Exception:
                pass
        for a in args:
            if isinstance(a, dict):
                for v in a.values():
                    param_uuids.add(str(v).lower())
        for v in kwargs.values():
            param_uuids.add(str(v).lower())

        if "update inventory" in q:
            try:
                compile_params = query.compile().params if hasattr(query, "compile") else {}
                p_id = None
                w_id = None
                qty_val = 0
                for k, v in compile_params.items():
                    if "product_id" in k:
                        p_id = str(v)
                    elif "warehouse_id" in k:
                        w_id = str(v)
                    elif "reserved_qty" in k and isinstance(v, (int, float)):
                        qty_val = int(v)
                if p_id:
                    persistence.reserve_inventory_units(p_id, qty_val, w_id)
            except Exception as e:
                logger.warning("Failed to execute live standby update inventory", error=str(e))
            m = MagicMock()
            m.rowcount = 1
            return m

        if "from customers" in q or "customers." in q or "customer_id" in q:
            try:
                target_cid = None
                for cid in param_uuids:
                    if cid in STANDBY_CUSTOMERS or len(cid) == 36:
                        target_cid = cid
                        break
                if not target_cid and customer_id:
                    target_cid = str(customer_id)
                if target_cid:
                    with persistence._get_connection() as conn:
                        row = conn.execute(
                            "SELECT customer_id, name, customer_tier, email, is_active FROM customers WHERE customer_id = ?",
                            (target_cid,)
                        ).fetchone()
                        if row:
                            return _scalar(StandbyCustomer(
                                customer_id=row["customer_id"],
                                name=row["name"],
                                tier=row["customer_tier"],
                                is_active=bool(row["is_active"]),
                            ))
            except Exception:
                pass
            for cid in param_uuids:
                if cid in STANDBY_CUSTOMERS:
                    return _scalar(StandbyCustomer(customer_id=cid))
            if customer_id:
                return _scalar(StandbyCustomer(customer_id=customer_id))
            return _scalar(cust)

        if "from transportation_routes" in q or "transportation_routes." in q:
            return _scalars([route])

        if "from carriers" in q or "carriers." in q:
            return _scalars([carrier])

        if "from warehouses" in q or "warehouses." in q:
            return _scalar(wh)

        if "from inventory" in q or "inventory." in q:
            target_pid = None
            for pid in param_uuids:
                try:
                    target_pid = uuid.UUID(pid)
                    break
                except Exception:
                    pass

            try:
                with persistence._get_connection() as conn:
                    if target_pid:
                        rows = conn.execute(
                            "SELECT inventory_id, product_id, warehouse_id, available_qty, reserved_qty, safety_stock FROM inventory WHERE product_id = ?",
                            (str(target_pid),)
                        ).fetchall()
                    else:
                        rows = conn.execute(
                            "SELECT inventory_id, product_id, warehouse_id, available_qty, reserved_qty, safety_stock FROM inventory"
                        ).fetchall()
                    if rows:
                        inv_objs = [
                            StandbyInventory(
                                product_id=uuid.UUID(r["product_id"]),
                                warehouse_id=uuid.UUID(r["warehouse_id"]),
                                available=int(r["available_qty"]),
                                reserved=int(r["reserved_qty"]),
                                safety=int(r["safety_stock"]),
                                inventory_id=uuid.UUID(r["inventory_id"]),
                            )
                            for r in rows
                        ]
                        return _scalars(inv_objs)
            except Exception as e:
                logger.warning("Failed to query live inventory for standby session", error=str(e))

            inv = StandbyInventory(product_id=target_pid or uuid.uuid4(), warehouse_id=wh.warehouse_id)
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
            try:
                target_pid = None
                for pid in param_uuids:
                    if pid in STANDBY_PRODUCT_DATA or len(pid) == 36:
                        target_pid = pid
                        break
                if target_pid:
                    with persistence._get_connection() as conn:
                        row = conn.execute(
                            "SELECT product_id, sku, name, unit_price, active FROM products WHERE product_id = ?",
                            (target_pid,)
                        ).fetchone()
                        if row:
                            return _scalar(StandbyProduct(
                                product_id=row["product_id"],
                                name=row["name"],
                                sku=row["sku"],
                                price=Decimal(str(row["unit_price"])),
                                active=bool(row["active"]),
                            ))
            except Exception:
                pass
            for pid in param_uuids:
                if pid in STANDBY_PRODUCT_DATA:
                    return _scalar(StandbyProduct(product_id=pid))
            for pid, (pname, psku, pprice) in STANDBY_PRODUCT_DATA.items():
                if str(pid).lower() in q:
                    return _scalar(StandbyProduct(pid, pname, psku, pprice))
            if items:
                for it in items:
                    pid_str = str(it.get("product_id", "")).lower()
                    if pid_str in param_uuids or pid_str in q:
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
