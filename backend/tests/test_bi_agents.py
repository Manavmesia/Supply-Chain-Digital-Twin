"""
Unit tests for Phase 4 Business Intelligence agents — ADS-02, ADS-09, ADS-10, ADS-18.

All DB and EventPublisher operations are mocked via AsyncMock.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.graph.state import SupplyChainState


def _make_state(**overrides) -> SupplyChainState:
    base: SupplyChainState = {
        "workflow_id": str(uuid.uuid4()),
        "correlation_id": str(uuid.uuid4()),
        "workflow_status": "operational",
        "active_agents": [],
        "event_history": [],
        "decisions": [],
        "errors": [],
    }
    base.update(overrides)
    return base


def _mock_scalar(val):
    res = MagicMock()
    res.scalar.return_value = val
    res.scalar_one_or_none.return_value = val
    res.scalars.return_value.all.return_value = [val] if val else []
    return res


# =============================================================================
# ADS-02 — Demand Forecast Agent
# =============================================================================

class TestDemandForecastAgent:
    @pytest.mark.asyncio
    async def test_generates_forecast_and_confidence(self):
        from app.agents.business.demand_forecast import DemandForecastAgent

        prod_id = uuid.uuid4()
        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[
            _mock_scalar(200),  # hist_qty sum
            _mock_scalar(None), # promo lookup
        ])

        state = _make_state(
            order={
                "items": [{"product_id": str(prod_id), "quantity": 5}],
            }
        )

        agent = DemandForecastAgent(session=session)
        result = await agent.run(state)

        assert "forecast" in result
        fc = result["forecast"][str(prod_id)]
        assert fc["forecast_quantity"] == 200
        assert fc["confidence"] > 0.70
        assert any(e["event_type"] == "DemandForecastGenerated" for e in result.get("event_history", []))

    @pytest.mark.asyncio
    async def test_detects_demand_spike(self):
        from app.agents.business.demand_forecast import DemandForecastAgent

        prod_id = uuid.uuid4()
        session = AsyncMock()
        # hist_qty = 12 → 12m avg = 1.0. Forecast = max(12, 10*10) = 100 >= 2 * 1.0 → spike
        session.execute = AsyncMock(side_effect=[
            _mock_scalar(12),
            _mock_scalar(None),
        ])

        state = _make_state(
            order={
                "items": [{"product_id": str(prod_id), "quantity": 10}],
            }
        )

        agent = DemandForecastAgent(session=session)
        result = await agent.run(state)

        event_types = [e["event_type"] for e in result.get("event_history", [])]
        assert "DemandSpikeDetected" in event_types


# =============================================================================
# ADS-09 — Finance Agent
# =============================================================================

class TestFinanceAgent:
    @pytest.mark.asyncio
    async def test_financial_approval_granted_for_profitable_order(self):
        from app.agents.business.finance import FinanceAgent

        state = _make_state(
            order={
                "order_id": str(uuid.uuid4()),
                "total_amount": "10000.00",
                "items": [{"quantity": 2}],
            },
            supplier={
                "purchase_orders": [
                    {"unit_cost": "2000.00", "quantity": 2}  # Cost = 4000
                ]
            },
            shipment={"freight_mode": "road"},
        )

        agent = FinanceAgent(session=None)
        result = await agent.run(state)

        assert result["finance"]["financial_approval"] is True
        assert result["finance"]["gross_margin_pct"] > 15.0
        assert any(e["event_type"] == "FinancialApprovalGranted" for e in result.get("event_history", []))

    @pytest.mark.asyncio
    async def test_cost_optimization_suggested_for_low_margin(self):
        from app.agents.business.finance import FinanceAgent

        state = _make_state(
            order={
                "order_id": str(uuid.uuid4()),
                "total_amount": "5000.00",
                "items": [{"quantity": 1}],
            },
            supplier={
                "purchase_orders": [
                    {"unit_cost": "4600.00", "quantity": 1}  # High cost -> low margin
                ]
            },
            shipment={"freight_mode": "air"},  # 650 shipping cost -> total cost 5260 > revenue
        )

        agent = FinanceAgent(session=None)
        result = await agent.run(state)

        assert result["finance"]["financial_approval"] is False
        assert any(e["event_type"] == "CostOptimizationSuggested" for e in result.get("event_history", []))


# =============================================================================
# ADS-10 — Risk Management Agent
# =============================================================================

class TestRiskAgent:
    @pytest.mark.asyncio
    async def test_low_risk_evaluation(self):
        from app.agents.business.risk import RiskAgent

        state = _make_state(
            order={"order_id": str(uuid.uuid4())},
            supplier={"status": "selected", "purchase_orders": [{"reliability_score": 95.0}]},
            shipment={"freight_mode": "road", "transit_days": 3},
            finance={"gross_margin_pct": 35.0},
            forecast={"p1": {"confidence": 0.90}},
        )

        agent = RiskAgent(session=None)
        result = await agent.run(state)

        assert result["risk"]["level"] == "Low"
        assert result["risk"]["score"] < 40.0

    @pytest.mark.asyncio
    async def test_high_risk_triggers_risk_detected_event(self):
        from app.agents.business.risk import RiskAgent

        state = _make_state(
            order={"order_id": str(uuid.uuid4())},
            supplier={"status": "unavailable"},  # +40 pts
            shipment={"freight_mode": "air", "transit_days": 12},  # +15 +20 pts
            finance={"gross_margin_pct": 5.0},  # +30 pts -> Total > 90
        )

        agent = RiskAgent(session=None)
        result = await agent.run(state)

        assert result["risk"]["level"] in ("High", "Critical")
        assert result["risk"]["mitigation_recommended"] is True
        event_types = [e["event_type"] for e in result.get("event_history", [])]
        assert "ExecutiveEscalation" in event_types or "RiskDetected" in event_types


# =============================================================================
# ADS-18 — Reporting Agent
# =============================================================================

class TestReportingAgent:
    @pytest.mark.asyncio
    async def test_generates_report_snapshot_and_events(self):
        from app.agents.coordination.reporting import ReportingAgent

        session = AsyncMock()
        session.flush = AsyncMock()

        state = _make_state(
            workflow_id=str(uuid.uuid4()),
            order={"order_id": str(uuid.uuid4()), "status": "delivered", "total_amount": "12000.00"},
            shipment={"carrier": "FedEx", "tracking_id": "TRK123"},
            finance={"gross_margin_pct": 28.5},
            risk={"score": 15.0, "level": "Low"},
            executive_decision={"approved": True, "approval_tier": "finance_review"},
        )

        agent = ReportingAgent(session=session)
        result = await agent.run(state)

        assert "reports" in result
        assert result["reports"]["summary"]["gross_margin_pct"] == 28.5
        assert result["reports"]["summary"]["ceo_approved"] is True
        event_types = [e["event_type"] for e in result.get("event_history", [])]
        assert "ReportGenerated" in event_types
        assert "DashboardUpdated" in event_types
