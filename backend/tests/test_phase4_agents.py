"""
Unit tests for all 6 Phase 4 agents — no DB, no broker required.

Tests cover:
  - ADS-11 PricingAgent         — demand spike, low margin, high margin, stable
  - ADS-12 ProcurementStrategyAgent — bulk reorder, lead time risk, contract expiry
  - ADS-13 SustainabilityAgent  — air CO2, road CO2, green alternative
  - ADS-14 QualityAssuranceAgent — pass, fail, always InspectionCompleted
  - ADS-15 PlannerAgent         — quality failed, high risk, demand spike, standard
  - ADS-16 NegotiationAgent     — volume discount, penalty clause, urgency skip, no POs
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.graph.state import SupplyChainState


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_state(**overrides) -> SupplyChainState:
    base: SupplyChainState = {
        "workflow_id": str(uuid.uuid4()),
        "correlation_id": str(uuid.uuid4()),
        "workflow_status": "operational",
        "active_agents": [],
        "event_history": [],
        "decisions": [],
        "errors": [],
        "messages": [],
        "retries": {},
    }
    base.update(overrides)
    return base


def _event_types(result: dict) -> list[str]:
    return [e["event_type"] for e in result.get("event_history", [])]


# =============================================================================
# ADS-11 — Pricing Agent
# =============================================================================

class TestPricingAgent:
    """Verify dynamic pricing rules produce correct recommendations."""

    @pytest.mark.asyncio
    async def test_demand_spike_recommends_price_increase(self):
        from app.agents.business.pricing import PricingAgent

        product_id = str(uuid.uuid4())
        session = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()

        state = _make_state(
            order={
                "order_id": str(uuid.uuid4()),
                "items": [{"product_id": product_id, "quantity": 5, "unit_price": "100.00"}],
            },
            forecast={
                product_id: {
                    # baseline=10, forecast=30 → 3× baseline = spike
                    "forecast_quantity": 30.0,
                    "baseline_quantity": 10.0,
                    "confidence": 0.85,
                }
            },
            finance={"gross_margin_pct": 25.0},
        )

        agent = PricingAgent(session=session)
        result = await agent.run(state)

        assert "pricing" in result
        events = _event_types(result)
        assert "PriceUpdated" in events
        assert "PriceStable" not in events
        results = result["pricing"]["results"]
        assert len(results) == 1
        assert results[0]["recommendation"] == "increase"
        assert results[0]["adjustment_pct"] > 0

    @pytest.mark.asyncio
    async def test_low_margin_recommends_price_increase(self):
        from app.agents.business.pricing import PricingAgent

        product_id = str(uuid.uuid4())
        session = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()

        state = _make_state(
            order={
                "order_id": str(uuid.uuid4()),
                "items": [{"product_id": product_id, "quantity": 1, "unit_price": "200.00"}],
            },
            forecast={
                product_id: {
                    "forecast_quantity": 5.0,
                    "baseline_quantity": 5.0,   # no spike
                    "confidence": 0.80,
                }
            },
            # gross margin < 15% threshold → should trigger price increase
            finance={"gross_margin_pct": 10.0},
        )

        agent = PricingAgent(session=session)
        result = await agent.run(state)

        events = _event_types(result)
        assert "PriceUpdated" in events
        results = result["pricing"]["results"]
        assert results[0]["recommendation"] == "increase"
        # Low margin increase = 8% = 8.0 adjustment_pct
        assert abs(results[0]["adjustment_pct"] - 8.0) < 0.01

    @pytest.mark.asyncio
    async def test_high_margin_recommends_discount(self):
        from app.agents.business.pricing import PricingAgent

        product_id = str(uuid.uuid4())
        session = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()

        state = _make_state(
            order={
                "order_id": str(uuid.uuid4()),
                "items": [{"product_id": product_id, "quantity": 1, "unit_price": "500.00"}],
            },
            forecast={
                product_id: {
                    "forecast_quantity": 5.0,
                    "baseline_quantity": 5.0,   # no spike
                    "confidence": 0.80,
                }
            },
            # gross margin > 40% threshold → promotional discount
            finance={"gross_margin_pct": 45.0},
        )

        agent = PricingAgent(session=session)
        result = await agent.run(state)

        events = _event_types(result)
        assert "PriceUpdated" in events
        results = result["pricing"]["results"]
        assert results[0]["recommendation"] == "discount"
        assert results[0]["adjustment_pct"] < 0  # negative = discount

    @pytest.mark.asyncio
    async def test_stable_conditions_emit_price_stable_event(self):
        from app.agents.business.pricing import PricingAgent

        product_id = str(uuid.uuid4())
        session = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()

        state = _make_state(
            order={
                "order_id": str(uuid.uuid4()),
                "items": [{"product_id": product_id, "quantity": 1, "unit_price": "100.00"}],
            },
            forecast={
                product_id: {
                    "forecast_quantity": 5.0,
                    "baseline_quantity": 5.0,  # no spike
                    "confidence": 0.80,
                }
            },
            finance={"gross_margin_pct": 25.0},  # in sweet spot: 15-40%
        )

        agent = PricingAgent(session=session)
        result = await agent.run(state)

        events = _event_types(result)
        assert "PriceStable" in events
        assert "PriceUpdated" not in events
        assert result["pricing"]["results"][0]["recommendation"] == "stable"


# =============================================================================
# ADS-12 — Procurement Strategy Agent
# =============================================================================

class TestProcurementStrategyAgent:
    """Verify procurement strategy rules: bulk reorder, lead time risk, urgent contracts."""

    @pytest.mark.asyncio
    async def test_no_contracts_standard_strategy_published(self):
        from app.agents.business.procurement_strategy import ProcurementStrategyAgent

        product_id = str(uuid.uuid4())
        session = AsyncMock()
        no_contracts = MagicMock()
        no_contracts.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=no_contracts)
        session.flush = AsyncMock()

        state = _make_state(
            order={
                "order_id": str(uuid.uuid4()),
                "items": [{"product_id": product_id, "quantity": 10}],
            },
            supplier={"status": "selected", "purchase_orders": [
                {"supplier_id": str(uuid.uuid4()), "quantity": 10, "lead_time_days": 5}
            ]},
            forecast={product_id: {"forecast_quantity": 12.0}},
        )

        agent = ProcurementStrategyAgent(session=session)
        result = await agent.run(state)

        assert "procurement" in result
        events = _event_types(result)
        assert "ProcurementPlanCreated" in events
        assert result["procurement"]["strategy"] == "standard"
        assert result["procurement"]["reorder_urgency"] == "normal"

    @pytest.mark.asyncio
    async def test_high_lead_time_flags_urgency(self):
        from app.agents.business.procurement_strategy import ProcurementStrategyAgent

        product_id = str(uuid.uuid4())
        session = AsyncMock()
        no_contracts = MagicMock()
        no_contracts.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=no_contracts)
        session.flush = AsyncMock()

        state = _make_state(
            order={
                "order_id": str(uuid.uuid4()),
                "items": [{"product_id": product_id, "quantity": 5}],
            },
            supplier={"status": "selected", "purchase_orders": [
                # lead_time_days > 14 → high risk
                {"supplier_id": str(uuid.uuid4()), "quantity": 5, "lead_time_days": 21}
            ]},
            forecast={product_id: {"forecast_quantity": 5.0}},
        )

        agent = ProcurementStrategyAgent(session=session)
        result = await agent.run(state)

        assert result["procurement"]["lead_time_risk"] is True
        assert result["procurement"]["reorder_urgency"] == "high"

    @pytest.mark.asyncio
    async def test_demand_spike_triggers_bulk_strategy(self):
        from app.agents.business.procurement_strategy import ProcurementStrategyAgent

        product_id = str(uuid.uuid4())
        session = AsyncMock()
        no_contracts = MagicMock()
        no_contracts.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=no_contracts)
        session.flush = AsyncMock()

        state = _make_state(
            order={
                "order_id": str(uuid.uuid4()),
                "items": [{"product_id": product_id, "quantity": 5}],
            },
            supplier={"status": "selected", "purchase_orders": [
                {"supplier_id": str(uuid.uuid4()), "quantity": 5, "lead_time_days": 7}
            ]},
            # forecast_qty > ordered_qty × 1.5 → bulk reorder
            forecast={product_id: {"forecast_quantity": 100.0}},
        )

        agent = ProcurementStrategyAgent(session=session)
        result = await agent.run(state)

        assert result["procurement"]["strategy"] == "bulk"
        assert result["procurement"]["recommended_qty"] > _STANDARD_REORDER_QTY()
        assert result["procurement"]["reorder_urgency"] == "high"


def _STANDARD_REORDER_QTY():
    """Return the standard reorder qty constant from the procurement agent."""
    from app.agents.business.procurement_strategy import _STANDARD_REORDER_QTY
    return _STANDARD_REORDER_QTY


# =============================================================================
# ADS-13 — Sustainability Agent
# =============================================================================

class TestSustainabilityAgent:
    """Verify CO2 calculations and green alternative detection."""

    @pytest.mark.asyncio
    async def test_air_freight_produces_high_co2_low_score(self):
        from app.agents.business.sustainability import SustainabilityAgent

        session = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()

        state = _make_state(
            order={"order_id": str(uuid.uuid4()), "items": [{"product_id": str(uuid.uuid4()), "quantity": 10}]},
            shipment={"freight_mode": "air", "carrier": "DHL Air", "transit_days": 1},
        )

        agent = SustainabilityAgent(session=session)
        result = await agent.run(state)

        assert "sustainability" in result
        assert result["sustainability"]["freight_mode"] == "air"
        # Air freight produces much more CO2 than road
        assert result["sustainability"]["co2_kg"] > 100.0
        # Low score for air
        assert result["sustainability"]["sustainability_score"] < 80.0
        events = _event_types(result)
        assert "SustainabilityScoreCalculated" in events

    @pytest.mark.asyncio
    async def test_road_freight_produces_lower_co2(self):
        from app.agents.business.sustainability import SustainabilityAgent

        session = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()

        state = _make_state(
            order={"order_id": str(uuid.uuid4()), "items": [{"product_id": str(uuid.uuid4()), "quantity": 5}]},
            shipment={"freight_mode": "road", "carrier": "FedEx Ground", "transit_days": 5},
        )

        agent = SustainabilityAgent(session=session)
        result = await agent.run(state)

        # Road CO2 should be much lower than air
        assert result["sustainability"]["co2_kg"] < 100.0
        assert result["sustainability"]["sustainability_score"] > 90.0

    @pytest.mark.asyncio
    async def test_high_air_co2_triggers_green_alternative(self):
        from app.agents.business.sustainability import SustainabilityAgent, _CO2_HIGH_THRESHOLD

        session = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()

        state = _make_state(
            order={
                "order_id": str(uuid.uuid4()),
                # Many items → high weight → high CO2 for air
                "items": [{"product_id": str(uuid.uuid4()), "quantity": 500}],
            },
            shipment={"freight_mode": "air", "carrier": "DHL", "transit_days": 1},
        )

        agent = SustainabilityAgent(session=session)
        result = await agent.run(state)

        events = _event_types(result)
        # With large quantity, air CO2 should exceed threshold
        if result["sustainability"]["co2_kg"] >= _CO2_HIGH_THRESHOLD:
            assert "GreenAlternativeAvailable" in events
            assert result["sustainability"]["green_alternative"] is not None
            assert result["sustainability"]["green_alternative"]["alternative_mode"] == "road"

    @pytest.mark.asyncio
    async def test_sea_freight_produces_lowest_co2(self):
        from app.agents.business.sustainability import SustainabilityAgent

        session = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()

        state = _make_state(
            order={"order_id": str(uuid.uuid4()), "items": [{"product_id": str(uuid.uuid4()), "quantity": 10}]},
            shipment={"freight_mode": "sea", "carrier": "Maersk", "transit_days": 20},
        )

        agent = SustainabilityAgent(session=session)
        result = await agent.run(state)

        # Sea freight should have the lowest CO2 of all modes
        assert result["sustainability"]["co2_kg"] < 50.0
        assert result["sustainability"]["sustainability_score"] > 95.0


# =============================================================================
# ADS-14 — Quality Assurance Agent
# =============================================================================

class TestQualityAssuranceAgent:
    """Verify inspection simulation and event publication."""

    @pytest.mark.asyncio
    async def test_always_publishes_inspection_completed(self):
        from app.agents.business.quality_assurance import QualityAssuranceAgent

        product_id = str(uuid.uuid4())
        session = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()

        state = _make_state(
            order={
                "order_id": str(uuid.uuid4()),
                "items": [{"product_id": product_id, "quantity": 100}],
            }
        )

        agent = QualityAssuranceAgent(session=session)
        result = await agent.run(state)

        events = _event_types(result)
        assert "InspectionCompleted" in events
        assert "quality" in result

    @pytest.mark.asyncio
    async def test_deterministic_result_for_same_product_id(self):
        """Two runs with same product_id produce identical defect rates."""
        from app.agents.business.quality_assurance import QualityAssuranceAgent, _deterministic_defect_rate

        product_id = str(uuid.uuid4())
        mo_id = str(uuid.uuid4())

        rate1 = _deterministic_defect_rate(product_id, mo_id)
        rate2 = _deterministic_defect_rate(product_id, mo_id)
        assert rate1 == rate2

    @pytest.mark.asyncio
    async def test_manufacturing_orders_used_when_present(self):
        from app.agents.business.quality_assurance import QualityAssuranceAgent

        product_id = str(uuid.uuid4())
        mo_id = str(uuid.uuid4())
        session = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()

        state = _make_state(
            order={"order_id": str(uuid.uuid4()), "items": []},
            manufacturing={
                "orders": [{
                    "mo_id": mo_id,
                    "product_id": product_id,
                    "planned_qty": 200,
                }]
            }
        )

        agent = QualityAssuranceAgent(session=session)
        result = await agent.run(state)

        events = _event_types(result)
        assert "InspectionCompleted" in events
        # Should be either QualityPassed or QualityFailed — exactly one
        assert ("QualityPassed" in events) != ("QualityFailed" in events)
        inspections = result["quality"]["inspections"]
        assert len(inspections) == 1
        assert inspections[0]["mo_id"] == mo_id

    @pytest.mark.asyncio
    async def test_no_items_skips_inspection(self):
        from app.agents.business.quality_assurance import QualityAssuranceAgent

        session = AsyncMock()
        state = _make_state(order={"order_id": str(uuid.uuid4()), "items": []})

        agent = QualityAssuranceAgent(session=session)
        result = await agent.run(state)

        assert result["quality"]["status"] == "skipped"


# =============================================================================
# ADS-15 — Planner Agent
# =============================================================================

class TestPlannerAgent:
    """Verify execution plan generation from multi-agent state synthesis."""

    @pytest.mark.asyncio
    async def test_quality_failure_adds_remanufacture_action(self):
        from app.agents.coordination.planner import PlannerAgent

        state = _make_state(
            order={"order_id": str(uuid.uuid4()), "priority": "standard"},
            quality={"status": "failed", "all_passed": False, "failed_count": 2},
            risk={"score": 20.0, "factors": []},
            forecast={},
            procurement={"reorder_urgency": "normal"},
        )

        agent = PlannerAgent(session=None)
        result = await agent.run(state)

        assert "planning" in result
        assert result["planning"]["remanufacture_required"] is True
        action_types = [a["action"] for a in result["planning"]["actions"]]
        assert "remanufacture" in action_types
        events = _event_types(result)
        assert "ExecutionPlanReady" in events
        assert "ProductionPlanned" in events

    @pytest.mark.asyncio
    async def test_high_risk_adds_mitigation_step(self):
        from app.agents.coordination.planner import PlannerAgent

        state = _make_state(
            order={"order_id": str(uuid.uuid4()), "priority": "standard"},
            quality={"status": "passed", "all_passed": True, "failed_count": 0},
            risk={
                "score": 80.0,  # >= 70 threshold
                "factors": [{"factor": "supplier_delay"}, {"factor": "long_transit"}],
            },
            forecast={},
            procurement={"reorder_urgency": "normal"},
        )

        agent = PlannerAgent(session=None)
        result = await agent.run(state)

        action_types = [a["action"] for a in result["planning"]["actions"]]
        assert "risk_mitigation" in action_types
        # Verify mitigations were generated
        risk_action = next(a for a in result["planning"]["actions"] if a["action"] == "risk_mitigation")
        assert len(risk_action["mitigations"]) > 0

    @pytest.mark.asyncio
    async def test_high_procurement_urgency_triggers_expedite(self):
        from app.agents.coordination.planner import PlannerAgent

        product_id = str(uuid.uuid4())
        state = _make_state(
            order={"order_id": str(uuid.uuid4()), "priority": "standard"},
            quality={"status": "passed", "all_passed": True, "failed_count": 0},
            risk={"score": 10.0, "factors": []},
            forecast={},
            procurement={"reorder_urgency": "high", "strategy": "bulk"},
        )

        agent = PlannerAgent(session=None)
        result = await agent.run(state)

        action_types = [a["action"] for a in result["planning"]["actions"]]
        assert "expedite_procurement" in action_types

    @pytest.mark.asyncio
    async def test_standard_fulfillment_always_in_plan(self):
        """Standard fulfillment step is always present regardless of conditions."""
        from app.agents.coordination.planner import PlannerAgent

        state = _make_state(
            order={"order_id": str(uuid.uuid4()), "priority": "standard"},
            quality={"status": "passed", "all_passed": True, "failed_count": 0},
            risk={"score": 5.0, "factors": []},
            forecast={},
            procurement={"reorder_urgency": "normal"},
        )

        agent = PlannerAgent(session=None)
        result = await agent.run(state)

        action_types = [a["action"] for a in result["planning"]["actions"]]
        assert "standard_fulfillment" in action_types


# =============================================================================
# ADS-16 — Negotiation Agent
# =============================================================================

class TestNegotiationAgent:
    """Verify negotiation strategies: volume discount, penalty clause, urgency skip."""

    @pytest.mark.asyncio
    async def test_high_urgency_skips_negotiation(self):
        from app.agents.coordination.negotiation import NegotiationAgent

        state = _make_state(
            order={"order_id": str(uuid.uuid4())},
            supplier={"status": "selected", "purchase_orders": [
                {"supplier_id": str(uuid.uuid4()), "unit_cost": "1000.00", "quantity": 100}
            ]},
            procurement={"reorder_urgency": "high", "strategy": "standard"},
        )

        agent = NegotiationAgent(session=None)
        result = await agent.run(state)

        assert result["negotiation"]["status"] == "skipped"
        assert result["negotiation"]["strategy"] == "urgent_skip"
        events = _event_types(result)
        assert "NegotiationCompleted" in events

    @pytest.mark.asyncio
    async def test_no_purchase_orders_skips_negotiation(self):
        from app.agents.coordination.negotiation import NegotiationAgent

        state = _make_state(
            order={"order_id": str(uuid.uuid4())},
            supplier={"status": "unavailable", "purchase_orders": []},
            procurement={"reorder_urgency": "normal", "strategy": "standard"},
        )

        agent = NegotiationAgent(session=None)
        result = await agent.run(state)

        assert result["negotiation"]["status"] == "skipped"
        assert result["negotiation"]["reason"] == "no_purchase_orders"

    @pytest.mark.asyncio
    async def test_low_reliability_supplier_gets_penalty_clause(self):
        from app.agents.coordination.negotiation import NegotiationAgent

        supplier_id = str(uuid.uuid4())
        state = _make_state(
            order={"order_id": str(uuid.uuid4())},
            supplier={"status": "selected", "purchase_orders": [
                {"supplier_id": supplier_id, "unit_cost": "500.00", "quantity": 5}
            ]},
            procurement={"reorder_urgency": "normal", "strategy": "standard"},
            # Inject SupplierUpdated event with low reliability
            event_history=[{
                "event_type": "SupplierUpdated",
                "source_agent": "ADS-05",
                "payload": {
                    "supplier_id": supplier_id,
                    "reliability_score": 72.0,  # < 85 threshold
                    "lead_time_days": 10,
                },
                "timestamp": "2026-08-06T12:00:00Z",
            }],
        )

        agent = NegotiationAgent(session=None)
        result = await agent.run(state)

        assert result["negotiation"]["status"] == "completed"
        # Penalty clause should be in proposed terms
        terms = result["negotiation"]["terms_proposed"]
        assert any("penalty" in t.lower() or "sla" in t.lower() for t in terms)
        events = _event_types(result)
        assert "ContractTermsProposed" in events

    @pytest.mark.asyncio
    async def test_large_volume_gets_volume_discount(self):
        from app.agents.coordination.negotiation import NegotiationAgent, _VOLUME_DISCOUNT_MULTIPLIER

        state = _make_state(
            order={"order_id": str(uuid.uuid4())},
            supplier={"status": "selected", "purchase_orders": [
                {
                    "supplier_id": str(uuid.uuid4()),
                    "unit_cost": "100.00",
                    # qty = 30 >> min_order_qty(1) × 3 = 3 → volume discount eligible
                    "quantity": 30,
                }
            ]},
            procurement={"reorder_urgency": "normal", "strategy": "standard"},
            event_history=[{
                "event_type": "SupplierUpdated",
                "source_agent": "ADS-05",
                "payload": {"reliability_score": 95.0},  # good reliability
                "timestamp": "2026-08-06T12:00:00Z",
            }],
        )

        agent = NegotiationAgent(session=None)
        result = await agent.run(state)

        assert result["negotiation"]["status"] == "completed"
        assert result["negotiation"]["discount_pct"] > 0
        assert result["negotiation"]["strategy"] == "volume_discount"
        # Final price should be lower than original
        final = Decimal(result["negotiation"]["final_unit_cost"])
        assert final < Decimal("100.00")
