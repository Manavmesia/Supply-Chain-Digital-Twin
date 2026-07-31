"""
Workflow API endpoints — Phase 3

POST /api/v1/workflows/orders
    Accepts an order request, initialises shared state, and runs the
    supply chain workflow as a background asyncio task.

GET /api/v1/workflows/{workflow_id}
    Returns the current workflow state from the in-memory checkpoint store.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException, status

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
# In-process state store for workflow results
# (Phase 6 upgrades to Redis/PostgreSQL)
# ---------------------------------------------------------------------------

_WORKFLOW_STORE: dict[str, dict[str, Any]] = {}

# Compiled graph (singleton — avoids rebuilding MemorySaver per request)
_COMPILED_GRAPH = None


def _get_graph():
    global _COMPILED_GRAPH
    if _COMPILED_GRAPH is None:

        async def _session_factory():
            """Return a new AsyncSession that the caller must close."""
            return AsyncSessionLocal()

        _COMPILED_GRAPH = compile_workflow(session_factory=_session_factory)
    return _COMPILED_GRAPH


# ---------------------------------------------------------------------------
# Background workflow runner
# ---------------------------------------------------------------------------

async def _run_workflow(workflow_id: str, correlation_id: str, request: OrderWorkflowRequest) -> None:
    """
    Executes the full supply chain workflow asynchronously.
    Result is stored in _WORKFLOW_STORE[workflow_id].
    """
    initial_state: SupplyChainState = {
        "workflow_id": workflow_id,
        "correlation_id": correlation_id,
        "workflow_status": "received",
        "active_agents": [],
        "event_history": [],
        "decisions": [],
        "errors": [],
        "messages": [],
        "retries": {},
        "order": {
            "customer_id": str(request.customer_id),
            "items": [
                {"product_id": str(i.product_id), "quantity": i.quantity}
                for i in request.items
            ],
            "priority": request.priority,
        },
    }

    _WORKFLOW_STORE[workflow_id] = {**initial_state, "workflow_status": "running"}

    try:
        graph = _get_graph()
        config = {"configurable": {"thread_id": workflow_id}}

        # Use a single session for the full workflow run
        async with AsyncSessionLocal() as session:

            async def _session_factory():
                return session

            # Rebuild graph with bound session for this run
            compiled = compile_workflow(session_factory=_session_factory)
            final_state = await compiled.ainvoke(initial_state, config=config)

            await session.commit()

        _WORKFLOW_STORE[workflow_id] = final_state
        logger.info(
            "Workflow completed",
            workflow_id=workflow_id,
            status=final_state.get("workflow_status"),
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
    `workflow_id` to poll `GET /workflows/{workflow_id}` for status.
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
        priority=request.priority,
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
    )
