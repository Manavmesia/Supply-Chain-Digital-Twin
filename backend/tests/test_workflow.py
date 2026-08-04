"""
Integration tests for the LangGraph workflow graph (Phase 3).

Tests the complete graph compilation, routing logic, and state transitions
without a real database or message broker.  All agent._execute() calls are
monkey-patched so the graph wiring is tested, not agent business logic.
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.graph.state import SupplyChainState
from app.graph.workflow import (
    build_workflow,
    compile_workflow,
    route_after_ceo,
    route_after_inventory,
    route_after_order_management,
    route_after_supplier,
)


# ── Helper ────────────────────────────────────────────────────────────────────

def _base_state(**overrides) -> SupplyChainState:
    state: SupplyChainState = {
        "workflow_id": str(uuid.uuid4()),
        "correlation_id": str(uuid.uuid4()),
        "workflow_status": "received",
        "active_agents": [],
        "event_history": [],
        "decisions": [],
        "errors": [],
        "messages": [],
        "retries": {},
        "order": {
            "customer_id": str(uuid.uuid4()),
            "items": [{"product_id": str(uuid.uuid4()), "quantity": 2}],
            "priority": "standard",
            "total_amount": "5000.00",
        },
    }
    state.update(overrides)
    return state


# =============================================================================
# Routing function unit tests (no DB/graph needed)
# =============================================================================

class TestRoutingFunctions:
    def test_route_order_management_success_goes_to_demand_forecast(self):
        state = _base_state(workflow_status="operational")
        assert route_after_order_management(state) == "demand_forecast"

    def test_route_order_management_failure_goes_to_end(self):
        from langgraph.graph import END
        state = _base_state(workflow_status="failed")
        assert route_after_order_management(state) == END

    def test_route_inventory_with_next_node_warehouse(self):
        state = _base_state(next_node="warehouse")
        assert route_after_inventory(state) == "warehouse"

    def test_route_inventory_with_next_node_supplier(self):
        state = _base_state(next_node="supplier")
        assert route_after_inventory(state) == "supplier"

    def test_route_inventory_detects_out_of_stock_without_next_node(self):
        pid = str(uuid.uuid4())
        state = _base_state(
            inventory={pid: {"status": "out_of_stock"}},
        )
        # Remove next_node if present
        state.pop("next_node", None)
        assert route_after_inventory(state) == "supplier"

    def test_route_inventory_defaults_to_warehouse_when_all_reserved(self):
        pid = str(uuid.uuid4())
        state = _base_state(
            inventory={pid: {"status": "reserved", "warehouse_id": str(uuid.uuid4())}},
        )
        state.pop("next_node", None)
        assert route_after_inventory(state) == "warehouse"

    def test_route_after_ceo_goes_to_reporting(self):
        state = _base_state()
        assert route_after_ceo(state) == "reporting"

    def test_route_after_supplier_always_transportation(self):
        state = _base_state()
        assert route_after_supplier(state) == "transportation"


# =============================================================================
# Graph compilation test
# =============================================================================

class TestGraphCompilation:
    def test_graph_compiles_without_error(self):
        compiled = compile_workflow(session_factory=None, publisher=None)
        assert compiled is not None

    def test_compiled_graph_has_invoke_method(self):
        compiled = compile_workflow(session_factory=None, publisher=None)
        assert hasattr(compiled, "ainvoke")

    def test_graph_node_names(self):
        graph = build_workflow(session_factory=None, publisher=None)
        # After build, nodes are in the graph's node definitions
        assert "order_management" in graph.nodes
        assert "inventory" in graph.nodes
        assert "warehouse" in graph.nodes
        assert "supplier" in graph.nodes
        assert "transportation" in graph.nodes
        assert "ceo" in graph.nodes


# =============================================================================
# Full workflow integration tests (mocked _execute)
# =============================================================================

class TestWorkflowHappyPath:
    """
    Happy path: sufficient inventory → warehouse → transportation → CEO approve.
    """

    @pytest.mark.asyncio
    async def test_happy_path_workflow(self):
        """
        Mock each agent._execute to return pre-built partial states.
        Verify the final state reflects a completed workflow with correct
        agent sequence and CEO approval.
        """
        order_id = str(uuid.uuid4())
        product_id = str(uuid.uuid4())
        warehouse_id = str(uuid.uuid4())
        shipment_id = str(uuid.uuid4())

        order_state = {
            "order_id": order_id,
            "customer_id": str(uuid.uuid4()),
            "status": "pending",
            "priority": "standard",
            "total_amount": "5000.00",
            "currency": "USD",
            "items": [{"product_id": product_id, "quantity": 2}],
        }

        with (
            patch(
                "app.agents.operational.order_management.OrderManagementAgent._execute",
                new=AsyncMock(return_value={
                    "order": order_state,
                    "customer": {"name": "Acme"},
                    "workflow_status": "operational",
                    "decisions": [{"agent": "ADS-01", "action": "order_created"}],
                    "event_history": [{"event_type": "OrderCreated"}],
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
                    "order": {**order_state, "status": "warehouse_assigned"},
                    "decisions": [],
                    "event_history": [{"event_type": "ShipmentReady"}],
                }),
            ),
            patch(
                "app.agents.operational.transportation.TransportationAgent._execute",
                new=AsyncMock(return_value={
                    "shipment": {"shipment_id": shipment_id, "status": "dispatched", "eta": "2026-08-10T00:00:00Z"},
                    "order": {**order_state, "status": "in_transit"},
                    "decisions": [],
                    "event_history": [{"event_type": "ShipmentCreated"}, {"event_type": "ShipmentDispatched"}],
                }),
            ),
            patch(
                "app.agents.coordination.ceo.CEOAgent._execute",
                new=AsyncMock(return_value={
                    "executive_decision": {"approved": True, "approval_tier": "auto"},
                    "order": {**order_state, "status": "delivered"},
                    "workflow_status": "completed",
                    "decisions": [],
                    "event_history": [{"event_type": "CEOApprovalGranted"}],
                }),
            ),
        ):
            compiled = compile_workflow(session_factory=None, publisher=None)
            initial = _base_state(
                order={
                    "customer_id": str(uuid.uuid4()),
                    "items": [{"product_id": product_id, "quantity": 2}],
                    "priority": "standard",
                }
            )
            config = {"configurable": {"thread_id": str(uuid.uuid4())}}
            final = await compiled.ainvoke(initial, config=config)

        assert final["workflow_status"] == "completed"
        assert final["executive_decision"]["approved"] is True
        assert "ADS-01" in final["active_agents"]
        assert "ADS-17" in final["active_agents"]


class TestWorkflowOutOfStockPath:
    """
    Out-of-stock path: inventory fails → supplier → transportation → CEO.
    """

    @pytest.mark.asyncio
    async def test_out_of_stock_uses_supplier_node(self):
        order_id = str(uuid.uuid4())
        product_id = str(uuid.uuid4())

        order_state = {
            "order_id": order_id,
            "status": "pending",
            "priority": "standard",
            "total_amount": "8000.00",
            "items": [{"product_id": product_id, "quantity": 50}],
        }

        with (
            patch(
                "app.agents.operational.order_management.OrderManagementAgent._execute",
                new=AsyncMock(return_value={
                    "order": order_state,
                    "workflow_status": "operational",
                    "decisions": [],
                    "event_history": [{"event_type": "OrderCreated"}],
                }),
            ),
            patch(
                "app.agents.operational.inventory.InventoryAgent._execute",
                new=AsyncMock(return_value={
                    "inventory": {product_id: {"status": "out_of_stock"}},
                    "next_node": "supplier",
                    "decisions": [],
                    "event_history": [{"event_type": "InventoryOutOfStock"}],
                }),
            ),
            patch(
                "app.agents.operational.supplier.SupplierAgent._execute",
                new=AsyncMock(return_value={
                    "supplier": {"status": "selected", "purchase_orders": []},
                    "decisions": [],
                    "event_history": [{"event_type": "SupplierSelected"}, {"event_type": "PurchaseOrderCreated"}],
                    "next_node": "transportation",
                }),
            ),
            patch(
                "app.agents.operational.transportation.TransportationAgent._execute",
                new=AsyncMock(return_value={
                    "shipment": {"shipment_id": str(uuid.uuid4()), "status": "dispatched"},
                    "decisions": [],
                    "event_history": [{"event_type": "ShipmentCreated"}],
                }),
            ),
            patch(
                "app.agents.coordination.ceo.CEOAgent._execute",
                new=AsyncMock(return_value={
                    "executive_decision": {"approved": True, "approval_tier": "auto"},
                    "workflow_status": "completed",
                    "decisions": [],
                    "event_history": [{"event_type": "CEOApprovalGranted"}],
                }),
            ),
        ):
            compiled = compile_workflow(session_factory=None, publisher=None)
            initial = _base_state(order={
                "customer_id": str(uuid.uuid4()),
                "items": [{"product_id": product_id, "quantity": 50}],
                "priority": "standard",
            })
            config = {"configurable": {"thread_id": str(uuid.uuid4())}}
            final = await compiled.ainvoke(initial, config=config)

        assert final["workflow_status"] == "completed"
        # Both supplier and transportation must have run
        assert "ADS-05" in final["active_agents"]
        assert "ADS-06" in final["active_agents"]
        # The executive_decision should reflect approval
        assert final.get("executive_decision", {}).get("approved") is True


class TestWorkflowOrderRejectedPath:
    """
    Order rejected: order_management fails → workflow terminates without hitting inventory.
    """

    @pytest.mark.asyncio
    async def test_rejected_order_terminates_early(self):
        with (
            patch(
                "app.agents.operational.order_management.OrderManagementAgent._execute",
                new=AsyncMock(return_value={
                    "workflow_status": "failed",
                    "decisions": [{"action": "order_rejected", "reason": "Customer not found"}],
                    "event_history": [{"event_type": "OrderRejected"}],
                    "next_node": "END",
                }),
            ),
            patch(
                "app.agents.operational.inventory.InventoryAgent._execute",
                new=AsyncMock(side_effect=AssertionError("Inventory should NOT be called")),
            ),
        ):
            compiled = compile_workflow(session_factory=None, publisher=None)
            initial = _base_state()
            config = {"configurable": {"thread_id": str(uuid.uuid4())}}
            final = await compiled.ainvoke(initial, config=config)

        assert final["workflow_status"] == "failed"
        assert "ADS-03" not in (final.get("active_agents") or [])
