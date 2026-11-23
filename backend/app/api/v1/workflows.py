"""
Workflow API endpoints — Phase 3 + Trace

POST /api/v1/workflows/orders
    Accepts an order request, initialises shared state, and runs the
    supply chain workflow as a background asyncio task.

GET /api/v1/workflows/{workflow_id}
    Returns the current workflow state from the in-memory checkpoint store.

GET /api/v1/workflows/{workflow_id}/trace
    Returns per-agent input/output traces captured during execution.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Annotated, Any, Literal

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.v1.auth import require_authenticated_role

from app.core import persistence
from app.core.catalog import BASELINE_CUSTOMERS, BASELINE_PRODUCTS
from app.core.database import AsyncSessionLocal
from app.core.execution_config import get_agent_delay, set_agent_delay
from app.core.standby_session import create_standby_session, is_database_connected
from app.events.dispatcher import dispatch_event
from app.graph.state import SupplyChainState
from app.graph.workflow import compile_workflow
from app.schemas.order_request import (
    OrderWorkflowRequest,
    WorkflowAcceptedResponse,
    WorkflowStatusResponse,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/workflows", tags=["workflows"])

# ---------------------------------------------------------------------------
# Bounded in-process state stores (LRU eviction protects against memory DoS)
# ---------------------------------------------------------------------------

_WORKFLOW_STORE: dict[str, dict[str, Any]] = {}
_TRACE_STORE: dict[str, list[dict[str, Any]]] = {}
_MAX_WORKFLOW_STORE_SIZE = 500


def _save_workflow_state(
    wf_id: str,
    state: dict[str, Any],
    trace: list[dict[str, Any]] | None = None,
) -> None:
    if len(_WORKFLOW_STORE) >= _MAX_WORKFLOW_STORE_SIZE and wf_id not in _WORKFLOW_STORE:
        oldest_key = next(iter(_WORKFLOW_STORE))
        _WORKFLOW_STORE.pop(oldest_key, None)
        _TRACE_STORE.pop(oldest_key, None)
    _WORKFLOW_STORE[wf_id] = state
    if trace is not None:
        _TRACE_STORE[wf_id] = trace
    try:
        current_trace = trace if trace is not None else _TRACE_STORE.get(wf_id)
        persistence.save_workflow(wf_id, state, current_trace)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to persist workflow state", workflow_id=wf_id, error=str(exc))


# ---------------------------------------------------------------------------
# Background workflow runner
# ---------------------------------------------------------------------------

_MAX_CONCURRENT_WORKFLOWS = 10
_WORKFLOW_SEMAPHORE = asyncio.Semaphore(_MAX_CONCURRENT_WORKFLOWS)


async def _run_workflow(workflow_id: str, correlation_id: str, request: OrderWorkflowRequest | None = None) -> None:
    async with _WORKFLOW_SEMAPHORE:
        await _run_workflow_inner(workflow_id, correlation_id, request)


async def _run_workflow_inner(workflow_id: str, correlation_id: str, request: OrderWorkflowRequest | None = None) -> None:
    """
    Executes or resumes the decentralized supply chain workflow.
    """
    existing_state = _WORKFLOW_STORE.get(workflow_id) or persistence.get_workflow(workflow_id)
    if existing_state:
        initial_state = dict(existing_state)
        initial_state["loop_count"] = 0
        initial_state["next_node"] = None
        initial_state["workflow_status"] = "running"
        initial_state["requires_human_approval"] = False
    else:
        if request is None:
            raise ValueError("request must be provided for new workflows")
        initial_state = {
            "workflow_id": workflow_id,
            "correlation_id": correlation_id,
            "workflow_status": "running",
            "active_agents": [],
            "event_history": [],
            "decisions": [],
            "errors": [],
            "messages": [],
            "retries": {},
            "blackboard": {},
            "human_overrides": {},
            "loop_count": 0,
            "order": {
                "order_id": getattr(request, "order_id", None) or f"ord-{workflow_id[:8]}",
                "customer_id": str(request.customer_id),
                "items": [
                    {"product_id": str(i.product_id), "quantity": i.quantity}
                    for i in request.items
                ],
            },
        }

    _save_workflow_state(workflow_id, {**initial_state, "workflow_status": "running"})

    # Create/retrieve trace collector
    trace = _TRACE_STORE.get(workflow_id)
    if trace is None:
        trace = persistence.get_workflow_trace(workflow_id)
        _TRACE_STORE[workflow_id] = trace

    effective_delay = getattr(request, "delay_seconds", None) if request else None

    async def _on_step_update(agent_code: str, agent_name: str, status: str, state: dict, trace_entry: dict | None = None):
        step_trace = list(trace)
        if trace_entry and trace_entry not in step_trace:
            step_trace.append(trace_entry)
        _save_workflow_state(
            workflow_id,
            {
                **state,
                "workflow_status": "running",
                "current_node": agent_code,
                "active_agents": [agent_code] if status == "running" else [],
            },
            step_trace,
        )

    try:
        config = {"configurable": {"thread_id": workflow_id}}
        final_state: dict[str, Any] = {}

        db_available = await is_database_connected()
        if db_available:
            try:
                async with AsyncSessionLocal() as session:
                    async def _session_factory():
                        return session

                    compiled = compile_workflow(
                        session_factory=_session_factory,
                        trace_collector=trace,
                        delay_seconds=effective_delay,
                        on_step_update=_on_step_update,
                    )
                    final_state = await compiled.ainvoke(initial_state, config=config)

                    # Check if any agent recorded a connection failure mid-run
                    has_connection_error = any(
                        "connection" in str(e).lower() or "errno 61" in str(e).lower()
                        for e in final_state.get("errors", [])
                    )
                    if has_connection_error:
                        raise ConnectionRefusedError("Database lost mid-run")

                    if not final_state.get("errors") and final_state.get("workflow_status") != "failed":
                        if final_state.get("workflow_status") != "escalated":
                            final_state["workflow_status"] = "completed"

                    await session.commit()
            except (OSError, ConnectionRefusedError, Exception) as db_exc:
                logger.warning("DB unavailable or failed mid-run, falling back to standby session", error=str(db_exc))
                db_available = False

        if not db_available:
            standby_session = create_standby_session(
                customer_id=uuid.UUID(str(initial_state["order"]["customer_id"])) if initial_state.get("order", {}).get("customer_id") else None,
                items=initial_state.get("order", {}).get("items"),
            )
            async def _standby_factory():
                return standby_session

            trace.clear()
            fallback_initial_state = dict(initial_state)
            fallback_initial_state["errors"] = []
            compiled = compile_workflow(
                session_factory=_standby_factory,
                trace_collector=trace,
                delay_seconds=effective_delay,
                on_step_update=_on_step_update,
            )
            final_state = await compiled.ainvoke(fallback_initial_state, config=config)
            is_escalated = (
                bool(final_state.get("requires_human_approval"))
                or final_state.get("workflow_status") == "escalated"
                or (final_state.get("executive_decision") or {}).get("approval_tier") == "human_required"
            )
            if not final_state.get("errors") and final_state.get("workflow_status") != "failed":
                if is_escalated:
                    final_state["workflow_status"] = "escalated"
                    final_state["requires_human_approval"] = True
                else:
                    final_state["workflow_status"] = "completed"

        # Clear active agents and current node upon workflow completion
        final_state["active_agents"] = []
        final_state["current_node"] = None
        _save_workflow_state(workflow_id, final_state, trace)

        # Synchronize order and shipment database records to reflect final multi-agent decisions
        final_order = final_state.get("order") or {}
        order_id = final_order.get("order_id")
        order_status = final_order.get("status")
        is_escalated = (
            bool(final_state.get("requires_human_approval"))
            or final_state.get("workflow_status") == "escalated"
            or (final_state.get("executive_decision") or {}).get("approval_tier") == "human_required"
        )
        if is_escalated:
            order_status = "pending"
            final_order["status"] = "pending"
            final_state["order"] = final_order
        if order_id and order_status:
            persistence.update_order_status(order_id, order_status)

        final_shipment = final_state.get("shipment") or {}
        if order_id and final_shipment:
            shp = persistence.get_shipment_by_order(order_id)
            if shp:
                shipment_status = "pending" if is_escalated else final_shipment.get("status", "delivered")
                persistence.update_shipment_status(
                    shp["shipment_id"],
                    shipment_status,
                    "Held at Distribution Center Pending Executive Sign-off" if is_escalated else (final_shipment.get("current_location") or "Destination Fulfilled"),
                )

        logger.info(
            "Workflow completed",
            workflow_id=workflow_id,
            status=final_state.get("workflow_status"),
            agents_run=len(trace),
        )

    except Exception as exc:  # noqa: BLE001
        logger.error("Workflow failed", workflow_id=workflow_id, error=str(exc))
        _save_workflow_state(workflow_id, {
            **initial_state,
            "workflow_status": "failed",
            "active_agents": [],
            "current_node": None,
            "errors": [{"error": str(exc)}],
        }, trace)



# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

class WorkflowConfigPayload(BaseModel):
    delay_seconds: float = Field(ge=0.0, le=10.0, description="Delay in seconds between agent calls")


@router.get("/config", summary="Get execution pacing and visual delay configuration")
@router.get("/config/", include_in_schema=False)
async def get_workflow_config() -> dict[str, Any]:
    """Return the current visual execution delay (in seconds) between agent calls."""
    return {
        "delay_seconds": get_agent_delay(),
        "status": "active",
        "description": "Visual delay injected between multi-agent pipeline steps",
    }


@router.post("/config", summary="Set execution pacing and visual delay configuration")
@router.post("/config/", include_in_schema=False)
async def update_workflow_config(
    payload: WorkflowConfigPayload,
) -> dict[str, Any]:
    """Update the global visual delay (in seconds) between agent calls."""
    new_delay = set_agent_delay(payload.delay_seconds)
    return {
        "delay_seconds": new_delay,
        "status": "updated",
        "message": f"Agent execution delay set to {new_delay:.2f}s",
    }


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=WorkflowAcceptedResponse,
    summary="Start a new order fulfilment workflow",
)
@router.post(
    "/",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=WorkflowAcceptedResponse,
    include_in_schema=False,
)
@router.post(
    "/orders",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=WorkflowAcceptedResponse,
    summary="Start a new order fulfilment workflow",
)
@router.post(
    "/orders/",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=WorkflowAcceptedResponse,
    include_in_schema=False,
)
async def start_order_workflow(
    request: OrderWorkflowRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[dict | None, Depends(require_authenticated_role("admin", "operator", "analyst"))] = None,
) -> WorkflowAcceptedResponse:
    """
    Accepts a customer order and starts the supply chain workflow.

    The workflow runs asynchronously in the background. Use the returned
    `workflow_id` to poll `GET /workflows/{workflow_id}` for status,
    and `GET /workflows/{workflow_id}/trace` for per-agent I/O traces.
    """
    workflow_id = str(uuid.uuid4())
    correlation_id = str(uuid.uuid4())

    order_id = getattr(request, "order_id", None) or f"ord-{uuid.uuid4().hex[:12]}"
    request.order_id = order_id

    # Check if order is already saved in persistence
    existing_order = persistence.get_order(order_id)
    if not existing_order:
        cust_id_str = str(request.customer_id)
        cust_name = "Enterprise Client"
        for c in BASELINE_CUSTOMERS:
            if c[0] == cust_id_str:
                cust_name = c[1]
                break

        order_items_records = []
        total_val = 0.0
        for it in request.items:
            pid_str = str(it.product_id)
            pname = "Enterprise Component"
            sku = "SKU-001"
            uprice = 150.0
            for p in BASELINE_PRODUCTS:
                if p[0] == pid_str:
                    sku = p[1]
                    pname = p[2]
                    uprice = float(p[5])
                    break
            ltotal = round(uprice * it.quantity, 2)
            total_val += ltotal
            order_items_records.append({
                "order_item_id": f"item-{uuid.uuid4().hex[:8]}",
                "product_id": pid_str,
                "sku": sku,
                "product_name": pname,
                "quantity": it.quantity,
                "unit_price": uprice,
                "line_total": ltotal,
            })

        order_record = {
            "order_id": order_id,
            "customer_id": cust_id_str,
            "customer_name": cust_name,
            "status": "pending",
            "priority": "standard",
            "total_amount": f"{total_val:.2f}",
            "currency": "USD",
            "workflow_id": workflow_id,
        }
        persistence.save_order_with_items(order_record, order_items_records)

        # Provision linked TMS shipment
        shipment_id = f"shp-{uuid.uuid4().hex[:12]}"
        tracking_num = f"TRK-OMS-{uuid.uuid4().hex[:6].upper()}"
        persistence.save_shipment({
            "shipment_id": shipment_id,
            "order_id": order_id,
            "carrier": "Global Intermodal Logistics",
            "carrier_tracking_id": tracking_num,
            "freight_mode": "road",
            "origin": "Distribution Logistics Hub",
            "destination": f"{cust_name} Facility",
            "status": "in_transit",
            "current_location": "En Route - Regional Transit Hub",
            "workflow_id": workflow_id,
        })

        try:
            await dispatch_event(
                event_type="OrderPlaced",
                source_agent="OMS-AutonomousPortal",
                payload={
                    "order_id": order_id,
                    "customer_name": cust_name,
                    "total_amount": total_val,
                    "workflow_id": workflow_id,
                },
            )
        except Exception:
            pass

    background_tasks.add_task(
        _run_workflow,
        workflow_id,
        correlation_id,
        request,
    )

    logger.info(
        "Workflow accepted",
        workflow_id=workflow_id,
        customer_id=str(request.customer_id),
    )

    return WorkflowAcceptedResponse(
        workflow_id=workflow_id,
        correlation_id=correlation_id,
    )


@router.get(
    "",
    summary="List recent workflows",
)
async def list_workflows_endpoint(
    limit: int = Query(50, ge=1, le=100),
) -> dict[str, Any]:
    """List recent workflows with execution status and summary."""
    items = persistence.list_workflows(limit=limit)
    return {"items": items, "total": len(items)}


@router.get(
    "/{workflow_id}",
    response_model=WorkflowStatusResponse,
    summary="Get current workflow state",
)
async def get_workflow_status(workflow_id: str) -> WorkflowStatusResponse:
    """
    Returns the current state of the workflow identified by `workflow_id`.

    States: received → running → completed | failed
    """
    persisted = persistence.get_workflow(workflow_id)
    state = _WORKFLOW_STORE.get(workflow_id) or persisted
    if persisted and state:
        if persisted.get("order") and isinstance(state.get("order"), dict):
            for k in ("order_id", "customer_name", "total_amount", "priority", "status", "items"):
                if persisted["order"].get(k) and not state["order"].get(k):
                    state["order"][k] = persisted["order"][k]
        if persisted.get("customer") and not state.get("customer"):
            state["customer"] = persisted["customer"]

    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found",
        )

    return WorkflowStatusResponse(
        workflow_id=workflow_id,
        correlation_id=state.get("correlation_id"),
        workflow_status=state.get("workflow_status", "unknown"),
        current_node=state.get("current_node"),
        active_agents=state.get("active_agents") or [],
        order=state.get("order"),
        shipment=state.get("shipment"),
        executive_decision=state.get("executive_decision"),
        requires_human_approval=state.get("requires_human_approval", False),
        event_count=len(state.get("event_history") or []),
        error_count=len(state.get("errors") or []),
        blackboard=state.get("blackboard"),
        human_overrides=state.get("human_overrides"),
    )


@router.get(
    "/{workflow_id}/trace",
    summary="Get per-agent input/output traces for a workflow",
)
async def get_workflow_trace(workflow_id: str) -> dict[str, Any]:
    """
    Returns the full per-agent execution trace for a completed (or running) workflow.

    Each entry contains:
    - agent_code / agent_name
    - started_at / finished_at / duration_ms
    - status (completed | failed)
    - input: snapshot of SupplyChainState the agent received
    - output: partial state dict the agent returned
    - decision: the agent's own decision record (from decisions list)
    - events_published: events this agent published to event_history
    """
    trace = _TRACE_STORE.get(workflow_id)
    if trace is None:
        trace = persistence.get_workflow_trace(workflow_id)
        if trace:
            _TRACE_STORE[workflow_id] = trace

    persisted = persistence.get_workflow(workflow_id)
    state = _WORKFLOW_STORE.get(workflow_id) or persisted
    if persisted and state:
        if persisted.get("order") and isinstance(state.get("order"), dict):
            for k in ("order_id", "customer_name", "total_amount", "priority", "status", "items"):
                if persisted["order"].get(k) and not state["order"].get(k):
                    state["order"][k] = persisted["order"][k]
        if persisted.get("customer") and not state.get("customer"):
            state["customer"] = persisted["customer"]

    # Check workflow exists
    if not state and not trace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found",
        )

    workflow_status = (state or {}).get("workflow_status", "unknown")

    return {
        "workflow_id": workflow_id,
        "workflow_status": workflow_status,
        "agents_executed": len(trace or []),
        "traces": trace or [],
    }


VALID_OVERRIDE_TOPICS = (
    "order", "inventory", "warehouse", "supplier", "shipment", "finance",
    "risk", "forecast", "quality", "sustainability", "manufacturing",
    "customer_service", "pricing", "procurement", "planning", "negotiation",
    "executive_decision",
)


class OverrideRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=50)
    action: Literal["pin", "revert"]
    value: dict[str, Any] = Field(default_factory=dict)


@router.post(
    "/{workflow_id}/override",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Human override / PIN a decision on the Blackboard",
)
async def human_override(
    workflow_id: str,
    request: OverrideRequest,
    background_tasks: BackgroundTasks,
    _user: Annotated[dict, Depends(require_authenticated_role("admin", "analyst"))] = None,
) -> dict[str, Any]:
    """
    Exposes the Human Monitoring Override. Allows an observer to override,
    PIN, or REVERT a decision on the versioned blackboard, and resumes
    the consensus loops.
    """
    if request.topic not in VALID_OVERRIDE_TOPICS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid blackboard topic '{request.topic}'. Must be one of {VALID_OVERRIDE_TOPICS}",
        )

    state = _WORKFLOW_STORE.get(workflow_id) or persistence.get_workflow(workflow_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found",
        )

    overrides = dict(state.get("human_overrides") or {})
    blackboard = dict(state.get("blackboard") or {})
    topic = request.topic

    if request.action == "pin":
        overrides[topic] = request.value
        topic_entries = list(blackboard.get(topic) or [])
        
        # Mark previous active as superseded
        new_entries = []
        for entry in topic_entries:
            entry_copy = dict(entry)
            if entry_copy.get("status") in ("proposed", "contested", "accepted"):
                entry_copy["status"] = "superseded"
            new_entries.append(entry_copy)
            
        from datetime import datetime, timezone
        new_entries.append({
            "agent_id": "human_override",
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "confidence": 1.0,
            "rationale": "User manually overridden/pinned this decision.",
            "status": "accepted",
            "data": request.value,
        })
        blackboard[topic] = new_entries

    elif request.action == "revert":
        overrides.pop(topic, None)
        topic_entries = list(blackboard.get(topic) or [])
        if topic_entries:
            # Revert latest override to proposed
            topic_entries[-1]["status"] = "proposed"
            blackboard[topic] = topic_entries

    state["human_overrides"] = overrides
    state["blackboard"] = blackboard
    state["workflow_status"] = "running"
    state["requires_human_approval"] = False
    state["loop_count"] = 0  # Reset loop counter to allow retry reasoning

    _save_workflow_state(workflow_id, state)

    # Trigger async retry loop run
    background_tasks.add_task(
        _run_workflow,
        workflow_id,
        state.get("correlation_id") or str(uuid.uuid4()),
    )

    return {
        "status": "resumed",
        "message": f"Override '{request.action}' applied to topic '{topic}'. Consensus loops resumed.",
    }


class ExecutiveApprovalRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=500)


@router.post(
    "/{workflow_id}/approve",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Executive approval for an escalated workflow",
)
async def approve_workflow(
    workflow_id: str,
    background_tasks: BackgroundTasks,
    body: ExecutiveApprovalRequest | None = None,
    _user: Annotated[dict, Depends(require_authenticated_role("admin"))] = None,
) -> dict[str, Any]:
    """Approves an escalated workflow requiring human review and resumes execution."""
    state = _WORKFLOW_STORE.get(workflow_id) or persistence.get_workflow(workflow_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found",
        )

    from datetime import datetime, timezone

    now_iso = datetime.now(tz=timezone.utc).isoformat()
    notes = body.notes if body and body.notes else "Approved by Human Executive"

    state["executive_decision"] = {
        "approved": True,
        "approval_tier": "human_executive",
        "rationale": notes,
        "timestamp": now_iso,
    }
    state["requires_human_approval"] = False
    state["workflow_status"] = "running"
    state["loop_count"] = 0

    decisions = list(state.get("decisions") or [])
    decisions.append({
        "agent": "ADS-17",
        "action": "executive_approved",
        "reason": notes,
        "data": {"approval_tier": "human_executive"},
        "decision_source": "human_in_the_loop",
        "timestamp": now_iso,
    })
    state["decisions"] = decisions

    events = list(state.get("event_history") or [])
    events.append({
        "event_type": "CEOApprovalGranted",
        "source_agent": "ADS-17",
        "payload": {"reason": notes, "tier": "human_executive"},
        "timestamp": now_iso,
    })
    state["event_history"] = events

    order_id = (state.get("order") or {}).get("order_id")
    if order_id:
        persistence.update_order_status(order_id, "delivered")
        shp = persistence.get_shipment_by_order(order_id)
        if shp:
            persistence.update_shipment_status(
                shipment_id=shp["shipment_id"],
                status="delivered",
                current_location="Destination Fulfilled",
            )

    _save_workflow_state(workflow_id, state)

    background_tasks.add_task(
        _run_workflow,
        workflow_id,
        state.get("correlation_id") or str(uuid.uuid4()),
    )

    return {
        "workflow_id": workflow_id,
        "status": "resumed",
        "message": "Workflow approved by executive. Execution resumed.",
    }


@router.post(
    "/{workflow_id}/reject",
    status_code=status.HTTP_200_OK,
    summary="Executive rejection for an escalated workflow",
)
async def reject_workflow(
    workflow_id: str,
    body: ExecutiveApprovalRequest | None = None,
    _user: Annotated[dict, Depends(require_authenticated_role("admin"))] = None,
) -> dict[str, Any]:
    """Rejects an escalated workflow and halts further processing."""
    state = _WORKFLOW_STORE.get(workflow_id) or persistence.get_workflow(workflow_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found",
        )

    from datetime import datetime, timezone

    now_iso = datetime.now(tz=timezone.utc).isoformat()
    notes = body.notes if body and body.notes else "Rejected by Human Executive"

    state["executive_decision"] = {
        "approved": False,
        "approval_tier": "human_executive",
        "rationale": notes,
        "timestamp": now_iso,
    }
    state["requires_human_approval"] = False
    state["workflow_status"] = "failed"

    decisions = list(state.get("decisions") or [])
    decisions.append({
        "agent": "ADS-17",
        "action": "executive_rejected",
        "reason": notes,
        "data": {"approval_tier": "human_executive"},
        "decision_source": "human_in_the_loop",
        "timestamp": now_iso,
    })
    state["decisions"] = decisions

    events = list(state.get("event_history") or [])
    events.append({
        "event_type": "CEOApprovalDenied",
        "source_agent": "ADS-17",
        "payload": {"reason": notes, "tier": "human_executive"},
        "timestamp": now_iso,
    })
    state["event_history"] = events

    order_id = (state.get("order") or {}).get("order_id")
    if order_id:
        persistence.update_order_status(order_id, "delivered")
        shp = persistence.get_shipment_by_order(order_id)
        if shp:
            persistence.update_shipment_status(
                shipment_id=shp["shipment_id"],
                status="delivered",
                current_location="Destination Fulfilled",
            )

    _save_workflow_state(workflow_id, state)

    order_id = (state.get("order") or {}).get("order_id")
    if order_id:
        persistence.update_order_status(order_id, "cancelled")
        shp = persistence.get_shipment_by_order(order_id)
        if shp:
            persistence.update_shipment_status(
                shipment_id=shp["shipment_id"],
                status="cancelled",
                current_location="Held / Cancelled at Dispatch Origin",
            )

    return {
        "workflow_id": workflow_id,
        "status": "failed",
        "message": "Workflow rejected by executive.",
    }

