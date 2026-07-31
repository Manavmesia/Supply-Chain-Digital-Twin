"""
Unit tests for all 6 Phase 3 agents — no DB, no broker required.

All DB interactions are mocked via AsyncMock on session.execute().
All event publishing is mocked via publisher = None (BaseAgent skips publish).
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.graph.state import SupplyChainState

# ── Helper factories ──────────────────────────────────────────────────────────


def _make_state(**overrides) -> SupplyChainState:
    base: SupplyChainState = {
        "workflow_id": str(uuid.uuid4()),
        "correlation_id": str(uuid.uuid4()),
        "workflow_status": "received",
        "active_agents": [],
        "event_history": [],
        "decisions": [],
        "errors": [],
        "messages": [],
        "retries": {},
    }
    base.update(overrides)
    return base


def _mock_scalar(value):
    """Return an AsyncMock that mimics session.execute() returning one scalar."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    result.scalars.return_value.all.return_value = [value] if value is not None else []
    result.all.return_value = [(value, value)] if value else []
    return result


def _mock_scalars(values: list):
    result = MagicMock()
    result.scalars.return_value.all.return_value = values
    result.scalar_one_or_none.return_value = values[0] if values else None
    result.all.return_value = [(v, v) for v in values]
    return result


# ── Fake model objects ────────────────────────────────────────────────────────

def _fake_customer(active=True):
    c = MagicMock()
    c.customer_id = uuid.uuid4()
    c.name = "Acme Corp"
    c.customer_tier = "enterprise"
    c.is_active = active
    return c


def _fake_product(active=True, price=Decimal("1000.00")):
    p = MagicMock()
    p.product_id = uuid.uuid4()
    p.name = "Laptop Pro"
    p.sku = "LAP-001"
    p.unit_price = price
    p.active = active
    return p


def _fake_inventory(available=100, reserved=0, safety=20, warehouse_id=None):
    inv = MagicMock()
    inv.inventory_id = uuid.uuid4()
    inv.product_id = uuid.uuid4()
    inv.warehouse_id = warehouse_id or uuid.uuid4()
    inv.available_qty = available
    inv.reserved_qty = reserved
    inv.safety_stock = safety
    inv.reorder_point = 30
    return inv


def _fake_warehouse(capacity=10000, load=500):
    wh = MagicMock()
    wh.warehouse_id = uuid.uuid4()
    wh.name = "WH-EAST-01"
    wh.city = "Newark"
    wh.country = "US"
    wh.location = "Newark, NJ"
    wh.capacity_units = capacity
    wh.current_load = load
    wh.status = "active"
    return wh


def _fake_supplier(lead_time=7, reliability=Decimal("90.0")):
    s = MagicMock()
    s.supplier_id = uuid.uuid4()
    s.name = "TechCore Mfg"
    s.lead_time_days = lead_time
    s.reliability_score = reliability
    s.status = "active"
    return s


def _fake_supplier_product(price=Decimal("900.00"), min_qty=1):
    sp = MagicMock()
    sp.supplier_id = uuid.uuid4()
    sp.product_id = uuid.uuid4()
    sp.contract_price = price
    sp.minimum_order_qty = min_qty
    return sp


def _fake_carrier(name="FedEx", reliability=Decimal("94.5"), modes=None):
    c = MagicMock()
    c.carrier_id = uuid.uuid4()
    c.name = name
    c.code = "FEDEX"
    c.reliability_score = reliability
    c.status = "active"
    c.freight_modes = modes or ["air", "road"]
    return c


def _fake_route(mode="road", transit=5, cost=Decimal("850.00"), carrier_id=None):
    r = MagicMock()
    r.route_id = uuid.uuid4()
    r.carrier_id = carrier_id or uuid.uuid4()
    r.origin_location = "Newark, US"
    r.destination = "Los Angeles, US"
    r.freight_mode = mode
    r.transit_days = transit
    r.base_cost = cost
    r.is_active = True
    return r


# =============================================================================
# ADS-01 — Order Management Agent
# =============================================================================

class TestOrderManagementAgent:
    @pytest.mark.asyncio
    async def test_valid_order_creates_order_and_events(self):
        from app.agents.operational.order_management import OrderManagementAgent

        customer = _fake_customer()
        product = _fake_product(price=Decimal("5000.00"))
        product_id = uuid.uuid4()
        product.product_id = product_id

        session = AsyncMock()
        # customer lookup returns customer
        session.execute = AsyncMock(side_effect=[
            _mock_scalar(customer),   # customer query
            _mock_scalar(product),    # product query
        ])
        session.flush = AsyncMock()
        session.add = MagicMock()

        state = _make_state(
            order={
                "customer_id": str(customer.customer_id),
                "items": [{"product_id": str(product_id), "quantity": 2}],
                "priority": "standard",
            }
        )

        agent = OrderManagementAgent(session=session)
        result = await agent.run(state)

        assert result.get("workflow_status") != "failed", f"Unexpected failure: {result.get('decisions')}"
        assert "order" in result
        assert result["order"]["status"] == "pending"
        assert any(e["event_type"] == "OrderCreated" for e in result.get("event_history", []))
        assert "ADS-01" in result["active_agents"]

    @pytest.mark.asyncio
    async def test_unknown_customer_rejects_order(self):
        from app.agents.operational.order_management import OrderManagementAgent

        session = AsyncMock()
        session.execute = AsyncMock(return_value=_mock_scalar(None))  # customer not found

        state = _make_state(
            order={
                "customer_id": str(uuid.uuid4()),
                "items": [{"product_id": str(uuid.uuid4()), "quantity": 1}],
            }
        )

        agent = OrderManagementAgent(session=session)
        result = await agent.run(state)

        assert result["workflow_status"] == "failed"
        assert any(e["event_type"] == "OrderRejected" for e in result.get("event_history", []))

    @pytest.mark.asyncio
    async def test_inactive_customer_rejects_order(self):
        from app.agents.operational.order_management import OrderManagementAgent

        customer = _fake_customer(active=False)
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_mock_scalar(customer))

        state = _make_state(
            order={
                "customer_id": str(customer.customer_id),
                "items": [{"product_id": str(uuid.uuid4()), "quantity": 1}],
            }
        )

        agent = OrderManagementAgent(session=session)
        result = await agent.run(state)

        assert result["workflow_status"] == "failed"

    @pytest.mark.asyncio
    async def test_missing_items_rejects_order(self):
        from app.agents.operational.order_management import OrderManagementAgent

        session = AsyncMock()
        state = _make_state(order={"customer_id": str(uuid.uuid4()), "items": []})

        agent = OrderManagementAgent(session=session)
        result = await agent.run(state)

        assert result["workflow_status"] == "failed"

    @pytest.mark.asyncio
    async def test_inactive_product_rejects_order(self):
        from app.agents.operational.order_management import OrderManagementAgent

        customer = _fake_customer()
        product = _fake_product(active=False)

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[
            _mock_scalar(customer),
            _mock_scalar(product),
        ])
        session.flush = AsyncMock()
        session.add = MagicMock()

        state = _make_state(
            order={
                "customer_id": str(customer.customer_id),
                "items": [{"product_id": str(product.product_id), "quantity": 1}],
            }
        )

        agent = OrderManagementAgent(session=session)
        result = await agent.run(state)

        assert result["workflow_status"] == "failed"


# =============================================================================
# ADS-03 — Inventory Agent
# =============================================================================

class TestInventoryAgent:
    def _make_order_state(self, product_id, qty=2):
        return _make_state(
            order={
                "order_id": str(uuid.uuid4()),
                "items": [{"product_id": str(product_id), "quantity": qty}],
                "priority": "standard",
            }
        )

    @pytest.mark.asyncio
    async def test_sufficient_stock_routes_to_warehouse(self):
        from app.agents.operational.inventory import InventoryAgent

        product_id = uuid.uuid4()
        wh_id = uuid.uuid4()
        inv = _fake_inventory(available=50, reserved=10, safety=5, warehouse_id=wh_id)
        inv.product_id = product_id

        # After reservation
        inv2 = _fake_inventory(available=50, reserved=12, safety=5, warehouse_id=wh_id)
        inv2.product_id = product_id

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[
            _mock_scalars([inv]),    # availability check
            MagicMock(),             # UPDATE reserved_qty
            _mock_scalar(inv2),     # re-read after update
        ])
        session.flush = AsyncMock()

        state = self._make_order_state(product_id, qty=2)
        agent = InventoryAgent(session=session)
        result = await agent.run(state)

        assert result.get("next_node") == "warehouse"
        assert any(e["event_type"] == "InventoryAllocated" for e in result.get("event_history", []))

    @pytest.mark.asyncio
    async def test_insufficient_stock_routes_to_supplier(self):
        from app.agents.operational.inventory import InventoryAgent

        product_id = uuid.uuid4()
        session = AsyncMock()
        # No records with sufficient stock
        session.execute = AsyncMock(return_value=_mock_scalars([]))
        session.flush = AsyncMock()

        state = self._make_order_state(product_id, qty=100)
        agent = InventoryAgent(session=session)
        result = await agent.run(state)

        assert result.get("next_node") == "supplier"
        assert any(e["event_type"] == "InventoryOutOfStock" for e in result.get("event_history", []))

    @pytest.mark.asyncio
    async def test_low_stock_triggers_inventory_low_event(self):
        from app.agents.operational.inventory import InventoryAgent

        product_id = uuid.uuid4()
        wh_id = uuid.uuid4()

        # Available=25, reserve 10 → net_available=15 < safety_stock=20
        inv = _fake_inventory(available=25, reserved=0, safety=20, warehouse_id=wh_id)
        inv.product_id = product_id
        inv2 = _fake_inventory(available=25, reserved=10, safety=20, warehouse_id=wh_id)
        inv2.product_id = product_id

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[
            _mock_scalars([inv]),
            MagicMock(),
            _mock_scalar(inv2),
        ])
        session.flush = AsyncMock()

        state = self._make_order_state(product_id, qty=10)
        agent = InventoryAgent(session=session)
        result = await agent.run(state)

        # Should still allocate (stock was sufficient) but emit InventoryLow
        assert result.get("next_node") == "warehouse"
        event_types = [e["event_type"] for e in result.get("event_history", [])]
        assert "InventoryLow" in event_types
        assert "InventoryAllocated" in event_types


# =============================================================================
# ADS-04 — Warehouse Agent
# =============================================================================

class TestWarehouseAgent:
    @pytest.mark.asyncio
    async def test_assigns_warehouse_and_publishes_shipment_ready(self):
        from app.agents.operational.warehouse import WarehouseAgent

        warehouse = _fake_warehouse(capacity=10000, load=500)
        order_id = str(uuid.uuid4())

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[
            _mock_scalar(warehouse),   # warehouse lookup
            MagicMock(),               # update current_load
            MagicMock(),               # update order status
        ])
        session.flush = AsyncMock()

        state = _make_state(
            order={"order_id": order_id, "priority": "standard", "items": []},
            inventory={
                str(uuid.uuid4()): {
                    "status": "reserved",
                    "warehouse_id": str(warehouse.warehouse_id),
                    "reserved_qty": 5,
                }
            },
        )

        agent = WarehouseAgent(session=session)
        result = await agent.run(state)

        assert "warehouse" in result
        assert result["warehouse"]["warehouse_id"] == str(warehouse.warehouse_id)
        assert any(e["event_type"] == "ShipmentReady" for e in result.get("event_history", []))

    @pytest.mark.asyncio
    async def test_raises_if_no_order_id(self):
        from app.agents.operational.warehouse import WarehouseAgent

        session = AsyncMock()
        state = _make_state(order={})
        agent = WarehouseAgent(session=session)
        result = await agent.run(state)

        # BaseAgent catches the ValueError and returns failed status
        assert result["workflow_status"] == "failed"
        assert len(result["errors"]) > 0


# =============================================================================
# ADS-05 — Supplier Agent
# =============================================================================

class TestSupplierAgent:
    @pytest.mark.asyncio
    async def test_selects_best_supplier_and_creates_po(self):
        from app.agents.operational.supplier import SupplierAgent

        product_id = uuid.uuid4()
        supplier = _fake_supplier(lead_time=5, reliability=Decimal("95.0"))
        sp = _fake_supplier_product(price=Decimal("8500.00"), min_qty=1)
        sp.supplier_id = supplier.supplier_id
        sp.product_id = product_id
        warehouse = _fake_warehouse()

        # execute calls: supplier_products join, warehouse fallback
        session = AsyncMock()
        pair_result = MagicMock()
        pair_result.all.return_value = [(sp, supplier)]

        wh_result = MagicMock()
        wh_result.scalar_one_or_none.return_value = warehouse

        session.execute = AsyncMock(side_effect=[
            pair_result,   # supplier_products JOIN suppliers
        ])
        session.flush = AsyncMock()
        session.add = MagicMock()

        state = _make_state(
            order={
                "order_id": str(uuid.uuid4()),
                "items": [{"product_id": str(product_id), "quantity": 10}],
            },
            inventory={
                str(product_id): {"status": "out_of_stock", "needed": 10, "available": 0}
            },
            warehouse={"warehouse_id": str(warehouse.warehouse_id)},
            workflow_id=str(uuid.uuid4()),
        )

        agent = SupplierAgent(session=session)
        result = await agent.run(state)

        assert result["supplier"]["status"] == "selected"
        event_types = [e["event_type"] for e in result.get("event_history", [])]
        assert "SupplierSelected" in event_types
        assert "PurchaseOrderCreated" in event_types

    @pytest.mark.asyncio
    async def test_no_supplier_publishes_unavailable(self):
        from app.agents.operational.supplier import SupplierAgent

        product_id = uuid.uuid4()
        session = AsyncMock()
        no_rows = MagicMock()
        no_rows.all.return_value = []
        session.execute = AsyncMock(return_value=no_rows)
        session.flush = AsyncMock()

        state = _make_state(
            order={
                "order_id": str(uuid.uuid4()),
                "items": [{"product_id": str(product_id), "quantity": 5}],
            },
            inventory={str(product_id): {"status": "out_of_stock"}},
            warehouse={"warehouse_id": str(uuid.uuid4())},
            workflow_id=str(uuid.uuid4()),
        )

        agent = SupplierAgent(session=session)
        result = await agent.run(state)

        assert result["supplier"]["status"] == "unavailable"
        assert any(e["event_type"] == "SupplierUnavailable" for e in result.get("event_history", []))

    @pytest.mark.asyncio
    async def test_higher_reliability_wins_when_prices_equal(self):
        from app.agents.operational.supplier import SupplierAgent, _W_RELIABILITY

        product_id = uuid.uuid4()

        sup_a = _fake_supplier(lead_time=7, reliability=Decimal("95.0"))
        sup_b = _fake_supplier(lead_time=7, reliability=Decimal("80.0"))
        sp_a = _fake_supplier_product(price=Decimal("1000.00"), min_qty=1)
        sp_a.supplier_id = sup_a.supplier_id
        sp_a.product_id = product_id
        sp_b = _fake_supplier_product(price=Decimal("1000.00"), min_qty=1)
        sp_b.supplier_id = sup_b.supplier_id
        sp_b.product_id = product_id

        warehouse = _fake_warehouse()
        session = AsyncMock()
        pair_result = MagicMock()
        pair_result.all.return_value = [(sp_a, sup_a), (sp_b, sup_b)]
        session.execute = AsyncMock(return_value=pair_result)
        session.flush = AsyncMock()
        session.add = MagicMock()

        state = _make_state(
            order={
                "order_id": str(uuid.uuid4()),
                "items": [{"product_id": str(product_id), "quantity": 1}],
            },
            inventory={str(product_id): {"status": "out_of_stock"}},
            warehouse={"warehouse_id": str(warehouse.warehouse_id)},
            workflow_id=str(uuid.uuid4()),
        )

        agent = SupplierAgent(session=session)
        result = await agent.run(state)

        assert result["supplier"]["status"] == "selected"
        # The selected supplier should be sup_a (higher reliability)
        selected_event = next(
            e for e in result["event_history"] if e["event_type"] == "SupplierSelected"
        )
        assert selected_event["payload"]["supplier_name"] == sup_a.name


# =============================================================================
# ADS-06 — Transportation Agent
# =============================================================================

class TestTransportationAgent:
    @pytest.mark.asyncio
    async def test_standard_priority_picks_cheapest_route(self):
        from app.agents.operational.transportation import TransportationAgent

        carrier = _fake_carrier()
        cheap_route = _fake_route(mode="road", transit=5, cost=Decimal("800.00"))
        cheap_route.carrier_id = carrier.carrier_id
        fast_route = _fake_route(mode="air", transit=1, cost=Decimal("5000.00"))
        fast_route.carrier_id = carrier.carrier_id

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[
            _mock_scalars([carrier]),           # carriers query
            _mock_scalars([cheap_route, fast_route]),  # routes query
            MagicMock(),                        # update order status
        ])
        session.flush = AsyncMock()
        session.add = MagicMock()

        state = _make_state(
            order={"order_id": str(uuid.uuid4()), "priority": "standard", "items": []},
            warehouse={"warehouse_id": str(uuid.uuid4()), "city": "Newark", "country": "US"},
        )

        agent = TransportationAgent(session=session)
        result = await agent.run(state)

        assert "shipment" in result
        assert result["shipment"]["freight_mode"] == "road"  # cheapest = road
        event_types = [e["event_type"] for e in result.get("event_history", [])]
        assert "ShipmentCreated" in event_types
        assert "ShipmentDispatched" in event_types

    @pytest.mark.asyncio
    async def test_high_priority_picks_fastest_route(self):
        from app.agents.operational.transportation import TransportationAgent

        carrier = _fake_carrier()
        cheap_route = _fake_route(mode="road", transit=5, cost=Decimal("800.00"))
        cheap_route.carrier_id = carrier.carrier_id
        fast_route = _fake_route(mode="air", transit=1, cost=Decimal("5000.00"))
        fast_route.carrier_id = carrier.carrier_id

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[
            _mock_scalars([carrier]),
            _mock_scalars([cheap_route, fast_route]),
            MagicMock(),
        ])
        session.flush = AsyncMock()
        session.add = MagicMock()

        state = _make_state(
            order={"order_id": str(uuid.uuid4()), "priority": "high", "items": []},
            warehouse={"warehouse_id": str(uuid.uuid4()), "city": "Newark", "country": "US"},
        )

        agent = TransportationAgent(session=session)
        result = await agent.run(state)

        assert result["shipment"]["freight_mode"] == "air"  # fastest = air

    @pytest.mark.asyncio
    async def test_generates_unique_tracking_id(self):
        from app.agents.operational.transportation import TransportationAgent

        carrier = _fake_carrier()
        route = _fake_route()
        route.carrier_id = carrier.carrier_id

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[
            _mock_scalars([carrier]),
            _mock_scalars([route]),
            MagicMock(),
        ])
        session.flush = AsyncMock()
        session.add = MagicMock()

        state = _make_state(
            order={"order_id": str(uuid.uuid4()), "priority": "standard", "items": []},
            warehouse={"warehouse_id": str(uuid.uuid4()), "city": "Newark", "country": "US"},
        )

        agent = TransportationAgent(session=session)
        result = await agent.run(state)

        tracking_id = result["shipment"]["tracking_id"]
        assert tracking_id is not None
        assert len(tracking_id) > 5


# =============================================================================
# ADS-17 — CEO Agent
# =============================================================================

class TestCEOAgent:
    @pytest.mark.asyncio
    async def test_auto_approves_low_value_order(self):
        from app.agents.coordination.ceo import CEOAgent

        session = AsyncMock()
        session.execute = AsyncMock(return_value=MagicMock())
        session.flush = AsyncMock()

        state = _make_state(
            order={"order_id": str(uuid.uuid4()), "total_amount": "5000.00", "priority": "standard", "status": "in_transit"},
        )

        agent = CEOAgent(session=session)
        result = await agent.run(state)

        assert result["executive_decision"]["approved"] is True
        assert result["executive_decision"]["approval_tier"] == "auto"
        assert result["workflow_status"] == "completed"

    @pytest.mark.asyncio
    async def test_approves_mid_value_with_finance_review(self):
        from app.agents.coordination.ceo import CEOAgent

        session = AsyncMock()
        session.execute = AsyncMock(return_value=MagicMock())
        session.flush = AsyncMock()

        state = _make_state(
            order={"order_id": str(uuid.uuid4()), "total_amount": "25000.00", "priority": "standard", "status": "in_transit"},
        )

        agent = CEOAgent(session=session)
        result = await agent.run(state)

        assert result["executive_decision"]["approved"] is True
        assert result["executive_decision"]["approval_tier"] == "finance_review"

    @pytest.mark.asyncio
    async def test_sets_human_flag_for_very_high_value(self):
        from app.agents.coordination.ceo import CEOAgent

        session = AsyncMock()
        session.execute = AsyncMock(return_value=MagicMock())
        session.flush = AsyncMock()

        state = _make_state(
            order={"order_id": str(uuid.uuid4()), "total_amount": "750000.00", "priority": "standard", "status": "in_transit"},
        )

        agent = CEOAgent(session=session)
        result = await agent.run(state)

        assert result["executive_decision"]["approved"] is True
        assert result["requires_human_approval"] is True
        assert result["executive_decision"]["approval_tier"] == "human_required"

    @pytest.mark.asyncio
    async def test_denies_high_risk_workflow(self):
        from app.agents.coordination.ceo import CEOAgent

        session = AsyncMock()
        session.execute = AsyncMock(return_value=MagicMock())
        session.flush = AsyncMock()

        state = _make_state(
            order={"order_id": str(uuid.uuid4()), "total_amount": "8000.00", "priority": "standard", "status": "in_transit"},
            risk={"score": 90.0},  # > 85 threshold
        )

        agent = CEOAgent(session=session)
        result = await agent.run(state)

        assert result["executive_decision"]["approved"] is False
        assert result["workflow_status"] == "failed"

    @pytest.mark.asyncio
    async def test_denies_errored_standard_workflow(self):
        from app.agents.coordination.ceo import CEOAgent

        session = AsyncMock()
        session.execute = AsyncMock(return_value=MagicMock())
        session.flush = AsyncMock()

        state = _make_state(
            order={"order_id": str(uuid.uuid4()), "total_amount": "3000.00", "priority": "standard", "status": "in_transit"},
            errors=[{"agent": "ADS-04", "error": "warehouse not found"}],
        )

        agent = CEOAgent(session=session)
        result = await agent.run(state)

        # Standard priority + errors → denied
        assert result["executive_decision"]["approved"] is False

    @pytest.mark.asyncio
    async def test_high_priority_errors_still_approved(self):
        """Critical orders proceed even if non-critical errors exist."""
        from app.agents.coordination.ceo import CEOAgent

        session = AsyncMock()
        session.execute = AsyncMock(return_value=MagicMock())
        session.flush = AsyncMock()

        state = _make_state(
            order={"order_id": str(uuid.uuid4()), "total_amount": "3000.00", "priority": "critical", "status": "in_transit"},
            errors=[{"agent": "ADS-04", "error": "minor warning"}],
        )

        agent = CEOAgent(session=session)
        result = await agent.run(state)

        assert result["executive_decision"]["approved"] is True
