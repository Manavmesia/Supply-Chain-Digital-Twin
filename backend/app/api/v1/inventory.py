"""
Inventory REST API — Phase 3 / Live Stock Levels

GET /api/v1/inventory                    — all inventory across all warehouses
GET /api/v1/inventory/{product_id}       — inventory for a specific product
GET /api/v1/inventory/warehouse/{wh_id}  — all inventory in a warehouse
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.inventory import Inventory
from app.models.product import Product
from app.models.warehouse import Warehouse

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/inventory", tags=["inventory"])


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


@router.get(
    "/summary",
    summary="Inventory summary statistics",
)
async def get_inventory_summary(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Aggregate inventory health metrics across all warehouses."""
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
            (Inventory.available_qty - Inventory.reserved_qty) < Inventory.safety_stock
        )
    )
    low_stock_count = low_stock_result.scalar() or 0

    out_of_stock_result = await session.execute(
        select(func.count(Inventory.inventory_id)).where(
            (Inventory.available_qty - Inventory.reserved_qty) <= 0
        )
    )
    out_of_stock_count = out_of_stock_result.scalar() or 0

    return {
        "total_sku_locations": total_records or 0,
        "total_available_units": int(total_available or 0),
        "total_reserved_units": int(total_reserved or 0),
        "net_available_units": int((total_available or 0) - (total_reserved or 0)),
        "low_stock_locations": low_stock_count,
        "out_of_stock_locations": out_of_stock_count,
        "fill_rate_pct": round(
            100 * (1 - out_of_stock_count / max(total_records or 1, 1)), 2
        ),
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
    result = await session.execute(
        select(Inventory, Warehouse)
        .join(Warehouse, Inventory.warehouse_id == Warehouse.warehouse_id)
        .where(Inventory.product_id == product_id)
    )
    rows = result.all()

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No inventory found for product '{product_id}'",
        )

    # Get product info
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
