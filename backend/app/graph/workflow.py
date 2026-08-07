"""
Supply Chain LangGraph Workflow

Assembles the StateGraph for Phase 5 — Decentralized Peer-to-Peer Multi-Agent Loop.

Graph topology:
    START
      → order_management (intake)
           ↓
      → demand_forecast (loop start)
      → inventory
      → warehouse / supplier
      → transportation
      → sustainability
      → quality_assurance
      → finance
      → pricing
      → risk
      → procurement_strategy
      → planner
      → negotiation
           ↓
      → consensus_checker (evaluates blackboard consensus/objections)
           ↓ (if contested & loop_count < 3)  → loops back to demand_forecast
           ↓ (if consensus reached or limit)   → customer_service
      → customer_service
      → manufacturing (remanufacture if QA/Planner triggered)
      → reporting (audit)
      → END
"""

from __future__ import annotations

from typing import Any
from datetime import datetime, timezone

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.business.demand_forecast import DemandForecastAgent
from app.agents.business.finance import FinanceAgent
from app.agents.business.pricing import PricingAgent
from app.agents.business.procurement_strategy import ProcurementStrategyAgent
from app.agents.business.quality_assurance import QualityAssuranceAgent
from app.agents.business.risk import RiskAgent
from app.agents.business.sustainability import SustainabilityAgent
from app.agents.coordination.ceo import CEOAgent
from app.agents.coordination.negotiation import NegotiationAgent
from app.agents.coordination.planner import PlannerAgent
from app.agents.coordination.reporting import ReportingAgent
from app.agents.operational.customer_service import CustomerServiceAgent
from app.agents.operational.inventory import InventoryAgent
from app.agents.operational.manufacturing import ManufacturingAgent
from app.agents.operational.order_management import OrderManagementAgent
from app.agents.operational.supplier import SupplierAgent
from app.agents.operational.transportation import TransportationAgent
from app.agents.operational.warehouse import WarehouseAgent
from app.graph.state import SupplyChainState, BlackboardEntry


# ---------------------------------------------------------------------------
# Node factory — creates a bound async callable for each agent
# ---------------------------------------------------------------------------

def _make_node(agent_cls, session_factory=None, publisher=None, trace_collector=None):
    """
    Return an async function that:
      1. Creates a new agent instance (with session + publisher injected)
      2. Calls agent.run(state)
      3. Records input snapshot + output diff in trace_collector (if provided)
      4. Returns the partial state update
    """
    import time
    from datetime import datetime, timezone

    _SKIP_KEYS = {"messages"}
    _TRUNCATE_KEYS = {"event_history", "active_agents", "decisions", "errors"}
    _TRUNCATE_N = 3

    def _snapshot(state: dict) -> dict:
        snap = {}
        for k, v in state.items():
            if k in _SKIP_KEYS:
                continue
            if k in _TRUNCATE_KEYS and isinstance(v, list):
                snap[k] = v[-_TRUNCATE_N:] if v else []
                snap[k + "__total"] = len(v)
            else:
                snap[k] = v
        return snap

    async def node_fn(state: SupplyChainState) -> dict[str, Any]:
        t_start = time.perf_counter()
        started_at = datetime.now(tz=timezone.utc).isoformat()

        input_snapshot = _snapshot(dict(state))

        session = await session_factory() if session_factory else None
        agent = agent_cls(session=session, publisher=publisher)
        output = await agent.run(state)

        duration_ms = round((time.perf_counter() - t_start) * 1000, 1)
        finished_at = datetime.now(tz=timezone.utc).isoformat()

        if trace_collector is not None:
            trace_collector.append({
                "agent_code": agent_cls.agent_code,
                "agent_name": agent_cls.agent_name,
                "started_at": started_at,
                "finished_at": finished_at,
                "duration_ms": duration_ms,
                "status": "failed" if output.get("workflow_status") == "failed" else "completed",
                "input": input_snapshot,
                "output": {k: v for k, v in output.items() if k not in _SKIP_KEYS},
                "decision": next(
                    (d for d in reversed(output.get("decisions") or [])
                     if d.get("agent") == agent_cls.agent_code),
                    None,
                ),
                "events_published": [
                    e for e in (output.get("event_history") or [])
                     if e.get("source_agent") == agent_cls.agent_code
                ],
            })

        return output

    node_fn.__name__ = agent_cls.agent_code
    return node_fn


# ---------------------------------------------------------------------------
# Decentralized Loop & Consensus Checker
# ---------------------------------------------------------------------------

async def consensus_checker(state: SupplyChainState) -> dict[str, Any]:
    """
    Evaluates the Blackboard status:
      - If there are any active contested topics and loop_count < 2, increment loop and retry.
      - If loops are exhausted and topics remain contested, escalate to human.
      - Otherwise, commit consensus.
    """
    blackboard = state.get("blackboard") or {}
    loop_count = state.get("loop_count", 0)

    has_contested = False
    contested_topics = []
    for topic, entries in blackboard.items():
        for entry in entries:
            if entry.get("status") == "contested":
                has_contested = True
                contested_topics.append(topic)
                break

    if has_contested:
        if loop_count < 2:
            return {
                "loop_count": loop_count + 1,
                "next_node": "demand_forecast",
            }
        else:
            return {
                "workflow_status": "escalated",
                "requires_human_approval": True,
                "next_node": "customer_service",
            }

    return {
        "workflow_status": "completed",
        "next_node": "customer_service",
    }


def route_after_consensus_checker(state: SupplyChainState) -> str:
    """Return the designated next node based on consensus checker result."""
    return state.get("next_node") or "customer_service"


# ---------------------------------------------------------------------------
# Existing Routing helpers
# ---------------------------------------------------------------------------

def route_after_inventory(state: SupplyChainState) -> str:
    next_node = state.get("next_node")
    if next_node in ("supplier", "warehouse"):
        return next_node
    inventory = state.get("inventory") or {}
    for _, data in inventory.items():
        if isinstance(data, dict) and data.get("status") == "out_of_stock":
            return "supplier"
    return "warehouse"


def route_after_order_management(state: SupplyChainState) -> str:
    if state.get("workflow_status") == "failed":
        return END
    return "demand_forecast"


def route_after_supplier(state: SupplyChainState) -> str:
    return "transportation"


def route_after_customer_service(state: SupplyChainState) -> str:
    planning = state.get("planning") or {}
    if planning.get("remanufacture_required"):
        return "manufacturing"
    return "reporting"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_workflow(
    session_factory=None,
    publisher=None,
    trace_collector=None,
) -> StateGraph:
    """Assemble and compile the LangGraph StateGraph."""
    graph = StateGraph(SupplyChainState)

    def _node(cls):
        return _make_node(cls, session_factory, publisher, trace_collector)

    # ── Operational Nodes ─────────────────────────────────────────────────────
    graph.add_node("order_management", _node(OrderManagementAgent))
    graph.add_node("inventory",        _node(InventoryAgent))
    graph.add_node("warehouse",        _node(WarehouseAgent))
    graph.add_node("supplier",         _node(SupplierAgent))
    graph.add_node("transportation",   _node(TransportationAgent))
    graph.add_node("manufacturing",    _node(ManufacturingAgent))
    graph.add_node("customer_service", _node(CustomerServiceAgent))
    graph.add_node("legacy_ceo_compat", _node(CEOAgent))

    # ── BI Nodes ─────────────────────────────────────────────────────────────
    graph.add_node("demand_forecast",      _node(DemandForecastAgent))
    graph.add_node("sustainability",       _node(SustainabilityAgent))
    graph.add_node("quality_assurance",    _node(QualityAssuranceAgent))
    graph.add_node("finance",              _node(FinanceAgent))
    graph.add_node("pricing",              _node(PricingAgent))
    graph.add_node("risk",                 _node(RiskAgent))
    graph.add_node("procurement_strategy", _node(ProcurementStrategyAgent))
    graph.add_node("planner",              _node(PlannerAgent))
    graph.add_node("negotiation",          _node(NegotiationAgent))

    # ── Coordination & Consensus ──────────────────────────────────────────────
    graph.add_node("consensus_checker", consensus_checker)
    graph.add_node("reporting",         _node(ReportingAgent))

    # ── Flow connections ────────────────--------------------------------──────
    graph.add_edge(START, "order_management")

    graph.add_conditional_edges(
        "order_management",
        route_after_order_management,
        {"demand_forecast": "demand_forecast", END: END},
    )

    graph.add_edge("demand_forecast", "inventory")

    graph.add_conditional_edges(
        "inventory",
        route_after_inventory,
        {"warehouse": "warehouse", "supplier": "supplier"},
    )

    graph.add_edge("warehouse", "transportation")

    graph.add_conditional_edges(
        "supplier",
        route_after_supplier,
        {"transportation": "transportation"},
    )

    # Parallel pipeline review loop
    graph.add_edge("transportation",       "sustainability")
    graph.add_edge("sustainability",       "quality_assurance")
    graph.add_edge("quality_assurance",    "finance")
    graph.add_edge("finance",              "pricing")
    graph.add_edge("pricing",              "risk")
    graph.add_edge("risk",                 "procurement_strategy")
    graph.add_edge("procurement_strategy", "planner")
    graph.add_edge("planner",              "negotiation")
    
    # Negotiation routes to consensus evaluator
    graph.add_edge("negotiation", "consensus_checker")

    # Consensus evaluator conditional edge
    graph.add_conditional_edges(
        "consensus_checker",
        route_after_consensus_checker,
        {"demand_forecast": "demand_forecast", "customer_service": "customer_service"},
    )

    graph.add_conditional_edges(
        "customer_service",
        route_after_customer_service,
        {"reporting": "reporting", "manufacturing": "manufacturing"},
    )

    graph.add_edge("manufacturing", "reporting")
    graph.add_edge("reporting", "legacy_ceo_compat")
    graph.add_edge("legacy_ceo_compat", END)

    return graph


def compile_workflow(session_factory=None, publisher=None, trace_collector=None):
    """Build and compile the workflow graph with in-memory checkpointing."""
    graph = build_workflow(
        session_factory=session_factory,
        publisher=publisher,
        trace_collector=trace_collector,
    )
    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)
