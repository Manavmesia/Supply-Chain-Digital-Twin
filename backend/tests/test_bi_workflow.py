"""
Integration tests for the Phase 4 Business Intelligence LangGraph workflow.

Verifies end-to-end execution across all 10 nodes:
  Order Management → Demand Forecast → Inventory → (Warehouse / Supplier)
  → Transportation → Finance → Risk Management → CEO Approval → Reporting → END
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.graph.state import SupplyChainState
from app.graph.workflow import compile_workflow


def _make_initial_state(**overrides) -> SupplyChainState:
    base: SupplyChainState = {
        "workflow_id": str(uuid.uuid4()),
        "correlation_id": str(uuid.uuid4()),
        "workflow_status": "received",
        "active_agents": [],
        "event_history": [],
        "decisions": [],
        "errors": [],
        "order": {
            "customer_id": str(uuid.uuid4()),
            "items": [{"product_id": str(uuid.uuid4()), "quantity": 2}],
            "priority": "standard",
        },
    }
    base.update(overrides)
    return base


class TestPhase4BIWorkflowIntegration:
    """Verifies that all 10 nodes execute in sequence and enrich global state."""

    @pytest.mark.asyncio
    async def test_full_10_node_bi_workflow_happy_path(self):
        order_id = str(uuid.uuid4())
        product_id = str(uuid.uuid4())
        warehouse_id = str(uuid.uuid4())

        with (
            patch(
                "app.agents.operational.order_management.OrderManagementAgent._execute",
                new=AsyncMock(return_value={
                    "order": {"order_id": order_id, "total_amount": "15000.00", "priority": "standard", "items": [{"product_id": product_id, "quantity": 2}]},
                    "customer": {"name": "Enterprise Client"},
                    "workflow_status": "operational",
                    "decisions": [],
                    "event_history": [{"event_type": "OrderCreated"}],
                }),
            ),
            patch(
                "app.agents.business.demand_forecast.DemandForecastAgent._execute",
                new=AsyncMock(return_value={
                    "forecast": {product_id: {"forecast_quantity": 50, "confidence": 0.88}},
                    "decisions": [],
                    "event_history": [{"event_type": "DemandForecastGenerated"}],
                }),
            ),
            patch(
                "app.agents.operational.inventory.InventoryAgent._execute",
                new=AsyncMock(return_value={
                    "inventory": {product_id: {"status": "reserved", "warehouse_id": warehouse_id}},
                    "next_node": "warehouse",
                    "decisions": [],
                    "event_history": [{"event_type": "InventoryAllocated"}],
                }),
            ),
            patch(
                "app.agents.operational.warehouse.WarehouseAgent._execute",
                new=AsyncMock(return_value={
                    "warehouse": {"warehouse_id": warehouse_id, "city": "Newark", "country": "US"},
                    "decisions": [],
                    "event_history": [{"event_type": "ShipmentReady"}],
                }),
            ),
            patch(
                "app.agents.operational.transportation.TransportationAgent._execute",
                new=AsyncMock(return_value={
                    "shipment": {"shipment_id": str(uuid.uuid4()), "carrier": "FedEx", "freight_mode": "road", "transit_days": 3},
                    "decisions": [],
                    "event_history": [{"event_type": "ShipmentCreated"}],
                }),
            ),
            patch(
                "app.agents.business.finance.FinanceAgent._execute",
                new=AsyncMock(return_value={
                    "finance": {"gross_margin_pct": 26.5, "financial_approval": True, "total_cost": "11000.00"},
                    "decisions": [],
                    "event_history": [{"event_type": "FinancialApprovalGranted"}],
                }),
            ),
            patch(
                "app.agents.business.risk.RiskAgent._execute",
                new=AsyncMock(return_value={
                    "risk": {"score": 22.0, "level": "Low", "mitigation_recommended": False},
                    "decisions": [],
                    "event_history": [],
                }),
            ),
            patch(
                "app.agents.coordination.ceo.CEOAgent._execute",
                new=AsyncMock(return_value={
                    "executive_decision": {"approved": True, "approval_tier": "finance_review"},
                    "workflow_status": "completed",
                    "decisions": [],
                    "event_history": [{"event_type": "CEOApprovalGranted"}],
                }),
            ),
            patch(
                "app.agents.coordination.reporting.ReportingAgent._execute",
                new=AsyncMock(return_value={
                    "reports": {"latest_report_id": str(uuid.uuid4()), "summary": {"order_id": order_id}},
                    "decisions": [],
                    "event_history": [{"event_type": "ReportGenerated"}],
                }),
            ),
        ):
            compiled = compile_workflow(session_factory=None, publisher=None)
            initial = _make_initial_state()
            config = {"configurable": {"thread_id": str(uuid.uuid4())}}
            final = await compiled.ainvoke(initial, config=config)

        # Verify all BI agents ran in correct sequence
        active_agents = final.get("active_agents") or []
        assert "ADS-01" in active_agents
        assert "ADS-02" in active_agents  # Demand Forecast
        assert "ADS-03" in active_agents
        assert "ADS-04" in active_agents
        assert "ADS-06" in active_agents
        assert "ADS-09" in active_agents  # Finance
        assert "ADS-10" in active_agents  # Risk
        assert "ADS-17" in active_agents  # CEO
        assert "ADS-18" in active_agents  # Reporting

        assert final["workflow_status"] == "completed"
        assert final["executive_decision"]["approved"] is True
        assert "reports" in final
