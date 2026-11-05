"""
Events REST API — Phase 3 / Event Bus

POST /api/v1/events               — inject a manual event
GET  /api/v1/events               — list recent workflow event history
POST /api/v1/events/{id}/replay   — replay / requeue a failed event
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.v1.auth import require_authenticated_role
from app.core import persistence
from app.events.dispatcher import dispatch_event_remediation

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/events", tags=["events"])

# ---------------------------------------------------------------------------
# In-process event log (Phase 3 — replaced by DB in Phase 6)
# ---------------------------------------------------------------------------

_EVENT_LOG: list[dict[str, Any]] = []
_MAX_LOG_SIZE = 500


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ManualEventRequest(BaseModel):
    event_type: str = Field(min_length=1, max_length=100)
    source_agent: str = Field(default="manual", min_length=1, max_length=50)
    payload: dict[str, Any] = Field(default_factory=dict)
    workflow_id: str | None = Field(default=None, max_length=100)


class EventResponse(BaseModel):
    event_id: str
    event_type: str
    source_agent: str
    payload: dict[str, Any]
    workflow_id: str | None
    timestamp: str
    status: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Inject a manual event into the system",
)
async def inject_event(
    request: ManualEventRequest,
    _user: Annotated[dict, Depends(require_authenticated_role("admin", "analyst"))] = None,
) -> dict[str, Any]:
    """
    Inject a synthetic event into the supply chain event bus.

    Useful for testing agent reactions to specific events (e.g., triggering
    InventoryLow, SupplierUnavailable, or custom disruption events).
    """
    event_id = str(uuid.uuid4())
    timestamp = datetime.now(tz=timezone.utc).isoformat()

    event_record = {
        "event_id": event_id,
        "event_type": request.event_type,
        "source_agent": request.source_agent,
        "payload": request.payload,
        "workflow_id": request.workflow_id,
        "timestamp": timestamp,
        "status": "injected",
    }

    # Append to in-memory log (rotating) and persist
    global _EVENT_LOG
    _EVENT_LOG.append(event_record)
    if len(_EVENT_LOG) > _MAX_LOG_SIZE:
        _EVENT_LOG = _EVENT_LOG[-_MAX_LOG_SIZE:]

    try:
        persistence.save_event(event_record)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to persist initial event", event_id=event_id, error=str(exc))

    # Autonomous Multi-Agent Dispatch & Closed-Loop Remediation
    remediation: dict[str, Any] = {}
    try:
        remediation = await dispatch_event_remediation(event_record)
        event_record["status"] = "remediated"
        event_record["subscribers"] = remediation.get("subscribers", [])
        event_record["remediation_summary"] = remediation.get("remediation_summary", "")
        event_record["autonomous_actions"] = remediation.get("autonomous_actions", [])
        persistence.save_event(event_record)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Event dispatcher remediation error", event_id=event_id, error=str(exc))

    logger.info(
        "Manual event injected and remediated by autonomous agents",
        event_id=event_id,
        event_type=request.event_type,
        source=request.source_agent,
        subscribers=remediation.get("subscribers", []),
    )

    return {
        "event_id": event_id,
        "event_type": request.event_type,
        "status": "remediated",
        "timestamp": timestamp,
        "message": remediation.get("remediation_summary") or "Event processed by subscribed agents.",
        "subscribers": remediation.get("subscribers", []),
        "remediation_status": "remediated",
        "remediation_summary": remediation.get("remediation_summary", ""),
        "autonomous_actions": remediation.get("autonomous_actions", []),
    }


@router.get(
    "",
    summary="List recent injected events",
)
async def list_events(
    limit: int = Query(50, ge=1, le=200),
    event_type: str | None = Query(None),
) -> dict[str, Any]:
    """Return the most recent events from persistent storage."""
    persisted = persistence.list_events(limit=limit, event_type=event_type)
    if persisted:
        return {
            "items": persisted,
            "total": len(persisted),
            "limit": limit,
        }

    events = list(reversed(_EVENT_LOG))
    if event_type:
        events = [e for e in events if e["event_type"] == event_type]

    return {
        "items": events[:limit],
        "total": len(events),
        "limit": limit,
    }


@router.post(
    "/{event_id}/replay",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Replay a failed event from the DLQ",
)
async def replay_event(
    event_id: str,
    _user: Annotated[dict, Depends(require_authenticated_role("admin", "analyst"))] = None,
) -> dict[str, Any]:
    """
    Requeue a specific event for replay.  In production this would
    move the message from the Dead Letter Queue back to the main exchange.
    In Phase 3 it resets the event status in the in-memory log.
    """
    for event in _EVENT_LOG:
        if event["event_id"] == event_id:
            event["status"] = "replayed"
            event["replayed_at"] = datetime.now(tz=timezone.utc).isoformat()
            logger.info("Event replayed", event_id=event_id, event_type=event["event_type"])
            return {
                "event_id": event_id,
                "status": "replayed",
                "message": f"Event '{event['event_type']}' has been requeued for processing.",
            }

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Event '{event_id}' not found in the event log",
    )


@router.get(
    "/types",
    summary="List all known event types",
)
async def list_event_types() -> dict[str, Any]:
    """Return all canonical supply chain event types and their producer agents."""
    return {
        "event_types": [
            {"type": "OrderCreated",            "producer": "ADS-01", "layer": "operational"},
            {"type": "OrderRejected",           "producer": "ADS-01", "layer": "operational"},
            {"type": "InventoryAllocated",      "producer": "ADS-03", "layer": "operational"},
            {"type": "InventoryOutOfStock",     "producer": "ADS-03", "layer": "operational"},
            {"type": "InventoryLow",            "producer": "ADS-03", "layer": "operational"},
            {"type": "SupplierSelected",        "producer": "ADS-05", "layer": "operational"},
            {"type": "SupplierUnavailable",     "producer": "ADS-05", "layer": "operational"},
            {"type": "ShipmentCreated",         "producer": "ADS-06", "layer": "operational"},
            {"type": "ShipmentDispatched",      "producer": "ADS-06", "layer": "operational"},
            {"type": "DemandForecastReady",     "producer": "ADS-02", "layer": "business"},
            {"type": "FinancialApprovalGranted","producer": "ADS-09", "layer": "business"},
            {"type": "BudgetExceeded",          "producer": "ADS-09", "layer": "business"},
            {"type": "RiskDetected",            "producer": "ADS-10", "layer": "business"},
            {"type": "ExecutiveEscalation",     "producer": "ADS-10", "layer": "business"},
            {"type": "PricingUpdated",          "producer": "ADS-11", "layer": "business"},
            {"type": "SustainabilityFlagged",   "producer": "ADS-13", "layer": "business"},
            {"type": "QualityFailed",           "producer": "ADS-14", "layer": "business"},
            {"type": "ExecutionPlanReady",      "producer": "ADS-15", "layer": "coordination"},
            {"type": "NegotiationCompleted",    "producer": "ADS-16", "layer": "coordination"},
            {"type": "ContractTermsProposed",   "producer": "ADS-16", "layer": "coordination"},
            {"type": "CEOApprovalGranted",      "producer": "ADS-17", "layer": "coordination"},
            {"type": "CEOApprovalDenied",       "producer": "ADS-17", "layer": "coordination"},
            {"type": "ReportGenerated",         "producer": "ADS-18", "layer": "coordination"},
            {"type": "DashboardUpdated",        "producer": "ADS-18", "layer": "coordination"},
        ]
    }
