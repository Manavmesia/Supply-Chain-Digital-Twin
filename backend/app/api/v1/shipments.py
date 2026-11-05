"""
Logistics & Transportation (TMS) REST API

Endpoints for tracking cargo movements, freight modes, waypoint telemetry,
and autonomous disruption rerouting across the digital twin logistics network.

GET  /api/v1/shipments            — list shipments with live filters
GET  /api/v1/shipments/stats      — logistics KPI metrics (on-time rate, active modes)
GET  /api/v1/shipments/{id}       — shipment tracking detail + telemetry
POST /api/v1/shipments            — create/dispatch shipment
POST /api/v1/shipments/{id}/status  — update waypoint status / report delay
POST /api/v1/shipments/{id}/reroute — reroute freight mode (e.g., ocean -> air)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import require_authenticated_role
from app.core import persistence
from app.core.database import get_db_session
from app.events.dispatcher import dispatch_event
from app.models.shipment import Shipment

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/shipments", tags=["shipments"])


class CreateShipmentRequest(BaseModel):
    order_id: str | None = None
    warehouse_id: str | None = None
    carrier: str = Field(default="Global Intermodal Logistics")
    freight_mode: Literal["road", "air", "ocean", "rail"] = "road"
    origin: str = Field(default="Newark Distribution Center")
    destination: str = Field(default="Frankfurt Logistics Centre")
    eta: str | None = None


class UpdateShipmentStatusRequest(BaseModel):
    status: Literal["pending", "assigned", "dispatched", "in_transit", "delivered", "delayed", "failed"]
    current_location: str | None = None
    delay_reason: str | None = None


class RerouteShipmentRequest(BaseModel):
    new_freight_mode: Literal["road", "air", "ocean", "rail"] = "air"
    new_carrier: str | None = "Express Air Cargo Global"
    reason: str = "Autonomous disruption bypass & expedited delivery"


@router.get("", summary="List all shipments with filters")
async def list_shipments(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    shipment_status: str | None = Query(None, alias="status"),
    freight_mode: str | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Retrieve all shipments across the enterprise network."""
    try:
        query = select(Shipment)
        count_query = select(func.count(Shipment.shipment_id))
        if shipment_status:
            query = query.where(Shipment.status == shipment_status)
            count_query = count_query.where(Shipment.status == shipment_status)
        if freight_mode:
            query = query.where(Shipment.freight_mode == freight_mode)
            count_query = count_query.where(Shipment.freight_mode == freight_mode)

        query = query.order_by(Shipment.created_at.desc()).offset(skip).limit(limit)
        res = await session.execute(query)
        shipments = res.scalars().all()
        cnt = (await session.execute(count_query)).scalar() or 0

        items = [
            {
                "shipment_id": str(s.shipment_id),
                "order_id": str(s.order_id) if s.order_id else None,
                "warehouse_id": str(s.warehouse_id) if s.warehouse_id else None,
                "carrier": s.carrier,
                "carrier_tracking_id": s.carrier_tracking_id,
                "route": s.route,
                "freight_mode": s.freight_mode or "road",
                "origin": "Distribution Hub",
                "destination": "Destination Port",
                "eta": s.eta.isoformat() if s.eta else None,
                "actual_delivery": s.actual_delivery.isoformat() if s.actual_delivery else None,
                "status": s.status,
                "delay_reason": s.delay_reason,
                "current_location": "En route",
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in shipments
        ]
        return {"items": items, "total": cnt, "skip": skip, "limit": limit}
    except Exception as exc:
        logger.warning("DB query failed in list_shipments, falling back to SQLite persistence", error=str(exc))
        items, total = persistence.list_shipments(
            skip=skip,
            limit=limit,
            status_filter=shipment_status,
            freight_mode=freight_mode,
        )
        return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/stats", summary="Logistics KPI metrics")
async def get_shipment_stats() -> dict[str, Any]:
    """Calculate aggregate logistics metrics (on-time rate, active shipments, freight modes)."""
    items, total = persistence.list_shipments(skip=0, limit=500)
    in_transit = sum(1 for s in items if s.get("status") == "in_transit")
    delayed = sum(1 for s in items if s.get("status") == "delayed")
    delivered = sum(1 for s in items if s.get("status") == "delivered")
    modes = {}
    for s in items:
        m = s.get("freight_mode") or "road"
        modes[m] = modes.get(m, 0) + 1

    on_time_pct = round(((total - delayed) / max(total, 1)) * 100, 1)

    return {
        "total_shipments": total,
        "in_transit": in_transit,
        "delayed": delayed,
        "delivered": delivered,
        "on_time_rate_pct": on_time_pct,
        "by_freight_mode": modes,
    }


@router.get("/{shipment_id}", summary="Get detailed shipment telemetry")
async def get_shipment(shipment_id: str) -> dict[str, Any]:
    """Retrieve detailed shipment info including waypoint telemetry."""
    shipment = persistence.get_shipment(shipment_id)
    if not shipment:
        raise HTTPException(status_code=404, detail=f"Shipment '{shipment_id}' not found")
    return shipment


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create/dispatch a shipment")
async def create_shipment(
    payload: CreateShipmentRequest,
    current_user: dict[str, Any] = Depends(require_authenticated_role(["admin", "operator", "viewer"])),
) -> dict[str, Any]:
    """Dispatch a new shipment across the supply chain network."""
    now_iso = datetime.now(timezone.utc).isoformat()
    tracking_code = f"TRK-{payload.freight_mode[:3].upper()}-{uuid.uuid4().hex[:6].upper()}"
    shipment_dict = {
        "shipment_id": f"shp-{uuid.uuid4().hex[:12]}",
        "order_id": payload.order_id,
        "warehouse_id": payload.warehouse_id,
        "carrier": payload.carrier,
        "carrier_tracking_id": tracking_code,
        "route": f"{payload.origin} -> {payload.destination}",
        "freight_mode": payload.freight_mode,
        "origin": payload.origin,
        "destination": payload.destination,
        "eta": payload.eta or now_iso,
        "status": "in_transit",
        "current_location": f"Departed {payload.origin}",
        "created_at": now_iso,
    }
    shp_id = persistence.save_shipment(shipment_dict)
    return {"shipment_id": shp_id, "status": "in_transit", "tracking_number": tracking_code}


@router.post("/{shipment_id}/status", summary="Update shipment status / log delay exception")
async def update_status(
    shipment_id: str,
    payload: UpdateShipmentStatusRequest,
    current_user: dict[str, Any] = Depends(require_authenticated_role(["admin", "operator", "viewer"])),
) -> dict[str, Any]:
    """Update shipment waypoint or trigger autonomous delay remediation."""
    updated = persistence.update_shipment_status(
        shipment_id=shipment_id,
        status=payload.status,
        current_location=payload.current_location,
        delay_reason=payload.delay_reason,
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Shipment '{shipment_id}' not found")

    # If delayed, dispatch DeliveryDelayed canonical event to trigger ADS-06 rerouting
    event_dispatched = None
    if payload.status == "delayed":
        event_dispatched = await dispatch_event(
            event_type="DeliveryDelayed",
            source_agent="TMS-Telemetry",
            payload={
                "shipment_id": shipment_id,
                "carrier": updated.get("carrier"),
                "freight_mode": updated.get("freight_mode"),
                "delay_reason": payload.delay_reason or "Severe logistical transit bottleneck",
                "current_location": payload.current_location or updated.get("current_location"),
            },
        )

    return {
        "shipment": updated,
        "autonomous_remediation_event": event_dispatched,
    }


@router.post("/{shipment_id}/reroute", summary="Autonomous or manual freight reroute")
async def reroute_freight(
    shipment_id: str,
    payload: RerouteShipmentRequest,
    current_user: dict[str, Any] = Depends(require_authenticated_role(["admin", "operator", "viewer"])),
) -> dict[str, Any]:
    """Reroute freight mode (e.g., from delayed ocean/road to expedited air cargo)."""
    rerouted = persistence.reroute_shipment(
        shipment_id=shipment_id,
        new_mode=payload.new_freight_mode,
        new_carrier=payload.new_carrier,
        reason=payload.reason,
    )
    if not rerouted:
        raise HTTPException(status_code=404, detail=f"Shipment '{shipment_id}' not found")

    # Record event in digital twin audit trail
    event_dispatched = await dispatch_event(
        event_type="RouteOptimized",
        source_agent="ADS-06",
        payload={
            "shipment_id": shipment_id,
            "new_freight_mode": payload.new_freight_mode,
            "new_carrier": payload.new_carrier,
            "resolution_reason": payload.reason,
        },
    )

    return {
        "success": True,
        "shipment": rerouted,
        "audit_event": event_dispatched,
    }
