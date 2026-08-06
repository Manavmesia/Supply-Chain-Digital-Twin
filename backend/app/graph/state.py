"""
SupplyChainState — the single shared object passed between all LangGraph nodes.

Defined exactly as specified in LangGraph Workflow Document §2.
All fields are optional so every node only populates what it knows.
"""

from __future__ import annotations

from typing import Annotated, Any
from langgraph.graph import add_messages
from typing_extensions import TypedDict


class OrderItemInput(TypedDict):
    """A single line item inside an incoming order request."""
    product_id: str
    quantity: int
    unit_price: float | None          # resolved by Order Management from DB


class SupplyChainState(TypedDict, total=False):
    """
    Global workflow state shared across all agent nodes.

    All fields are optional (total=False) so nodes only update the
    slices they own.  LangGraph merges partial updates automatically.
    """

    # ── Workflow identity ────────────────────────────────────────────────────
    workflow_id: str                  # UUID assigned at workflow start
    correlation_id: str               # Trace across service boundaries
    current_node: str                 # Name of currently-executing node
    active_agents: list[str]          # Agent codes that have run (e.g. ADS-01)

    # ── Order ────────────────────────────────────────────────────────────────
    order: dict[str, Any]             # Order header + items + status
    customer: dict[str, Any]          # Customer record fetched from DB

    # ── Inventory ────────────────────────────────────────────────────────────
    inventory: dict[str, Any]         # Availability map {product_id: available_qty}

    # ── Warehouse ────────────────────────────────────────────────────────────
    warehouse: dict[str, Any]         # Assigned warehouse details

    # ── Supplier / Procurement ───────────────────────────────────────────────
    supplier: dict[str, Any]          # Selected supplier + PO info

    # ── Shipment / Transportation ────────────────────────────────────────────
    shipment: dict[str, Any]          # Shipment record + carrier + ETA

    # ── Business agents (Phase 4 & 5) ────────────────────────────────────────
    finance: dict[str, Any]           # Budget analysis, approval status
    risk: dict[str, Any]              # Risk scores and flags
    forecast: dict[str, Any]          # Demand forecast output
    quality: dict[str, Any]           # QA inspection result
    sustainability: dict[str, Any]    # CO2 / sustainability metrics
    manufacturing: dict[str, Any]     # Production orders & capacity state
    customer_service: dict[str, Any]  # Customer notifications & support tickets

    # ── Coordination ─────────────────────────────────────────────────────────
    decisions: list[dict[str, Any]]   # Ordered list of agent decisions
    executive_decision: dict[str, Any]  # CEO approval record
    reports: dict[str, Any]           # Generated report metadata and snapshot

    # ── Event / message bus ──────────────────────────────────────────────────
    event_history: list[dict[str, Any]]   # Events published during this workflow
    messages: Annotated[list, add_messages]  # LangChain message history (for LLM phase)

    # ── Error handling ───────────────────────────────────────────────────────
    retries: dict[str, int]           # {node_name: retry_count}
    errors: list[dict[str, Any]]      # Structured error records

    # ── Routing signals ──────────────────────────────────────────────────────
    next_node: str | None             # Explicit override set by conditional edges
    workflow_status: str              # received → validated → operational → completed/failed
    requires_human_approval: bool     # Set by CEO when amount > $500k
