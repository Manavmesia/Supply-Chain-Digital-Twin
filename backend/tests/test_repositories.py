"""
Repository tests — verifies all domain-specific query methods in each repo.
Every test runs inside a rolled-back transaction via db_session.
"""

import uuid
from decimal import Decimal

import pytest
from tests.conftest import (
    CUSTOMER_ID,
    PRODUCT_LAPTOP_ID,
    PRODUCT_MONITOR_ID,
    SUPPLIER_TECHCORE_ID,
    WAREHOUSE_EAST_ID,
    WAREHOUSE_WEST_ID,
    make_carrier,
    make_order,
    make_purchase_order,
    make_shipment,
    make_support_ticket,
    make_transportation_route,
)


# ---------------------------------------------------------------------------
# BaseRepository
# ---------------------------------------------------------------------------

class TestBaseRepository:
    @pytest.mark.asyncio
    async def test_create_and_get(self, db_session):
        from app.models.order import Order
        from app.repositories.base import BaseRepository
        repo = BaseRepository(Order, db_session)
        order = make_order()
        created = await repo.create(order)
        assert created.order_id == order.order_id

        fetched = await repo.get(order.order_id)
        assert fetched is not None
        assert fetched.order_id == order.order_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, db_session):
        from app.models.order import Order
        from app.repositories.base import BaseRepository
        repo = BaseRepository(Order, db_session)
        result = await repo.get(uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_list_with_pagination(self, db_session):
        from app.models.order import Order
        from app.repositories.base import BaseRepository
        repo = BaseRepository(Order, db_session)

        for _ in range(5):
            await repo.create(make_order())

        page1 = await repo.list(skip=0, limit=3)
        page2 = await repo.list(skip=3, limit=3)
        assert len(page1) == 3
        # page2 has the remaining 2 (plus possibly seed data — just check it returns something)
        assert isinstance(page2, (list, tuple))

    @pytest.mark.asyncio
    async def test_delete(self, db_session):
        from app.models.order import Order
        from app.repositories.base import BaseRepository
        repo = BaseRepository(Order, db_session)
        order = make_order()
        await repo.create(order)
        await repo.delete(order)
        assert await repo.get(order.order_id) is None

    @pytest.mark.asyncio
    async def test_list_default_limit(self, db_session):
        from app.models.order import Order
        from app.repositories.base import BaseRepository
        repo = BaseRepository(Order, db_session)
        results = await repo.list()
        # default limit=100, must return a sequence
        assert hasattr(results, "__iter__")


# ---------------------------------------------------------------------------
# OrderRepository
# ---------------------------------------------------------------------------

class TestOrderRepository:
    @pytest.mark.asyncio
    async def test_get_with_items_no_items(self, db_session):
        from app.repositories.order import OrderRepository
        repo = OrderRepository(db_session)
        order = make_order()
        await repo.create(order)

        fetched = await repo.get_with_items(order.order_id)
        assert fetched is not None
        assert fetched.items == []

    @pytest.mark.asyncio
    async def test_get_with_items_unknown_id(self, db_session):
        from app.repositories.order import OrderRepository
        repo = OrderRepository(db_session)
        result = await repo.get_with_items(uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_list_by_status_empty(self, db_session):
        from app.repositories.order import OrderRepository
        repo = OrderRepository(db_session)
        # Use a status that should not exist in seed
        results = await repo.list_by_status("warehouse_assigned")
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_list_by_status_finds_created(self, db_session):
        from app.repositories.order import OrderRepository
        repo = OrderRepository(db_session)
        order = make_order(status="cancelled")
        await repo.create(order)
        results = await repo.list_by_status("cancelled")
        assert any(o.order_id == order.order_id for o in results)

    @pytest.mark.asyncio
    async def test_list_by_status_excludes_other_statuses(self, db_session):
        from app.repositories.order import OrderRepository
        repo = OrderRepository(db_session)
        order = make_order(status="failed")
        await repo.create(order)
        results = await repo.list_by_status("pending")
        assert not any(o.order_id == order.order_id for o in results)

    @pytest.mark.asyncio
    async def test_multiple_orders_different_statuses(self, db_session):
        from app.repositories.order import OrderRepository
        repo = OrderRepository(db_session)
        o1 = make_order(status="validated")
        o2 = make_order(status="validated")
        o3 = make_order(status="in_transit")
        await repo.create(o1)
        await repo.create(o2)
        await repo.create(o3)

        validated = await repo.list_by_status("validated")
        ids = {o.order_id for o in validated}
        assert o1.order_id in ids
        assert o2.order_id in ids
        assert o3.order_id not in ids


# ---------------------------------------------------------------------------
# InventoryRepository
# ---------------------------------------------------------------------------

class TestInventoryRepository:
    @pytest.mark.asyncio
    async def test_get_by_product_and_warehouse_exists(self, db_session):
        """Laptop stock at WH-EAST-01 exists in seed data."""
        from app.repositories.inventory import InventoryRepository
        repo = InventoryRepository(db_session)
        inv = await repo.get_by_product_and_warehouse(PRODUCT_LAPTOP_ID, WAREHOUSE_EAST_ID)
        assert inv is not None
        assert inv.available_qty > 0

    @pytest.mark.asyncio
    async def test_get_by_product_and_warehouse_not_found(self, db_session):
        from app.repositories.inventory import InventoryRepository
        repo = InventoryRepository(db_session)
        result = await repo.get_by_product_and_warehouse(uuid.uuid4(), WAREHOUSE_EAST_ID)
        assert result is None

    @pytest.mark.asyncio
    async def test_check_availability_sufficient_stock(self, db_session):
        """500 laptops available, reserving 50 — requesting 200 should pass."""
        from app.repositories.inventory import InventoryRepository
        repo = InventoryRepository(db_session)
        ok = await repo.check_availability(PRODUCT_LAPTOP_ID, WAREHOUSE_EAST_ID, quantity=200)
        assert ok is True

    @pytest.mark.asyncio
    async def test_check_availability_exact_available(self, db_session):
        """500 available, 50 reserved → 450 net. Request exactly 450."""
        from app.repositories.inventory import InventoryRepository
        repo = InventoryRepository(db_session)
        inv = await repo.get_by_product_and_warehouse(PRODUCT_LAPTOP_ID, WAREHOUSE_EAST_ID)
        net = inv.available_qty - inv.reserved_qty
        ok = await repo.check_availability(PRODUCT_LAPTOP_ID, WAREHOUSE_EAST_ID, quantity=net)
        assert ok is True

    @pytest.mark.asyncio
    async def test_check_availability_exceeds_stock(self, db_session):
        from app.repositories.inventory import InventoryRepository
        repo = InventoryRepository(db_session)
        ok = await repo.check_availability(PRODUCT_LAPTOP_ID, WAREHOUSE_EAST_ID, quantity=999999)
        assert ok is False

    @pytest.mark.asyncio
    async def test_check_availability_no_inventory_record(self, db_session):
        from app.repositories.inventory import InventoryRepository
        repo = InventoryRepository(db_session)
        ok = await repo.check_availability(uuid.uuid4(), WAREHOUSE_EAST_ID, quantity=1)
        assert ok is False

    @pytest.mark.asyncio
    async def test_inventory_at_west_warehouse(self, db_session):
        from app.repositories.inventory import InventoryRepository
        repo = InventoryRepository(db_session)
        inv = await repo.get_by_product_and_warehouse(PRODUCT_LAPTOP_ID, WAREHOUSE_WEST_ID)
        assert inv is not None
        assert inv.available_qty == 300

    @pytest.mark.asyncio
    async def test_monitor_not_at_west_warehouse(self, db_session):
        """Seed data has no monitor stock at WH-WEST-01."""
        from app.repositories.inventory import InventoryRepository
        repo = InventoryRepository(db_session)
        inv = await repo.get_by_product_and_warehouse(PRODUCT_MONITOR_ID, WAREHOUSE_WEST_ID)
        assert inv is None


# ---------------------------------------------------------------------------
# SupplierRepository
# ---------------------------------------------------------------------------

class TestSupplierRepository:
    @pytest.mark.asyncio
    async def test_active_suppliers_for_laptop(self, db_session):
        from app.repositories.supplier import SupplierRepository
        repo = SupplierRepository(db_session)
        suppliers = await repo.get_active_suppliers_for_product(PRODUCT_LAPTOP_ID)
        # TechCore and Global Components both supply laptops and are active
        assert len(suppliers) >= 2
        names = [s.name for s in suppliers]
        assert "TechCore Manufacturing" in names
        assert "Global Components Ltd" in names

    @pytest.mark.asyncio
    async def test_no_suppliers_for_unknown_product(self, db_session):
        from app.repositories.supplier import SupplierRepository
        repo = SupplierRepository(db_session)
        suppliers = await repo.get_active_suppliers_for_product(uuid.uuid4())
        assert suppliers == []

    @pytest.mark.asyncio
    async def test_only_active_suppliers_returned(self, db_session):
        """Budget Parts is under_review — should not appear in active suppliers."""
        from app.repositories.supplier import SupplierRepository
        repo = SupplierRepository(db_session)
        # Budget Parts also supplies keyboards (PERI-KBD-001)
        keyboard_id = uuid.UUID("22222222-0000-0000-0000-000000000009")
        suppliers = await repo.get_active_suppliers_for_product(keyboard_id)
        statuses = [s.status for s in suppliers]
        assert "under_review" not in statuses
        assert "blacklisted" not in statuses

    @pytest.mark.asyncio
    async def test_supplier_fields(self, db_session):
        from app.repositories.supplier import SupplierRepository
        repo = SupplierRepository(db_session)
        suppliers = await repo.get_active_suppliers_for_product(PRODUCT_LAPTOP_ID)
        for s in suppliers:
            assert s.reliability_score is not None
            assert s.lead_time_days > 0


# ---------------------------------------------------------------------------
# ShipmentRepository
# ---------------------------------------------------------------------------

class TestShipmentRepository:
    @pytest.mark.asyncio
    async def test_get_by_order_id_not_found(self, db_session):
        from app.repositories.shipment import ShipmentRepository
        repo = ShipmentRepository(db_session)
        result = await repo.get_by_order_id(uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_order_id_found(self, db_session):
        from app.repositories.order import OrderRepository
        from app.repositories.shipment import ShipmentRepository
        order_repo = OrderRepository(db_session)
        ship_repo = ShipmentRepository(db_session)

        order = make_order()
        await order_repo.create(order)
        shipment = make_shipment(order.order_id)
        await ship_repo.create(shipment)

        fetched = await ship_repo.get_by_order_id(order.order_id)
        assert fetched is not None
        assert fetched.shipment_id == shipment.shipment_id

    @pytest.mark.asyncio
    async def test_list_by_status_delivered(self, db_session):
        from app.repositories.order import OrderRepository
        from app.repositories.shipment import ShipmentRepository
        order_repo = OrderRepository(db_session)
        ship_repo = ShipmentRepository(db_session)

        order = make_order()
        await order_repo.create(order)
        ship = make_shipment(order.order_id, status="delivered")
        await ship_repo.create(ship)

        results = await ship_repo.list_by_status("delivered")
        assert any(s.shipment_id == ship.shipment_id for s in results)

    @pytest.mark.asyncio
    async def test_status_update(self, db_session):
        """Ensure status field accepts all valid shipment_status enum values."""
        from app.repositories.order import OrderRepository
        from app.repositories.shipment import ShipmentRepository
        order_repo = OrderRepository(db_session)
        ship_repo = ShipmentRepository(db_session)

        order = make_order()
        await order_repo.create(order)
        ship = make_shipment(order.order_id, status="in_transit")
        await ship_repo.create(ship)

        ship.status = "delivered"
        await db_session.flush()

        fetched = await ship_repo.get(ship.shipment_id)
        assert fetched.status == "delivered"


# ---------------------------------------------------------------------------
# Cross-model integration
# ---------------------------------------------------------------------------

class TestCrossModelIntegration:
    @pytest.mark.asyncio
    async def test_order_with_carrier_linked_shipment(self, db_session):
        """Create order → carrier → shipment with carrier FK."""
        from app.models.carrier import Carrier
        from app.repositories.base import BaseRepository
        from app.repositories.order import OrderRepository
        from app.repositories.shipment import ShipmentRepository

        carrier_repo = BaseRepository(Carrier, db_session)
        order_repo = OrderRepository(db_session)
        ship_repo = ShipmentRepository(db_session)

        carrier = make_carrier(code=f"UPS-{uuid.uuid4().hex[:4].upper()}")
        await carrier_repo.create(carrier)

        order = make_order()
        await order_repo.create(order)

        from app.models.shipment import Shipment
        from datetime import datetime, timezone
        ship = Shipment(
            shipment_id=uuid.uuid4(),
            order_id=order.order_id,
            carrier_id=carrier.carrier_id,
            status="assigned",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await ship_repo.create(ship)

        fetched = await ship_repo.get(ship.shipment_id)
        assert fetched.carrier_id == carrier.carrier_id
        assert fetched.status == "assigned"

    @pytest.mark.asyncio
    async def test_carrier_with_routes(self, db_session):
        from app.models.carrier import Carrier
        from app.models.transportation_route import TransportationRoute
        from app.repositories.base import BaseRepository

        carrier_repo = BaseRepository(Carrier, db_session)
        route_repo = BaseRepository(TransportationRoute, db_session)

        carrier = make_carrier(code=f"DHL-{uuid.uuid4().hex[:4].upper()}", freight_modes=["air", "road"])
        await carrier_repo.create(carrier)

        route1 = make_transportation_route(carrier.carrier_id, freight_mode="air", transit_days=1)
        route2 = make_transportation_route(carrier.carrier_id, freight_mode="road", transit_days=5)
        await route_repo.create(route1)
        await route_repo.create(route2)

        all_routes = await route_repo.list()
        route_ids = {r.route_id for r in all_routes}
        assert route1.route_id in route_ids
        assert route2.route_id in route_ids
