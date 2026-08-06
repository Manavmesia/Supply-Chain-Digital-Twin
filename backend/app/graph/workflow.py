"""
Supply Chain LangGraph Workflow

Assembles the StateGraph for Phase 4 — Business Intelligence.

Graph topology:
    START
      → order_management
      → inventory
           ↓ (stock ok)       ↓ (out of stock)
       warehouse           supplier
           ↓                   ↓
       transportation ←────────┘
           ↓
       finance
           ↓
       risk
           ↓
       demand_forecast
           ↓
       ceo
           ↓
       reporting
           ↓
       END

Conditional edges read state["next_node"] to decide routing.
Each node is a wrapper that calls agent.run(state) and merges the partial update.
"""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.business.demand_forecast import DemandForecastAgent
from app.agents.business.finance import FinanceAgent
from app.agents.business.risk import RiskAgent
from app.agents.coordination.ceo import CEOAgent
from app.agents.coordination.reporting import ReportingAgent
from app.agents.operational.inventory import InventoryAgent
from app.agents.operational.order_management import OrderManagementAgent
from app.agents.operational.supplier import SupplierAgent
from app.agents.operational.transportation import TransportationAgent
from app.agents.operational.warehouse import WarehouseAgent
from app.agents.operational.manufacturing import ManufacturingAgent
from app.agents.operational.customer_service import CustomerServiceAgent
from app.graph.state import SupplyChainState


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

    session_factory is a zero-argument async callable that returns an AsyncSession.
    If None the agent runs without a DB session (useful for unit tests).
    trace_collector is a list; if provided, each agent appends a trace entry.
    """
    import time
    from datetime import datetime, timezone

    # Keys that are too verbose / not useful for agent I/O inspection
    _SKIP_KEYS = {"messages"}
    # Keys that are big lists — truncate to last N entries in snapshot
    _TRUNCATE_KEYS = {"event_history", "active_agents", "decisions", "errors"}
    _TRUNCATE_N = 3

    def _snapshot(state: dict) -> dict:
        """Extract a concise, JSON-safe snapshot of state for tracing."""
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

        # Snapshot what the agent RECEIVES as input
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
# Conditional routing functions
# ---------------------------------------------------------------------------

def route_after_inventory(state: SupplyChainState) -> str:
    """Route to warehouse if stock is available, else to supplier."""
    next_node = state.get("next_node")
    if next_node in ("supplier", "warehouse"):
        return next_node
    # Default: if any inventory out_of_stock → supplier; else warehouse
    inventory = state.get("inventory") or {}
    for _, data in inventory.items():
        if isinstance(data, dict) and data.get("status") == "out_of_stock":
            return "supplier"
    return "warehouse"


def route_after_order_management(state: SupplyChainState) -> str:
    """Abort to END if order was rejected."""
    if state.get("workflow_status") == "failed":
        return END
    return "demand_forecast"


def route_after_supplier(state: SupplyChainState) -> str:
    """After supplier node, always proceed to transportation."""
    return "transportation"


def route_after_ceo(state: SupplyChainState) -> str:
    """Always proceed to reporting after CEO decision (approved or denied)."""
    return "reporting"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_workflow(
    session_factory=None,
    publisher=None,
    trace_collector=None,
) -> StateGraph:
    """
    Assemble and compile the LangGraph StateGraph.

    Args:
        session_factory:  async callable → AsyncSession (or None for tests)
        publisher:        EventPublisher instance (or None for tests)
        trace_collector:  list to collect per-agent input/output traces

    Returns:
        Compiled LangGraph app (callable as ``app.ainvoke(state, config)``)
    """

    graph = StateGraph(SupplyChainState)

    def _node(cls):
        """Shorthand: build node with shared session/publisher/trace_collector."""
        return _make_node(cls, session_factory, publisher, trace_collector)

    # ── Add Phase 3 nodes ─────────────────────────────────────────────────────
    graph.add_node("order_management", _node(OrderManagementAgent))
    graph.add_node("inventory",        _node(InventoryAgent))
    graph.add_node("warehouse",        _node(WarehouseAgent))
    graph.add_node("supplier",         _node(SupplierAgent))
    graph.add_node("transportation",   _node(TransportationAgent))
    graph.add_node("ceo",              _node(CEOAgent))

    # ── Add Phase 4 nodes ─────────────────────────────────────────────────────
    graph.add_node("finance",          _node(FinanceAgent))
    graph.add_node("risk",             _node(RiskAgent))
    graph.add_node("demand_forecast",  _node(DemandForecastAgent))
    graph.add_node("reporting",        _node(ReportingAgent))
    graph.add_node("customer_service", _node(CustomerServiceAgent))
    graph.add_node("manufacturing",    _node(ManufacturingAgent))

    # ── Entry ─────────────────────────────────────────────────────────────────
    graph.add_edge(START, "order_management")

    # ── Conditional: order_management → demand_forecast OR END ───────────────
    graph.add_conditional_edges(
        "order_management",
        route_after_order_management,
        {"demand_forecast": "demand_forecast", END: END},
    )

    # ── Demand Forecast → inventory ───────────────────────────────────────────
    graph.add_edge("demand_forecast", "inventory")

    # ── Conditional: inventory → warehouse OR supplier ────────────────────────
    graph.add_conditional_edges(
        "inventory",
        route_after_inventory,
        {"warehouse": "warehouse", "supplier": "supplier"},
    )

    # ── Warehouse → transportation (always) ───────────────────────────────────
    graph.add_edge("warehouse", "transportation")

    # ── Supplier → transportation (always) ────────────────────────────────────
    graph.add_conditional_edges(
        "supplier",
        route_after_supplier,
        {"transportation": "transportation"},
    )

    # ── Transportation → finance (Phase 4 sequential BI chain) ───────────────
    graph.add_edge("transportation", "finance")

    # ── Finance → risk → ceo ──────────────────────────────────────────────────
    graph.add_edge("finance", "risk")
    graph.add_edge("risk", "ceo")

    # ── CEO → reporting (Phase 4) ─────────────────────────────────────────────
    graph.add_conditional_edges(
        "ceo",
        route_after_ceo,
        {"reporting": "reporting"},
    )

    # ── Reporting → END ──────────────────────────────────────────────────────
    graph.add_edge("reporting", END)

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
