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

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel

from app.core.database import AsyncSessionLocal
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
# In-process state stores
# (Phase 6 upgrades to Redis/PostgreSQL)
# ---------------------------------------------------------------------------

_WORKFLOW_STORE: dict[str, dict[str, Any]] = {}

# Per-workflow trace store: workflow_id → list of per-agent trace dicts
_TRACE_STORE: dict[str, list[dict[str, Any]]] = {}


# ---------------------------------------------------------------------------
# Background workflow runner
# ---------------------------------------------------------------------------

async def _run_workflow(workflow_id: str, correlation_id: str, request: OrderWorkflowRequest | None = None) -> None:
    """
    Executes or resumes the decentralized supply chain workflow.
    """
    existing_state = _WORKFLOW_STORE.get(workflow_id)
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

    _WORKFLOW_STORE[workflow_id] = {**initial_state, "workflow_status": "running"}

    # Create/retrieve trace collector
    trace = _TRACE_STORE.get(workflow_id)
    if trace is None:
        trace = []
        _TRACE_STORE[workflow_id] = trace

    try:
        config = {"configurable": {"thread_id": workflow_id}}

        async with AsyncSessionLocal() as session:
            async def _session_factory():
                return session

            compiled = compile_workflow(
                session_factory=_session_factory,
                trace_collector=trace,
            )
            final_state = await compiled.ainvoke(initial_state, config=config)

            # Mark completed only if there are no active errors/escalations
            if not final_state.get("errors") and final_state.get("workflow_status") != "failed":
                if final_state.get("workflow_status") != "escalated":
                    final_state["workflow_status"] = "completed"

            await session.commit()

        _WORKFLOW_STORE[workflow_id] = final_state
        logger.info(
            "Workflow completed",
            workflow_id=workflow_id,
            status=final_state.get("workflow_status"),
            agents_run=len(trace),
        )

    except Exception as exc:  # noqa: BLE001
        logger.error("Workflow failed", workflow_id=workflow_id, error=str(exc))
        _WORKFLOW_STORE[workflow_id] = {
            **initial_state,
            "workflow_status": "failed",
            "errors": [{"error": str(exc)}],
        }



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
    "/{workflow_id}",
    response_model=WorkflowStatusResponse,
    summary="Get current workflow state",
)
async def get_workflow_status(workflow_id: str) -> WorkflowStatusResponse:
    """
    Returns the current state of the workflow identified by `workflow_id`.

    States: received → running → completed | failed
    """
    state = _WORKFLOW_STORE.get(workflow_id)
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
    # Check workflow exists
    if workflow_id not in _WORKFLOW_STORE and workflow_id not in _TRACE_STORE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found",
        )

    trace = _TRACE_STORE.get(workflow_id, [])
    workflow_status = (_WORKFLOW_STORE.get(workflow_id) or {}).get("workflow_status", "unknown")

    return {
        "workflow_id": workflow_id,
        "workflow_status": workflow_status,
        "agents_executed": len(trace),
        "traces": trace,
    }


class OverrideRequest(BaseModel):
    topic: str
    action: str  # "pin" | "revert"
    value: dict[str, Any]


@router.post(
    "/{workflow_id}/override",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Human override / PIN a decision on the Blackboard",
)
async def human_override(
    workflow_id: str,
    request: OverrideRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """
    Exposes the Human Monitoring Override. Allows an observer to override,
    PIN, or REVERT a decision on the versioned blackboard, and resumes
    the consensus loops.
    """
    state = _WORKFLOW_STORE.get(workflow_id)
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

    _WORKFLOW_STORE[workflow_id] = state

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

