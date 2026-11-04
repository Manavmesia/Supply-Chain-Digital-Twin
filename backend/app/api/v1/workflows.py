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
from app.core.database import AsyncSessionLocal
from app.core.standby_session import create_standby_session, is_database_connected
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
            )
            final_state = await compiled.ainvoke(fallback_initial_state, config=config)
            if not final_state.get("errors") and final_state.get("workflow_status") != "failed":
                if final_state.get("workflow_status") != "escalated":
                    final_state["workflow_status"] = "completed"

        _save_workflow_state(workflow_id, final_state, trace)
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
            "errors": [{"error": str(exc)}],
        })



# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/orders",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=WorkflowAcceptedResponse,
    summary="Start a new order fulfilment workflow",
)
async def start_order_workflow(
    request: OrderWorkflowRequest,
    background_tasks: BackgroundTasks,
) -> WorkflowAcceptedResponse:
    """
    Accepts a customer order and starts the supply chain workflow.

    The workflow runs asynchronously in the background. Use the returned
    `workflow_id` to poll `GET /workflows/{workflow_id}` for status,
    and `GET /workflows/{workflow_id}/trace` for per-agent I/O traces.
    """
    workflow_id = str(uuid.uuid4())
    correlation_id = str(uuid.uuid4())

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
    state = _WORKFLOW_STORE.get(workflow_id) or persistence.get_workflow(workflow_id)
    if state is None:
        state = persistence.get_workflow(workflow_id)
        if state:
            _WORKFLOW_STORE[workflow_id] = state

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

    state = _WORKFLOW_STORE.get(workflow_id) or persistence.get_workflow(workflow_id)
    if state is None:
        state = persistence.get_workflow(workflow_id)
        if state:
            _WORKFLOW_STORE[workflow_id] = state

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
    body: ExecutiveApprovalRequest | None = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
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

    _save_workflow_state(workflow_id, state)

    return {
        "workflow_id": workflow_id,
        "status": "failed",
        "message": "Workflow rejected by executive.",
    }

