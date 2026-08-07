"""
SupplyChainState — the single shared object passed between all LangGraph nodes.

Refactored for the Decentralized Multi-Agent architecture:
  - Adds a versioned `blackboard` dictionary containing typed proposals/reviews/commits.
  - Adds a `human_overrides` dictionary to lock/pin decisions from the UI.
  - Adds loop metrics to prevent infinite agent reasoning cycles.
"""

from __future__ import annotations

from typing import Annotated, Any, TypedDict
from langgraph.graph import add_messages


class BlackboardEntry(TypedDict):
    """
    A single versioned entry on the shared blackboard.
    """
    agent_id: str                   # Agent code that posted this entry (e.g. ADS-01)
    timestamp: str                  # ISO timestamp
    confidence: float               # Confidence score (0.0 to 1.0)
    rationale: str                  # LLM reasoning or policy description
    status: str                     # "proposed" | "contested" | "accepted" | "superseded"
    data: dict[str, Any]            # Topic-specific payload (e.g. proposed carrier info)
    message_type: str | None        # Optional protocol type such as PROPOSE/OBJECT/COMMIT
    topic: str | None               # Optional topic name for easier filtering


class OrderItemInput(TypedDict):
    """A single line item inside an incoming order request."""
    product_id: str
    quantity: int
    unit_price: float | None          # resolved by Order Management from DB


class SupplyChainState(TypedDict, total=False):
    """
    Global workflow state shared across all decentralized agent nodes.
    """

    # ── Decentralized Blackboard Store ────────────────────────────────────────
    blackboard: dict[str, list[BlackboardEntry]]  # Versioned logs per topic
    human_overrides: dict[str, dict[str, Any]]    # Locked override mappings from UI
    loop_count: int                               # Cycle detector for consensus loops

    # ── Workflow identity ────────────────────────────────────────────────────
    workflow_id: str                  # UUID assigned at workflow start
    correlation_id: str               # Trace across service boundaries
    current_node: str                 # Name of currently-executing node
    active_agents: list[str]          # Agent codes that have run (e.g. ADS-01)

    # ── Legacy/Flat fields (maintained for backward compatibility) ────────────
    order: dict[str, Any]             # Order header + items + status
    customer: dict[str, Any]          # Customer record fetched from DB
    inventory: dict[str, Any]         # Availability map {product_id: available_qty}
    warehouse: dict[str, Any]         # Assigned warehouse details
    supplier: dict[str, Any]          # Selected supplier + PO info
    shipment: dict[str, Any]          # Shipment record + carrier + ETA
    finance: dict[str, Any]           # Budget analysis, approval status
    risk: dict[str, Any]              # Risk scores and flags
    forecast: dict[str, Any]          # Demand forecast output
    quality: dict[str, Any]           # QA inspection result
    sustainability: dict[str, Any]    # CO2 / sustainability metrics
    manufacturing: dict[str, Any]     # Production orders & capacity state
    customer_service: dict[str, Any]  # Customer notifications & support tickets
    pricing: dict[str, Any]           # Dynamic pricing recommendations (ADS-11)
    procurement: dict[str, Any]       # Procurement strategy + contract alerts (ADS-12)

    # ── Coordination ─────────────────────────────────────────────────────────
    decisions: list[dict[str, Any]]   # Ordered list of agent decisions
    executive_decision: dict[str, Any]  # CEO approval record
    reports: dict[str, Any]           # Generated report metadata and snapshot
    planning: dict[str, Any]          # Execution plan from Planner Agent (ADS-15)
    negotiation: dict[str, Any]       # Negotiation outcome from Negotiation Agent (ADS-16)

    # ── Event / message bus ──────────────────────────────────────────────────
    event_history: list[dict[str, Any]]   # Events published during this workflow
    messages: Annotated[list, add_messages]  # LangChain message history (for LLM phase)

    # ── Error handling ───────────────────────────────────────────────────────
    retries: dict[str, int]           # {node_name: retry_count}
    errors: list[dict[str, Any]]      # Structured error records

    # ── Routing signals ──────────────────────────────────────────────────────
    next_node: str | None             # Explicit override set by conditional edges
    workflow_status: str              # received → validated → operational → completed/failed/escalated
    requires_human_approval: bool     # Escalation toggle
