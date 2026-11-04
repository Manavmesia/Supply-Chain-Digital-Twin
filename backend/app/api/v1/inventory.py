"""
Inventory REST API — Phase 3 / Live Stock Levels

GET /api/v1/inventory                    — all inventory across all warehouses
GET /api/v1/inventory/{product_id}       — inventory for a specific product
GET /api/v1/inventory/warehouse/{wh_id}  — all inventory in a warehouse
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import require_authenticated_role

from app.core import persistence
from app.core.database import get_db_session
from app.models.inventory import Inventory
from app.models.product import Product
from app.models.warehouse import Warehouse

from app.core.catalog import BASELINE_INVENTORY, BASELINE_WAREHOUSES, PRODUCT_MAP

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/inventory", tags=["inventory"])

_WH_MAP = {w[0]: (w[1], w[2]) for w in BASELINE_WAREHOUSES}

_FALLBACK_INVENTORY: list[dict[str, Any]] = [
    {
        "inventory_id": inv[0],
        "product_id": inv[1],
        "product_name": PRODUCT_MAP.get(inv[1], ("Industrial Component", ""))[0],
        "sku": PRODUCT_MAP.get(inv[1], ("", "ELEC-001"))[1],
        "warehouse_id": inv[2],
        "warehouse_name": _WH_MAP.get(inv[2], ("Distribution Center", ""))[0],
        "warehouse_city": _WH_MAP.get(inv[2], ("", "Newark"))[1],
        "available_qty": inv[3],
        "reserved_qty": inv[4],
        "net_available": inv[3] - inv[4],
        "safety_stock": inv[5],
        "reorder_point": inv[6],
        "status": inv[7],
    }
    for inv in BASELINE_INVENTORY
]


def compute_inventory_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate exact aggregate inventory metrics from an item list."""
    total_records = len(items)
    total_available = sum(int(i["available_qty"]) for i in items)
    total_reserved = sum(int(i["reserved_qty"]) for i in items)
    net_available = total_available - total_reserved
    low_stock_count = sum(1 for i in items if i["status"] == "low")
    out_of_stock_count = sum(1 for i in items if i["status"] == "critical")
    fill_rate = round(100.0 * (1 - out_of_stock_count / max(total_records, 1)), 1)
    return {
        "total_sku_locations": total_records,
        "total_available_units": total_available,
        "total_reserved_units": total_reserved,
        "net_available_units": net_available,
        "low_stock_locations": low_stock_count,
        "out_of_stock_locations": out_of_stock_count,
        "fill_rate_pct": fill_rate,
    }


@router.get(
    "",
    summary="List all inventory levels",
)
async def list_inventory(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    low_stock_only: bool = Query(False, description="Filter to safety-stock violations"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Fetch paginated inventory levels with product and warehouse details."""
    try:
        query = (
            select(Inventory, Product, Warehouse)
            .join(Product, Inventory.product_id == Product.product_id)
            .join(Warehouse, Inventory.warehouse_id == Warehouse.warehouse_id)
        )

        if low_stock_only:
            query = query.where(
                (Inventory.available_qty - Inventory.reserved_qty) < Inventory.safety_stock
            )

        query = query.offset(skip).limit(limit)

        result = await session.execute(query)
        rows = result.all()

        # Count total
        count_query = select(func.count(Inventory.inventory_id))
        if low_stock_only:
            count_query = count_query.where(
                (Inventory.available_qty - Inventory.reserved_qty) < Inventory.safety_stock
            )
        count_result = await session.execute(count_query)
        total = count_result.scalar() or 0

        items = []
        for inv, product, warehouse in rows:
            net_available = int(inv.available_qty) - int(inv.reserved_qty)
            items.append({
                "inventory_id": str(inv.inventory_id),
                "product_id": str(inv.product_id),
                "product_name": product.name,
                "sku": product.sku,
                "warehouse_id": str(inv.warehouse_id),
                "warehouse_name": warehouse.name,
                "warehouse_city": warehouse.city,
                "available_qty": int(inv.available_qty),
                "reserved_qty": int(inv.reserved_qty),
                "net_available": net_available,
                "safety_stock": int(inv.safety_stock),
                "reorder_point": int(inv.reorder_point) if hasattr(inv, "reorder_point") else None,
                "status": "critical" if net_available <= 0 else (
                    "low" if net_available < int(inv.safety_stock) else "ok"
                ),
            })

        return {
            "items": items,
            "total": total,
            "skip": skip,
            "limit": limit,
            "low_stock_count": sum(1 for i in items if i["status"] in ("low", "critical")),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("DB query failed in list_inventory, returning persistent live data", error=str(exc))
        return persistence.list_inventory(skip=skip, limit=limit, low_stock_only=low_stock_only)


@router.get(
    "/summary",
    summary="Inventory summary statistics",
)
async def get_inventory_summary(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Aggregate inventory health metrics across all warehouses."""
    try:
        result = await session.execute(
            select(
                func.count(Inventory.inventory_id),
                func.sum(Inventory.available_qty),
                func.sum(Inventory.reserved_qty),
            )
        )
        total_records, total_available, total_reserved = result.one()

        low_stock_result = await session.execute(
            select(func.count(Inventory.inventory_id)).where(
                (Inventory.available_qty - Inventory.reserved_qty) < Inventory.safety_stock,
                (Inventory.available_qty - Inventory.reserved_qty) > 0,
            )
        )
        low_stock_count = low_stock_result.scalar() or 0

        out_of_stock_result = await session.execute(
            select(func.count(Inventory.inventory_id)).where(
                (Inventory.available_qty - Inventory.reserved_qty) <= 0
            )
        )
        out_of_stock_count = out_of_stock_result.scalar() or 0

        avail_units = int(total_available or 0)
        res_units = int(total_reserved or 0)

        return {
            "total_sku_locations": total_records or 0,
            "total_available_units": avail_units,
            "total_reserved_units": res_units,
            "net_available_units": avail_units - res_units,
            "low_stock_locations": low_stock_count,
            "out_of_stock_locations": out_of_stock_count,
            "fill_rate_pct": round(
                100 * (1 - out_of_stock_count / max(total_records or 1, 1)), 1
            ),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("DB query failed in get_inventory_summary, returning persistent live data", error=str(exc))
        return persistence.get_inventory_summary()


# ── Inbound Replenishment REST Endpoints ─────────────────────────────────────

@router.get(
    "/replenishment-orders",
    summary="List autonomous inbound replenishment purchase orders",
)
async def list_replenishment_orders(
    limit: int = Query(50, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
) -> dict[str, Any]:
    """Retrieve autonomous purchase orders drafted by ADS-05 Supplier Agent."""
    orders = persistence.list_purchase_orders(limit=limit, status_filter=status_filter)
    return {
        "items": orders,
        "total": len(orders),
        "limit": limit,
    }


@router.post(
    "/replenishment-orders/{po_id}/receive",
    summary="Receive an inbound shipment and replenish warehouse inventory",
)
async def receive_replenishment_order(
    po_id: str,
    _user: Annotated[dict, Depends(require_authenticated_role("admin", "analyst"))] = None,
) -> dict[str, Any]:
    """Commit inbound stock receipt to warehouse inventory, completing the replenishment loop."""
    result = persistence.receive_purchase_order(po_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Purchase order '{po_id}' not found",
        )
    return {
        "success": True,
        "message": f"Inbound replenishment {po_id} received successfully. Stock added to warehouse.",
        "data": result,
    }


@router.get(
    "/{product_id}",
    summary="Get inventory for a specific product",
)
async def get_product_inventory(
    product_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Fetch inventory levels for a single product across all warehouses."""
    try:
        result = await session.execute(
            select(Inventory, Warehouse)
            .join(Warehouse, Inventory.warehouse_id == Warehouse.warehouse_id)
            .where(Inventory.product_id == product_id)
        )
        rows = result.all()

        if rows:
            product_result = await session.execute(
                select(Product).where(Product.product_id == product_id)
            )
            product = product_result.scalar_one_or_none()

            locations = []
            for inv, warehouse in rows:
                net_available = int(inv.available_qty) - int(inv.reserved_qty)
                locations.append({
                    "inventory_id": str(inv.inventory_id),
                    "warehouse_id": str(inv.warehouse_id),
                    "warehouse_name": warehouse.name,
                    "warehouse_city": warehouse.city,
                    "available_qty": int(inv.available_qty),
                    "reserved_qty": int(inv.reserved_qty),
                    "net_available": net_available,
                    "safety_stock": int(inv.safety_stock),
                    "status": "critical" if net_available <= 0 else (
                        "low" if net_available < int(inv.safety_stock) else "ok"
                    ),
                })

            return {
                "product_id": str(product_id),
                "product_name": product.name if product else None,
                "sku": product.sku if product else None,
                "total_available": sum(loc["available_qty"] for loc in locations),
                "total_reserved": sum(loc["reserved_qty"] for loc in locations),
                "total_net": sum(loc["net_available"] for loc in locations),
                "locations": locations,
            }
    except Exception as exc:  # noqa: BLE001
        logger.warning("DB query failed in get_product_inventory, checking persistent storage", error=str(exc))

    str_pid = str(product_id)
    matches = persistence.get_inventory_for_product(str_pid)
    if matches:
        first = matches[0]
        return {
            "product_id": str_pid,
            "product_name": first["product_name"],
            "sku": first["sku"],
            "total_available": sum(m["available_qty"] for m in matches),
            "total_reserved": sum(m["reserved_qty"] for m in matches),
            "total_net": sum(m["net_available"] for m in matches),
            "locations": matches,
        }

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No inventory found for product '{product_id}'",
    )
