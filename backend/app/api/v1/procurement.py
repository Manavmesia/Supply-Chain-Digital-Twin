"""
Supplier Relationship Management & Procurement (SRM) REST API

Endpoints for tracking inbound Purchase Orders, supplier reliability scorecards,
and receiving inbound stock to replenish warehouse inventory.

GET  /api/v1/procurement/orders          — list inbound POs
GET  /api/v1/procurement/orders/{po_id}  — get PO detail
POST /api/v1/procurement/orders          — create/issue PO
POST /api/v1/procurement/orders/{id}/receive — 1-click stock receipt (replenishes WMS)
GET  /api/v1/procurement/suppliers       — supplier reliability scorecard
GET  /api/v1/procurement/stats           — aggregate procurement spend & metrics
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.v1.auth import require_authenticated_role
from app.core import persistence
from app.core.catalog import BASELINE_PRODUCTS, BASELINE_SUPPLIERS, BASELINE_WAREHOUSES
from app.events.dispatcher import dispatch_event

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/procurement", tags=["procurement"])


class CreatePurchaseOrderRequest(BaseModel):
    supplier_id: str
    supplier_name: str | None = None
    product_id: str
    product_name: str | None = None
    sku: str | None = None
    warehouse_id: str
    warehouse_name: str | None = None
    quantity: int = Field(gt=0, le=100_000)
    unit_cost: float = Field(gt=0)
    lead_time_days: int = Field(default=5, ge=1)


@router.get("/orders", summary="List all procurement purchase orders")
async def list_purchase_orders(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    """Fetch all inbound purchase orders with lifecycle status."""
    orders = persistence.list_purchase_orders(limit=limit, status_filter=status_filter)
    return {
        "items": orders,
        "total": len(orders),
        "limit": limit,
    }


@router.get("/stats", summary="Procurement & spend aggregate statistics")
async def get_procurement_stats() -> dict[str, Any]:
    """Calculate aggregate procurement figures."""
    pos = persistence.list_purchase_orders(limit=200)
    total_spend = sum(float(p.get("total_cost", 0.0)) for p in pos)
    in_transit_spend = sum(
        float(p.get("total_cost", 0.0)) for p in pos if p.get("status") == "in_transit"
    )
    in_transit_count = sum(1 for p in pos if p.get("status") == "in_transit")
    received_count = sum(1 for p in pos if p.get("status") == "received")

    return {
        "total_po_count": len(pos),
        "in_transit_count": in_transit_count,
        "received_count": received_count,
        "total_spend": round(total_spend, 2),
        "in_transit_spend": round(in_transit_spend, 2),
    }


@router.post("/orders", status_code=status.HTTP_201_CREATED, summary="Create/issue a Purchase Order")
async def create_purchase_order(
    payload: CreatePurchaseOrderRequest,
    current_user: dict[str, Any] = Depends(require_authenticated_role(["admin", "operator", "viewer"])),
) -> dict[str, Any]:
    """Issue a new inbound replenishment Purchase Order."""
    now_iso = datetime.now(timezone.utc).isoformat()
    po_id = f"po-{uuid.uuid4().hex[:12]}"

    # Resolve names if not provided
    s_name = payload.supplier_name
    if not s_name:
        for s in BASELINE_SUPPLIERS:
            if s[0] == payload.supplier_id:
                s_name = s[1]
                break
        s_name = s_name or "Industrial Supplier Corp"

    p_name = payload.product_name
    sku = payload.sku
    if not p_name or not sku:
        for p in BASELINE_PRODUCTS:
            if p[0] == payload.product_id:
                p_name = p[2]
                sku = p[1]
                break
        p_name = p_name or "Precision Component"
        sku = sku or "SKU-AUTO"

    w_name = payload.warehouse_name
    if not w_name:
        for w in BASELINE_WAREHOUSES:
            if w[0] == payload.warehouse_id:
                w_name = w[1]
                break
        w_name = w_name or "Regional Fulfilment Hub"

    total_cost = round(payload.unit_cost * payload.quantity, 2)

    po_dict = {
        "po_id": po_id,
        "supplier_id": payload.supplier_id,
        "supplier_name": s_name,
        "product_id": payload.product_id,
        "product_name": p_name,
        "sku": sku,
        "warehouse_id": payload.warehouse_id,
        "warehouse_name": w_name,
        "quantity": payload.quantity,
        "unit_cost": payload.unit_cost,
        "total_cost": total_cost,
        "lead_time_days": payload.lead_time_days,
        "status": "in_transit",
        "created_at": now_iso,
    }
    persistence.save_purchase_order(po_dict)

    # Dispatched event
    await dispatch_event(
        event_type="PurchaseOrderCreated",
        source_agent="SRM-Procurement",
        payload={
            "po_id": po_id,
            "supplier_name": s_name,
            "product_name": p_name,
            "quantity": payload.quantity,
            "total_cost": total_cost,
        },
    )

    return {"po_id": po_id, "status": "in_transit", "po": po_dict}


@router.post("/orders/{po_id}/receive", summary="Receive inbound stock into warehouse")
async def receive_purchase_order_endpoint(
    po_id: str,
    current_user: dict[str, Any] = Depends(require_authenticated_role(["admin", "operator", "viewer"])),
) -> dict[str, Any]:
    """Receive PO shipment at warehouse dock, replenishing inventory stock in real time."""
    result = persistence.receive_purchase_order(po_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Purchase order '{po_id}' not found")

    # Dispatch canonical InventoryReplenished event to update agent blackboard and digital twin state
    await dispatch_event(
        event_type="InventoryReplenished",
        source_agent="WMS-InboundDock",
        payload={
            "po_id": po_id,
            "product_id": result["product_id"],
            "quantity_replenished": result["quantity_replenished"],
            "warehouse_id": result["warehouse_id"],
        },
    )

    return {
        "success": True,
        "message": f"PO {po_id} received successfully. Stock replenished in warehouse.",
        "details": result,
    }


@router.get("/suppliers", summary="Supplier scorecard and reliability analytics")
async def get_supplier_scorecard() -> dict[str, Any]:
    """Return supplier directory with reliability ratings, lead times, and open orders."""
    pos = persistence.list_purchase_orders(limit=200)
    supplier_orders: dict[str, int] = {}
    for p in pos:
        s_id = p.get("supplier_id")
        if s_id:
            supplier_orders[s_id] = supplier_orders.get(s_id, 0) + 1

    scorecards = []
    for s in BASELINE_SUPPLIERS[:4]:
        scorecards.append({
            "supplier_id": s[0],
            "name": s[1],
            "country": s[2],
            "lead_time_days": s[3],
            "reliability_score": s[4],
            "rating": s[5],
            "status": s[6],
            "risk_tier": "low" if s[4] >= 90 else ("medium" if s[4] >= 80 else "high"),
            "open_purchase_orders": supplier_orders.get(s[0], 0),
        })

    return {"items": scorecards, "total": len(scorecards)}
