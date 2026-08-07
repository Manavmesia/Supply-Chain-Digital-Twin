"""
Dedicated E2E integration test suite for all Phase 4 scenarios.
Runs the complete multi-agent workflow graph (15+ nodes) without a real DB or broker,
asserting detailed state transitions and business intelligence actions for every scenario.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.graph.state import SupplyChainState
from app.graph.workflow import compile_workflow
from tests.test_comprehensive_scenarios import (
    FakeCarrier,
    FakeCustomer,
    FakeInventory,
    FakeProduct,
    FakeRoute,
    FakeSupplier,
    FakeSupplierProduct,
    FakeWarehouse,
    _setup_mock_session,
)


def _event_types(result: dict) -> list[str]:
    return [e["event_type"] for e in result.get("event_history", [])]


class TestPhase4ScenariosIntegration:

    # ── Scenario A: Standard Happy Path (Stock OK, Passes QA, Price Stable) ────
    @pytest.mark.asyncio
    @patch("app.agents.business.quality_assurance._deterministic_defect_rate", return_value=1.0)
    async def test_scenario_a_standard_happy_path(self, mock_rate):
        """Standard order, in-stock -> auto approval & delivery, sustainability road freight."""
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
            cust=cust, prod=prod, inv=inv, wh=wh, carrier=carrier, route=route
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
        assert final["order"]["status"] == "delivered"
        assert final["shipment"]["freight_mode"] == "road"
        assert final["sustainability"]["sustainability_score"] > 90.0
        assert final["quality"]["status"] == "passed"
        assert final["pricing"]["results"][0]["recommendation"] == "stable"
        assert final["planning"]["remanufacture_required"] is False
        assert "ADS-15" in final["active_agents"]  # Planner ran
        assert "ADS-16" in final["active_agents"]  # Negotiation ran

    # ── Scenario B: Out of Stock -> Supplier Procurement ─────────────────────
    @pytest.mark.asyncio
    @patch("app.agents.business.quality_assurance._deterministic_defect_rate", return_value=1.0)
    async def test_scenario_b_out_of_stock_supplier_procurement(self, mock_rate):
        """Insufficient stock -> selects supplier, creates PO, runs negotiation."""
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
        assert "ADS-05" in final["active_agents"]
        assert final["supplier"]["status"] == "selected"
        assert len(final["supplier"]["purchase_orders"]) == 1
        assert final["supplier"]["purchase_orders"][0]["quantity"] == 10
        assert final["negotiation"]["status"] == "completed"

    # ── Scenario C: Critical Priority Forces Air Freight & Green Alt Alert ───
    @pytest.mark.asyncio
    @patch("app.agents.business.quality_assurance._deterministic_defect_rate", return_value=1.0)
    async def test_scenario_c_critical_priority_air_freight(self, mock_rate):
        """Critical priority order -> air freight -> high CO2 -> GreenAlternativeAvailable event."""
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

        session = _setup_mock_session(
            cust=cust, prod=prod, inv=inv, wh=wh, carrier=carrier_air, route=route_air
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
                "items": [{"product_id": str(prod_id), "quantity": 25}],  # large quantity triggers high CO2
                "priority": "critical",
            },
        }

        final = await compiled.ainvoke(initial_state, config={"configurable": {"thread_id": str(uuid.uuid4())}})

        assert final["shipment"]["freight_mode"] == "air"
        assert final["sustainability"]["sustainability_score"] < 80.0
        assert final["sustainability"]["green_alternative"] is not None
        events = _event_types(final)
        assert "GreenAlternativeAvailable" in events

    # ── Scenario D: High-Value Order Human Governance Tier ───────────────────
    @pytest.mark.asyncio
    @patch("app.agents.business.quality_assurance._deterministic_defect_rate", return_value=1.0)
    async def test_scenario_d_high_value_order_governance(self, mock_rate):
        """Order > $500k total value -> requires human approval tier in CEO Agent."""
        cust_id = uuid.uuid4()
        prod_id = uuid.uuid4()
        wh_id = uuid.uuid4()
        carrier_id = uuid.uuid4()

        cust = FakeCustomer(cust_id)
        prod = FakeProduct(prod_id, price=Decimal("600000.00"))  # $600k total
        inv = FakeInventory(prod_id, wh_id, available=10)
        wh = FakeWarehouse(wh_id)
        carrier = FakeCarrier(carrier_id)
        route = FakeRoute(carrier_id)

        session = _setup_mock_session(
            cust=cust, prod=prod, inv=inv, wh=wh, carrier=carrier, route=route
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
                "items": [{"product_id": str(prod_id), "quantity": 1}],
            },
        }

        final = await compiled.ainvoke(initial_state, config={"configurable": {"thread_id": str(uuid.uuid4())}})

        assert final["executive_decision"]["approval_tier"] == "human_required"
        assert final["requires_human_approval"] is True

    # ── Scenario E: Low Gross Margin Suggests Optimization & Pricing Increase ──
    @pytest.mark.asyncio
    @patch("app.agents.business.quality_assurance._deterministic_defect_rate", return_value=1.0)
    async def test_scenario_e_low_margin_suggests_cost_optimization(self, mock_rate):
        """Gross margin under 15% -> Finance suggests cost optimization, Pricing suggests price increase."""
        cust_id = uuid.uuid4()
        prod_id = uuid.uuid4()
        wh_id = uuid.uuid4()
        sup_id = uuid.uuid4()
        carrier_id = uuid.uuid4()

        cust = FakeCustomer(cust_id)
        prod = FakeProduct(prod_id, price=Decimal("100.00"))  # unit price
        wh = FakeWarehouse(wh_id)
        supplier = FakeSupplier(sup_id)
        # Unit cost = $95 -> gross margin = 5% (< 15% threshold)
        sp = FakeSupplierProduct(sup_id, prod_id, price=Decimal("95.00"))
        carrier = FakeCarrier(carrier_id)
        route = FakeRoute(carrier_id, mode="road", cost=Decimal("150.00"))

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
                "items": [{"product_id": str(prod_id), "quantity": 1}],
            },
        }

        final = await compiled.ainvoke(initial_state, config={"configurable": {"thread_id": str(uuid.uuid4())}})

        assert final["finance"]["financial_approval"] is False
        event_types = _event_types(final)
        assert "CostOptimizationSuggested" in event_types
        # Pricing recommends increase
        assert final["pricing"]["results"][0]["recommendation"] == "increase"

    # ── Scenario F: High Risk Denial (Score >= 90) ───────────────────────────
    @pytest.mark.asyncio
    @patch("app.agents.business.quality_assurance._deterministic_defect_rate", return_value=1.0)
    async def test_scenario_f_high_risk_denial(self, mock_rate):
        """Low supplier reliability + long transit route -> Risk >= 90 -> CEO denies order."""
        cust_id = uuid.uuid4()
        prod_id = uuid.uuid4()
        wh_id = uuid.uuid4()

        cust = FakeCustomer(cust_id)
        prod = FakeProduct(prod_id, price=Decimal("500.00"))
        wh = FakeWarehouse(wh_id)
        carrier_id = uuid.uuid4()
        carrier = FakeCarrier(carrier_id)
        route = FakeRoute(carrier_id, mode="air", transit=15)  # transit > 10 adds +35 risk

        session = _setup_mock_session(
            cust=cust,
            prod=prod,
            inv=[],
            wh=wh,
            carrier=carrier,
            route=route,
            supplier_product_pair=None,  # No supplier available adds +40 risk
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
                "items": [{"product_id": str(prod_id), "quantity": 1}],
            },
        }

        final = await compiled.ainvoke(initial_state, config={"configurable": {"thread_id": str(uuid.uuid4())}})

        assert final["risk"]["score"] >= 90.0
        assert final["executive_decision"]["approved"] is False
        assert final["order"]["status"] == "cancelled"

    # ── Scenario G: Early Validation Failure (OM Customer Not Found) ──────────
    @pytest.mark.asyncio
    async def test_scenario_g_invalid_customer_early_termination(self):
        """OM Agent customer lookup returns None -> rejects and terminates workflow."""
        session = _setup_mock_session(cust=None)

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
            },
        }

        final = await compiled.ainvoke(initial_state, config={"configurable": {"thread_id": str(uuid.uuid4())}})

        assert final["workflow_status"] == "failed"
        assert final["active_agents"] == ["ADS-01"]
        assert "OrderRejected" in _event_types(final)

    # ── Scenario H: Demand Spike Detection ───────────────────────────────────
    @pytest.mark.asyncio
    @patch("app.agents.business.quality_assurance._deterministic_defect_rate", return_value=1.0)
    async def test_scenario_h_demand_spike_detection(self, mock_rate):
        """Ordered qty >> 12m avg -> DemandSpikeDetected event, Pricing recommends increase."""
        cust_id = uuid.uuid4()
        prod_id = uuid.uuid4()
        wh_id = uuid.uuid4()
        carrier_id = uuid.uuid4()

        cust = FakeCustomer(cust_id)
        prod = FakeProduct(prod_id, price=Decimal("100.00"))
        inv = FakeInventory(prod_id, wh_id, available=1000)
        wh = FakeWarehouse(wh_id)
        carrier = FakeCarrier(carrier_id)
        route = FakeRoute(carrier_id)

        session = _setup_mock_session(
            cust=cust,
            prod=prod,
            inv=inv,
            wh=wh,
            carrier=carrier,
            route=route,
            hist_avg=1,  # 12m avg is 1 unit
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
                "items": [{"product_id": str(prod_id), "quantity": 25}],  # 25 units >> 2x avg (spike)
            },
        }

        final = await compiled.ainvoke(initial_state, config={"configurable": {"thread_id": str(uuid.uuid4())}})

        events = _event_types(final)
        assert "DemandSpikeDetected" in events
        assert "PriceUpdated" in events
        assert final["pricing"]["results"][0]["recommendation"] == "increase"

    # ── Scenario I: Multi-Product Mixed Availability Path ───────────────────
    @pytest.mark.asyncio
    @patch("app.agents.business.quality_assurance._deterministic_defect_rate", return_value=1.0)
    async def test_scenario_i_multi_product_mixed_stock(self, mock_rate):
        """Mixed stock -> reserves in-stock item, selects supplier and reorders out-of-stock item."""
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
            },
        }

        final = await compiled.ainvoke(initial_state, config={"configurable": {"thread_id": str(uuid.uuid4())}})

        assert final["inventory"][str(p1_id)]["status"] == "reserved"
        assert final["inventory"][str(p2_id)]["status"] == "out_of_stock"
        assert "ADS-05" in final["active_agents"]
        assert final["workflow_status"] == "completed"

    # ── Scenario J: Quality Failure triggers Remanufacturing Routing ─────────
    @pytest.mark.asyncio
    @patch("app.agents.business.quality_assurance._deterministic_defect_rate", return_value=5.5)  # 5.5% > 3% FAIL
    async def test_scenario_j_quality_failure_remanufacturing(self, mock_rate):
        """QA defect rate 5.5% -> fails QA -> Planner schedules remanufacture -> routes to Manufacturing."""
        cust_id = uuid.uuid4()
        prod_id = uuid.uuid4()
        wh_id = uuid.uuid4()
        carrier_id = uuid.uuid4()

        cust = FakeCustomer(cust_id)
        prod = FakeProduct(prod_id, price=Decimal("2000.00"))
        inv = FakeInventory(prod_id, wh_id, available=50, reserved=0)
        wh = FakeWarehouse(wh_id)
        carrier = FakeCarrier(carrier_id)
        route = FakeRoute(carrier_id)

        session = _setup_mock_session(
            cust=cust, prod=prod, inv=inv, wh=wh, carrier=carrier, route=route
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
        assert final["quality"]["status"] == "failed"
        assert final["planning"]["remanufacture_required"] is True
        # Verify that the Manufacturing agent was actually executed in this path
        assert "ADS-07" in final["active_agents"]
        events = _event_types(final)
        assert "QualityFailed" in events
        assert "ProductionPlanned" in events

    # ── Scenario K: High Risk Mitigation (Score = 80) ────────────────────────
    @pytest.mark.asyncio
    @patch("app.agents.business.quality_assurance._deterministic_defect_rate", return_value=1.0)
    async def test_scenario_k_risk_mitigation(self, mock_rate):
        """Low supplier reliability + average route -> Risk = 80 -> Planner schedules risk mitigation."""
        cust_id = uuid.uuid4()
        prod_id = uuid.uuid4()
        wh_id = uuid.uuid4()

        cust = FakeCustomer(cust_id)
        prod = FakeProduct(prod_id, price=Decimal("500.00"))
        wh = FakeWarehouse(wh_id)
        carrier_id = uuid.uuid4()
        carrier = FakeCarrier(carrier_id)
        route = FakeRoute(carrier_id, mode="road", transit=5)

        # Mocking event history low reliability supplier (+40 risk)
        # And no active supplier (+40 risk)
        session = _setup_mock_session(
            cust=cust,
            prod=prod,
            inv=[],
            wh=wh,
            carrier=carrier,
            route=route,
            supplier_product_pair=None,
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
                "items": [{"product_id": str(prod_id), "quantity": 1}],
            },
            # Inject low supplier reliability event to trigger high risk score
            "event_history": [{
                "event_type": "SupplierUpdated",
                "source_agent": "ADS-05",
                "payload": {"reliability_score": 60.0},
            }]
        }

        final = await compiled.ainvoke(initial_state, config={"configurable": {"thread_id": str(uuid.uuid4())}})

        assert final["risk"]["score"] >= 70.0
        assert final["risk"]["score"] < 90.0
        actions = final["planning"]["actions"]
        action_types = [a["action"] for a in actions]
        assert "risk_mitigation" in action_types
        # Find risk mitigation step
        mitigation = next(a for a in actions if a["action"] == "risk_mitigation")
        assert len(mitigation["mitigations"]) > 0

    # ── Scenario L: Negotiation Volume Discount on High Volume ───────────────
    @pytest.mark.asyncio
    @patch("app.agents.business.quality_assurance._deterministic_defect_rate", return_value=1.0)
    async def test_scenario_l_negotiation_volume_discount(self, mock_rate):
        """Procurement qty >= min_qty x 3 -> Negotiation applies volume discount."""
        cust_id = uuid.uuid4()
        prod_id = uuid.uuid4()
        wh_id = uuid.uuid4()
        sup_id = uuid.uuid4()
        carrier_id = uuid.uuid4()

        cust = FakeCustomer(cust_id)
        prod = FakeProduct(prod_id, price=Decimal("100.00"))
        wh = FakeWarehouse(wh_id)
        supplier = FakeSupplier(sup_id)
        sp = FakeSupplierProduct(sup_id, prod_id, price=Decimal("100.00"))  # original cost
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
                # Qty = 100 >> min_qty (1) * 3 -> eligible for volume discount
                "items": [{"product_id": str(prod_id), "quantity": 100}],
            },
            "event_history": [{
                "event_type": "SupplierUpdated",
                "source_agent": "ADS-05",
                "payload": {"supplier_id": str(sup_id), "reliability_score": 95.0},
            }]
        }

        final = await compiled.ainvoke(initial_state, config={"configurable": {"thread_id": str(uuid.uuid4())}})

        assert final["negotiation"]["status"] == "completed"
        assert final["negotiation"]["discount_pct"] > 0
        assert final["negotiation"]["strategy"] == "volume_discount"
        assert Decimal(final["negotiation"]["final_unit_cost"]) < Decimal("100.00")
        assert "ContractTermsProposed" in _event_types(final)

    # ── Scenario M: Negotiation SLA Penalty Clause on Low Supplier Reliability ──
    @pytest.mark.asyncio
    @patch("app.agents.business.quality_assurance._deterministic_defect_rate", return_value=1.0)
    async def test_scenario_m_negotiation_penalty_clause(self, mock_rate):
        """Supplier reliability < 85 -> Negotiation proposes SLA penalty terms."""
        cust_id = uuid.uuid4()
        prod_id = uuid.uuid4()
        wh_id = uuid.uuid4()
        sup_id = uuid.uuid4()
        carrier_id = uuid.uuid4()

        cust = FakeCustomer(cust_id)
        prod = FakeProduct(prod_id, price=Decimal("100.00"))
        wh = FakeWarehouse(wh_id)
        supplier = FakeSupplier(sup_id, reliability=Decimal("75.0"))
        sp = FakeSupplierProduct(sup_id, prod_id, price=Decimal("100.00"), min_qty=5)
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
            hist_avg=8,
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
            # Inject low supplier reliability
            "event_history": [{
                "event_type": "SupplierUpdated",
                "source_agent": "ADS-05",
                "payload": {
                    "supplier_id": str(sup_id),
                    "reliability_score": 75.0,
                    "minimum_order_qty": 5,
                },
            }]
        }

        final = await compiled.ainvoke(initial_state, config={"configurable": {"thread_id": str(uuid.uuid4())}})

        assert final["negotiation"]["status"] == "completed"
        terms = final["negotiation"]["terms_proposed"]
        assert any("penalty" in t.lower() or "sla" in t.lower() for t in terms)

    # ── Scenario N: Negotiation urgent override skip ─────────────────────────
    @pytest.mark.asyncio
    @patch("app.agents.business.quality_assurance._deterministic_defect_rate", return_value=1.0)
    async def test_scenario_n_negotiation_urgent_skip(self, mock_rate):
        """Urgency = high -> Negotiation skips entirely to prioritize speed."""
        cust_id = uuid.uuid4()
        prod_id = uuid.uuid4()
        wh_id = uuid.uuid4()
        sup_id = uuid.uuid4()
        carrier_id = uuid.uuid4()

        cust = FakeCustomer(cust_id)
        prod = FakeProduct(prod_id, price=Decimal("100.00"))
        wh = FakeWarehouse(wh_id)
        supplier = FakeSupplier(sup_id)
        sp = FakeSupplierProduct(sup_id, prod_id, price=Decimal("100.00"))
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
                "items": [{"product_id": str(prod_id), "quantity": 1}],
            },
            # Inject high lead time to trigger reorder_urgency = high
            "procurement": {
                "reorder_urgency": "high",
                "strategy": "standard",
            }
        }

        final = await compiled.ainvoke(initial_state, config={"configurable": {"thread_id": str(uuid.uuid4())}})

        assert final["negotiation"]["status"] == "skipped"
        assert final["negotiation"]["strategy"] == "urgent_skip"
        assert "NegotiationCompleted" in _event_types(final)
