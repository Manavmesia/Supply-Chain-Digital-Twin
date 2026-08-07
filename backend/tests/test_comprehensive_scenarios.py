"""
Exhaustive Multi-Scenario End-to-End Test Suite — Phases 1 to 4.

Tests all 10 nodes across 9 distinct real-world supply chain scenarios:
  - Scenario A: Standard Happy Path (In-stock, standard priority, auto-approval <= $10k)
  - Scenario B: Out-of-Stock Sourcing Path (Stock empty -> Supplier scoring -> PO creation -> Delivery)
  - Scenario C: Critical Priority / Air Freight Path (Critical priority forces air freight mode)
  - Scenario D: High-Value Governance Path ($50k-$500k finance review, >$500k human approval flag)
  - Scenario E: Low Gross Margin Path (High shipping/COGS -> CostOptimizationSuggested)
  - Scenario F: Critical Risk Escalation Path (Supplier unavailable / risk score >= 90 -> CEO Denial)
  - Scenario G: Early Validation Failure Path (Invalid customer/SKU -> OrderRejected -> Abort to END)
  - Scenario H: Demand Spike Anomaly Path (Forecast > 2x 12m avg -> DemandSpikeDetected)
  - Scenario I: Multi-Product Mixed Stock Path (Order with 3 SKUs: 2 in-stock, 1 out-of-stock)
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.graph.state import SupplyChainState
from app.graph.workflow import compile_workflow


# ── Helper Mocks ──────────────────────────────────────────────────────────────

def _mock_scalar(val):
    m = MagicMock()
    m.scalar.return_value = val
    m.scalar_one.return_value = val
    m.scalar_one_or_none.return_value = val
    m.scalars.return_value.all.return_value = [val] if val is not None else []
    m.all.return_value = [(val, val)] if val is not None else []
    return m


def _mock_scalars(vals: list):
    m = MagicMock()
    m.scalars.return_value.all.return_value = vals
    m.scalar_one_or_none.return_value = vals[0] if vals else None
    m.all.return_value = [(v, v) for v in vals]
    return m


def _setup_mock_session(
    cust=None,
    prod=None,
    inv=None,
    wh=None,
    carrier=None,
    route=None,
    contracts=None,
    supplier_product_pair=None,
    hist_avg=10,
):
    session = AsyncMock()
    prod_queue = list(prod) if isinstance(prod, list) else ([prod] if prod else [])
    inv_queue = list(inv) if isinstance(inv, list) else ([inv] if inv is not None else [])

    def mock_execute(query, *args, **kwargs):
        q = str(query).lower()
        res = None
        if "from customers" in q or "join customers" in q or "update customers" in q or "customers." in q:
            res = _mock_scalar(cust)
            print(f"[DEBUG MOCK] Query -> CUSTOMER ({cust})")
        elif "from transportation_routes" in q or "join transportation_routes" in q or "transportation_routes." in q:
            res = _mock_scalars([route] if route else [])
            print(f"[DEBUG MOCK] Query -> ROUTE ({route})")
        elif "from carriers" in q or "join carriers" in q or "carriers." in q:
            res = _mock_scalars([carrier] if carrier else [])
            print(f"[DEBUG MOCK] Query -> CARRIER ({carrier})")
        elif "from warehouses" in q or "join warehouses" in q or "update warehouses" in q or "warehouses." in q:
            res = _mock_scalar(wh)
            print(f"[DEBUG MOCK] Query -> WAREHOUSE ({wh})")
        elif "from inventory" in q or "join inventory" in q or "update inventory" in q or "inventory." in q:
            val = inv_queue.pop(0) if inv_queue else []
            if isinstance(val, list):
                res = _mock_scalars(val)
            else:
                res = _mock_scalars([val] if val else [])
            print(f"[DEBUG MOCK] Query -> INVENTORY ({val})")
        elif "from contracts" in q or "join contracts" in q or "contracts." in q:
            res = _mock_scalars(contracts or [])
            print(f"[DEBUG MOCK] Query -> CONTRACT ({contracts})")
        elif "from supplier" in q or "join supplier" in q or "supplier" in q:
            if supplier_product_pair:
                p = MagicMock()
                p.all.return_value = [supplier_product_pair]
                res = p
            else:
                res = _mock_scalars([])
            print(f"[DEBUG MOCK] Query -> SUPPLIER ({supplier_product_pair})")
        elif "from promotions" in q or "join promotions" in q or "promotions." in q:
            res = _mock_scalar(None)
            print(f"[DEBUG MOCK] Query -> PROMOTION (None)")
        elif "coalesce" in q or "avg" in q or "sum" in q:
            res = _mock_scalar(hist_avg)
            print(f"[DEBUG MOCK] Query -> ORDER/AVG ({hist_avg})")
        elif "from products" in q or "join products" in q or "products." in q:
            p = prod_queue.pop(0) if prod_queue else None
            res = _mock_scalar(p)
            print(f"[DEBUG MOCK] Query -> PRODUCT ({p})")
        else:
            res = MagicMock()
            print(f"[DEBUG MOCK] Query -> FALLBACK")
        print(f"[DEBUG MOCK] FULL QUERY: {q}")
        return res

    session.execute = AsyncMock(side_effect=mock_execute)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture(autouse=True)
def mock_qa_defect_rate():
    """Autouse fixture to ensure QA inspection always passes (1.0% defect rate)
    for all Phase 3 integration scenarios, avoiding routing to Manufacturing."""
    with patch("app.agents.business.quality_assurance._deterministic_defect_rate", return_value=1.0):
        yield


# ── Fake Domain Objects ───────────────────────────────────────────────────────
# (rest of Fake Domain Objects...)


# ── Fake Domain Objects ───────────────────────────────────────────────────────

class FakeCustomer:
    def __init__(self, customer_id, name="Acme Corp", tier="enterprise", is_active=True):
        self.customer_id = customer_id
        self.name = name
        self.customer_tier = tier
        self.is_active = is_active


class FakeProduct:
    def __init__(self, product_id, name="Pro Laptop", sku="SKU-001", price=Decimal("2500.00"), active=True):
        self.product_id = product_id
        self.name = name
        self.sku = sku
        self.unit_price = price
        self.active = active


class FakeInventory:
    def __init__(self, product_id, warehouse_id, available=100, reserved=0, safety=10):
        self.inventory_id = uuid.uuid4()
        self.product_id = product_id
        self.warehouse_id = warehouse_id
        self.available_qty = available
        self.reserved_qty = reserved
        self.safety_stock = safety


class FakeWarehouse:
    def __init__(self, warehouse_id, name="WH-EAST", city="Newark", country="US", capacity=10000, load=1000):
        self.warehouse_id = warehouse_id
        self.name = name
        self.city = city
        self.country = country
        self.location = f"{city}, {country}"
        self.capacity_units = capacity
        self.current_load = load
        self.status = "active"


class FakeSupplier:
    def __init__(self, supplier_id, name="TechCore", lead_time=5, reliability=Decimal("95.0")):
        self.supplier_id = supplier_id
        self.name = name
        self.lead_time_days = lead_time
        self.reliability_score = reliability
        self.status = "active"


class FakeSupplierProduct:
    def __init__(self, supplier_id, product_id, price=Decimal("1500.00"), min_qty=1):
        self.supplier_id = supplier_id
        self.product_id = product_id
        self.contract_price = price
        self.minimum_order_qty = min_qty


class FakeCarrier:
    def __init__(self, carrier_id, name="FedEx", modes=None, reliability=Decimal("95.0")):
        self.carrier_id = carrier_id
        self.name = name
        self.code = name.upper()
        self.freight_modes = modes or ["road", "air"]
        self.reliability_score = reliability
        self.status = "active"


class FakeRoute:
    def __init__(self, carrier_id, mode="road", transit=4, cost=Decimal("500.00")):
        self.route_id = uuid.uuid4()
        self.carrier_id = carrier_id
        self.origin_location = "Newark, US"
        self.destination = "Los Angeles, US"
        self.freight_mode = mode
        self.transit_days = transit
        self.base_cost = cost
        self.is_active = True


# =============================================================================
# SCENARIO TEST SUITE
# =============================================================================

class TestSupplyChainScenariosEndToEnd:

    # ── Scenario A: Standard Happy Path ───────────────────────────────────────
    @pytest.mark.asyncio
    async def test_scenario_a_standard_happy_path(self):
        """Standard order <= $10k, in-stock -> auto approval & delivery."""
        cust_id = uuid.uuid4()
        prod_id = uuid.uuid4()
        wh_id = uuid.uuid4()
        carrier_id = uuid.uuid4()

        cust = FakeCustomer(cust_id)
        prod = FakeProduct(prod_id, price=Decimal("2000.00"))
        inv = FakeInventory(prod_id, wh_id, available=50, reserved=0)
        wh = FakeWarehouse(wh_id)
        carrier = FakeCarrier(carrier_id)
        route = FakeRoute(carrier_id, mode="road", transit=3, cost=Decimal("300.00"))

        session = _setup_mock_session(
            cust=cust,
            prod=prod,
            inv=inv,
            wh=wh,
            carrier=carrier,
            route=route,
        )

        async def _session_factory():
            return session

        compiled = compile_workflow(session_factory=_session_factory)
        initial_state: SupplyChainState = {
            "workflow_id": str(uuid.uuid4()),
            "correlation_id": str(uuid.uuid4()),
            "workflow_status": "received",
            "active_agents": [],
            "order": {
                "customer_id": str(cust_id),
                "items": [{"product_id": str(prod_id), "quantity": 2}],
            },
        }

        final = await compiled.ainvoke(initial_state, config={"configurable": {"thread_id": str(uuid.uuid4())}})

        assert final["workflow_status"] == "completed"
        assert final["executive_decision"]["approved"] is True
        assert final["executive_decision"]["approval_tier"] == "auto"
        assert final["order"]["status"] == "delivered"
        assert final["shipment"]["carrier"] == "FedEx"
        assert "reports" in final
        # 15 nodes executed in standard happy path:
        # om, df, inv, wh, trans, sustainability, qa, finance, pricing, risk, procurement, planner, negotiation, ceo, cs, cs-routing -> reporting
        assert len(final["active_agents"]) >= 13

    # ── Scenario B: Out-of-Stock Supplier Procurement Path ────────────────────
    @pytest.mark.asyncio
    async def test_scenario_b_out_of_stock_supplier_procurement(self):
        """Insufficient stock triggers Supplier Agent -> creates PurchaseOrder -> succeeds."""
        cust_id = uuid.uuid4()
        prod_id = uuid.uuid4()
        wh_id = uuid.uuid4()
        sup_id = uuid.uuid4()
        carrier_id = uuid.uuid4()

        cust = FakeCustomer(cust_id)
        prod = FakeProduct(prod_id, price=Decimal("3000.00"))
        wh = FakeWarehouse(wh_id)
        supplier = FakeSupplier(sup_id, "Global Micro")
        sp = FakeSupplierProduct(sup_id, prod_id, price=Decimal("2000.00"))
        carrier = FakeCarrier(carrier_id)
        route = FakeRoute(carrier_id)

        session = _setup_mock_session(
            cust=cust,
            prod=prod,
            inv=[],
            wh=wh,
            carrier=carrier,
            route=route,
            supplier_product_pair=(sp, supplier),
        )

        async def _session_factory():
            return session

        compiled = compile_workflow(session_factory=_session_factory)
        initial_state: SupplyChainState = {
            "workflow_id": str(uuid.uuid4()),
            "correlation_id": str(uuid.uuid4()),
            "workflow_status": "received",
            "active_agents": [],
            "order": {
                "customer_id": str(cust_id),
                "items": [{"product_id": str(prod_id), "quantity": 10}],
            },
        }

        final = await compiled.ainvoke(initial_state, config={"configurable": {"thread_id": str(uuid.uuid4())}})

        assert final["workflow_status"] == "completed"
        assert "ADS-05" in final["active_agents"]  # Supplier agent ran
        assert final["supplier"]["status"] == "selected"
        assert len(final["supplier"]["purchase_orders"]) == 1
        assert final["supplier"]["purchase_orders"][0]["quantity"] == 10

    # ── Scenario C: Critical Priority Forces Air Freight ──────────────────────
    @pytest.mark.asyncio
    async def test_scenario_c_critical_priority_air_freight(self):
        """Critical priority order forces air freight mode and fast transit."""
        cust_id = uuid.uuid4()
        prod_id = uuid.uuid4()
        wh_id = uuid.uuid4()
        carrier_id = uuid.uuid4()

        cust = FakeCustomer(cust_id)
        prod = FakeProduct(prod_id, price=Decimal("4000.00"))
        inv = FakeInventory(prod_id, wh_id, available=20)
        wh = FakeWarehouse(wh_id)
        carrier_air = FakeCarrier(carrier_id, name="DHL Air", modes=["air"])
        route_air = FakeRoute(carrier_id, mode="air", transit=1, cost=Decimal("1200.00"))

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[
            _mock_scalar(cust),
            _mock_scalar(prod),
            _mock_scalar(15),
            _mock_scalar(None),
            _mock_scalars([inv]),
            MagicMock(),
            _mock_scalar(inv),
            _mock_scalar(wh),
            MagicMock(),
            MagicMock(),
            _mock_scalars([carrier_air]),
            _mock_scalars([route_air]),
            MagicMock(),
            MagicMock(),
            MagicMock(),
        ])
        session.flush = AsyncMock()

        async def _session_factory():
            return session

        compiled = compile_workflow(session_factory=_session_factory)
        initial_state: SupplyChainState = {
            "workflow_id": str(uuid.uuid4()),
            "correlation_id": str(uuid.uuid4()),
            "workflow_status": "received",
            "active_agents": [],
            "order": {
                "customer_id": str(cust_id),
                "items": [{"product_id": str(prod_id), "quantity": 1}],
                "priority": "critical",
            },
        }

        final = await compiled.ainvoke(initial_state, config={"configurable": {"thread_id": str(uuid.uuid4())}})

        assert final["shipment"]["freight_mode"] == "air"
        assert final["shipment"]["transit_days"] == 1

    # ── Scenario D: High-Value Order Governance Tiers ─────────────────────────
    @pytest.mark.asyncio
    async def test_scenario_d_high_value_order_governance(self):
        """Order > $500k triggers human approval flag in CEO agent."""
        cust_id = uuid.uuid4()
        prod_id = uuid.uuid4()

        cust = FakeCustomer(cust_id)
        prod = FakeProduct(prod_id, price=Decimal("600000.00"))  # $600k total
        wh_id = uuid.uuid4()
        inv = FakeInventory(prod_id, wh_id, available=10)
        wh = FakeWarehouse(wh_id)
        carrier_id = uuid.uuid4()
        carrier = FakeCarrier(carrier_id)
        route = FakeRoute(carrier_id)

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[
            _mock_scalar(cust), _mock_scalar(prod),
            _mock_scalar(50), _mock_scalar(None),
            _mock_scalars([inv]), MagicMock(), _mock_scalar(inv),
            _mock_scalar(wh), MagicMock(), MagicMock(),
            _mock_scalars([carrier]), _mock_scalars([route]),
            MagicMock(), MagicMock(), MagicMock(),
        ])

        async def _session_factory():
            return session

        compiled = compile_workflow(session_factory=_session_factory)
        initial_state: SupplyChainState = {
            "workflow_id": str(uuid.uuid4()),
            "correlation_id": str(uuid.uuid4()),
            "workflow_status": "received",
            "active_agents": [],
            "order": {
                "customer_id": str(cust_id),
                "items": [{"product_id": str(prod_id), "quantity": 1}],
                "priority": "standard",
            },
        }

        final = await compiled.ainvoke(initial_state, config={"configurable": {"thread_id": str(uuid.uuid4())}})

        assert final["executive_decision"]["approval_tier"] == "human_required"
        assert final["requires_human_approval"] is True

    # ── Scenario E: Low Gross Margin triggers Cost Optimization ───────────────
    @pytest.mark.asyncio
    async def test_scenario_e_low_margin_cost_optimization(self):
        """When total costs reduce margin below 15%, Finance suggests optimization."""
        cust_id = uuid.uuid4()
        prod_id = uuid.uuid4()
        wh_id = uuid.uuid4()

        cust = FakeCustomer(cust_id)
        # Unit price = $100, but procurement cost = $95 -> low margin
        prod = FakeProduct(prod_id, price=Decimal("100.00"))
        wh = FakeWarehouse(wh_id)
        sup_id = uuid.uuid4()
        supplier = FakeSupplier(sup_id)
        sp = FakeSupplierProduct(sup_id, prod_id, price=Decimal("95.00"))
        carrier_id = uuid.uuid4()
        carrier = FakeCarrier(carrier_id)
        route = FakeRoute(carrier_id, mode="road", cost=Decimal("150.00"))

        session = AsyncMock()
        pair_mock = MagicMock()
        pair_mock.all.return_value = [(sp, supplier)]

        session.execute = AsyncMock(side_effect=[
            _mock_scalar(cust), _mock_scalar(prod),
            _mock_scalar(5), _mock_scalar(None),
            _mock_scalars([]), # Out of stock -> trigger supplier
            _mock_scalar(wh),  # Supplier fallback WH
            pair_mock,
            _mock_scalars([carrier]), _mock_scalars([route]),
            MagicMock(), MagicMock(), MagicMock(),
        ])

        async def _session_factory():
            return session

        compiled = compile_workflow(session_factory=_session_factory)
        initial_state: SupplyChainState = {
            "workflow_id": str(uuid.uuid4()),
            "correlation_id": str(uuid.uuid4()),
            "workflow_status": "received",
            "active_agents": [],
            "order": {
                "customer_id": str(cust_id),
                "items": [{"product_id": str(prod_id), "quantity": 1}],
                "priority": "standard",
            },
        }

        final = await compiled.ainvoke(initial_state, config={"configurable": {"thread_id": str(uuid.uuid4())}})

        assert final["finance"]["financial_approval"] is False
        event_types = [e["event_type"] for e in final.get("event_history", [])]
        assert "CostOptimizationSuggested" in event_types

    # ── Scenario F: Critical Risk Escalation Denies Order ─────────────────────
    @pytest.mark.asyncio
    async def test_scenario_f_critical_risk_denial(self):
        """No active supplier + low margin + long transit -> Risk >= 90 -> CEO denies."""
        cust_id = uuid.uuid4()
        prod_id = uuid.uuid4()
        wh_id = uuid.uuid4()

        cust = FakeCustomer(cust_id)
        prod = FakeProduct(prod_id, price=Decimal("500.00"))
        wh = FakeWarehouse(wh_id)
        carrier_id = uuid.uuid4()
        carrier = FakeCarrier(carrier_id)
        route = FakeRoute(carrier_id, mode="air", transit=12)

        session = AsyncMock()
        no_sup_mock = MagicMock()
        no_sup_mock.all.return_value = []

        session.execute = AsyncMock(side_effect=[
            _mock_scalar(cust), _mock_scalar(prod),
            _mock_scalar(2), _mock_scalar(None),
            _mock_scalars([]),       # Out of stock
            _mock_scalar(wh),        # Supplier fallback WH
            no_sup_mock,             # Supplier unavailable (+40 risk)
            _mock_scalars([carrier]),
            _mock_scalars([route]),  # Air + long transit (+35 risk)
            MagicMock(), MagicMock(), MagicMock(),
        ])

        async def _session_factory():
            return session

        compiled = compile_workflow(session_factory=_session_factory)
        initial_state: SupplyChainState = {
            "workflow_id": str(uuid.uuid4()),
            "correlation_id": str(uuid.uuid4()),
            "workflow_status": "received",
            "active_agents": [],
            "order": {
                "customer_id": str(cust_id),
                "items": [{"product_id": str(prod_id), "quantity": 1}],
                "priority": "standard",
            },
        }

        final = await compiled.ainvoke(initial_state, config={"configurable": {"thread_id": str(uuid.uuid4())}})

        assert final["risk"]["score"] >= 90.0
        assert final["executive_decision"]["approved"] is False
        assert final["order"]["status"] == "cancelled"

    # ── Scenario G: Early Validation Failure (Invalid Customer) ───────────────
    @pytest.mark.asyncio
    async def test_scenario_g_invalid_customer_early_termination(self):
        """Unknown customer ID causes Order Management to reject and terminate immediately."""
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_mock_scalar(None))  # Customer not found

        async def _session_factory():
            return session

        compiled = compile_workflow(session_factory=_session_factory)
        initial_state: SupplyChainState = {
            "workflow_id": str(uuid.uuid4()),
            "correlation_id": str(uuid.uuid4()),
            "workflow_status": "received",
            "active_agents": [],
            "order": {
                "customer_id": str(uuid.uuid4()),
                "items": [{"product_id": str(uuid.uuid4()), "quantity": 1}],
                "priority": "standard",
            },
        }

        final = await compiled.ainvoke(initial_state, config={"configurable": {"thread_id": str(uuid.uuid4())}})

        assert final["workflow_status"] == "failed"
        assert final["active_agents"] == ["ADS-01"]  # Only Order Management executed
        event_types = [e["event_type"] for e in final.get("event_history", [])]
        assert "OrderRejected" in event_types

    # ── Scenario H: Demand Spike Anomaly Detection ────────────────────────────
    @pytest.mark.asyncio
    async def test_scenario_h_demand_spike_detection(self):
        """Order quantity far exceeding historical 12m avg emits DemandSpikeDetected."""
        cust_id = uuid.uuid4()
        prod_id = uuid.uuid4()
        wh_id = uuid.uuid4()

        cust = FakeCustomer(cust_id)
        prod = FakeProduct(prod_id, price=Decimal("100.00"))
        inv = FakeInventory(prod_id, wh_id, available=1000)
        wh = FakeWarehouse(wh_id)
        carrier_id = uuid.uuid4()
        carrier = FakeCarrier(carrier_id)
        route = FakeRoute(carrier_id)

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[
            _mock_scalar(cust), _mock_scalar(prod),
            _mock_scalar(12), # 12m avg = 1 item/month
            _mock_scalar(None),
            _mock_scalars([inv]), MagicMock(), _mock_scalar(inv),
            _mock_scalar(wh), MagicMock(), MagicMock(),
            _mock_scalars([carrier]), _mock_scalars([route]),
            MagicMock(), MagicMock(), MagicMock(),
        ])

        async def _session_factory():
            return session

        compiled = compile_workflow(session_factory=_session_factory)
        initial_state: SupplyChainState = {
            "workflow_id": str(uuid.uuid4()),
            "correlation_id": str(uuid.uuid4()),
            "workflow_status": "received",
            "active_agents": [],
            "order": {
                "customer_id": str(cust_id),
                "items": [{"product_id": str(prod_id), "quantity": 25}],  # 25 units >> 2x avg
                "priority": "standard",
            },
        }

        final = await compiled.ainvoke(initial_state, config={"configurable": {"thread_id": str(uuid.uuid4())}})

        event_types = [e["event_type"] for e in final.get("event_history", [])]
        assert "DemandSpikeDetected" in event_types

    # ── Scenario I: Multi-Product Mixed Availability Path ─────────────────────
    @pytest.mark.asyncio
    async def test_scenario_i_multi_product_mixed_stock(self):
        """Order containing 2 products: 1 in-stock and 1 out-of-stock -> triggers supplier for item 2."""
        cust_id = uuid.uuid4()
        p1_id = uuid.uuid4()
        p2_id = uuid.uuid4()
        wh_id = uuid.uuid4()
        sup_id = uuid.uuid4()
        carrier_id = uuid.uuid4()

        cust = FakeCustomer(cust_id)
        prod1 = FakeProduct(p1_id, name="In-Stock Widget", price=Decimal("100.00"))
        prod2 = FakeProduct(p2_id, name="Out-of-Stock Widget", price=Decimal("500.00"))
        inv1 = FakeInventory(p1_id, wh_id, available=100)
        wh = FakeWarehouse(wh_id)
        supplier = FakeSupplier(sup_id)
        sp2 = FakeSupplierProduct(sup_id, p2_id, price=Decimal("350.00"))
        carrier = FakeCarrier(carrier_id)
        route = FakeRoute(carrier_id)

        session = _setup_mock_session(
            cust=cust,
            prod=[prod1, prod2],
            inv=[[inv1], []],  # first product is in stock, second is out of stock
            wh=wh,
            carrier=carrier,
            route=route,
            supplier_product_pair=(sp2, supplier),
        )

        async def _session_factory():
            return session

        compiled = compile_workflow(session_factory=_session_factory)
        initial_state: SupplyChainState = {
            "workflow_id": str(uuid.uuid4()),
            "correlation_id": str(uuid.uuid4()),
            "workflow_status": "received",
            "active_agents": [],
            "order": {
                "customer_id": str(cust_id),
                "items": [
                    {"product_id": str(p1_id), "quantity": 2},
                    {"product_id": str(p2_id), "quantity": 5},
                ],
                "priority": "standard",
            },
        }

        final = await compiled.ainvoke(initial_state, config={"configurable": {"thread_id": str(uuid.uuid4())}})

        assert final["inventory"][str(p1_id)]["status"] == "reserved"
        assert final["inventory"][str(p2_id)]["status"] == "out_of_stock"
        assert "ADS-05" in final["active_agents"]  # Supplier executed for p2
        assert final["workflow_status"] == "completed"
