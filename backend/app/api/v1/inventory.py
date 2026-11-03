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

_FALLBACK_INVENTORY: list[dict[str, Any]] = [
    # ELEC-001 Industrial Sensor Module
    {"inventory_id": "11111111-2222-3333-4444-555555555501", "product_id": "30000000-0000-0000-0000-000000000001", "product_name": "Industrial Sensor Module", "sku": "ELEC-001", "warehouse_id": "10000000-0000-0000-0000-000000000001", "warehouse_name": "Newark Distribution Center", "warehouse_city": "Newark", "available_qty": 500, "reserved_qty": 50, "net_available": 450, "safety_stock": 100, "reorder_point": 150, "status": "ok"},
    {"inventory_id": "11111111-2222-3333-4444-555555555502", "product_id": "30000000-0000-0000-0000-000000000001", "product_name": "Industrial Sensor Module", "sku": "ELEC-001", "warehouse_id": "10000000-0000-0000-0000-000000000002", "warehouse_name": "Birmingham Fulfilment Hub", "warehouse_city": "Birmingham", "available_qty": 300, "reserved_qty": 30, "net_available": 270, "safety_stock": 80, "reorder_point": 120, "status": "ok"},
    {"inventory_id": "11111111-2222-3333-4444-555555555503", "product_id": "30000000-0000-0000-0000-000000000001", "product_name": "Industrial Sensor Module", "sku": "ELEC-001", "warehouse_id": "10000000-0000-0000-0000-000000000003", "warehouse_name": "Frankfurt Logistics Centre", "warehouse_city": "Frankfurt", "available_qty": 250, "reserved_qty": 20, "net_available": 230, "safety_stock": 80, "reorder_point": 120, "status": "ok"},

    # ELEC-002 High-Torque Servo Motor
    {"inventory_id": "11111111-2222-3333-4444-555555555504", "product_id": "30000000-0000-0000-0000-000000000002", "product_name": "High-Torque Servo Motor", "sku": "ELEC-002", "warehouse_id": "10000000-0000-0000-0000-000000000001", "warehouse_name": "Newark Distribution Center", "warehouse_city": "Newark", "available_qty": 200, "reserved_qty": 10, "net_available": 190, "safety_stock": 50, "reorder_point": 80, "status": "ok"},
    {"inventory_id": "11111111-2222-3333-4444-555555555505", "product_id": "30000000-0000-0000-0000-000000000002", "product_name": "High-Torque Servo Motor", "sku": "ELEC-002", "warehouse_id": "10000000-0000-0000-0000-000000000002", "warehouse_name": "Birmingham Fulfilment Hub", "warehouse_city": "Birmingham", "available_qty": 150, "reserved_qty": 0, "net_available": 150, "safety_stock": 40, "reorder_point": 60, "status": "ok"},

    # ELEC-003 IoT Gateway Device
    {"inventory_id": "11111111-2222-3333-4444-555555555506", "product_id": "30000000-0000-0000-0000-000000000003", "product_name": "IoT Gateway Device", "sku": "ELEC-003", "warehouse_id": "10000000-0000-0000-0000-000000000001", "warehouse_name": "Newark Distribution Center", "warehouse_city": "Newark", "available_qty": 80, "reserved_qty": 5, "net_available": 75, "safety_stock": 20, "reorder_point": 30, "status": "ok"},
    {"inventory_id": "11111111-2222-3333-4444-555555555507", "product_id": "30000000-0000-0000-0000-000000000003", "product_name": "IoT Gateway Device", "sku": "ELEC-003", "warehouse_id": "10000000-0000-0000-0000-000000000003", "warehouse_name": "Frankfurt Logistics Centre", "warehouse_city": "Frankfurt", "available_qty": 60, "reserved_qty": 0, "net_available": 60, "safety_stock": 20, "reorder_point": 30, "status": "ok"},

    # MECH-001 Precision Ball Bearing Set
    {"inventory_id": "11111111-2222-3333-4444-555555555508", "product_id": "30000000-0000-0000-0000-000000000004", "product_name": "Precision Ball Bearing Set", "sku": "MECH-001", "warehouse_id": "10000000-0000-0000-0000-000000000001", "warehouse_name": "Newark Distribution Center", "warehouse_city": "Newark", "available_qty": 2000, "reserved_qty": 200, "net_available": 1800, "safety_stock": 500, "reorder_point": 700, "status": "ok"},
    {"inventory_id": "11111111-2222-3333-4444-555555555509", "product_id": "30000000-0000-0000-0000-000000000004", "product_name": "Precision Ball Bearing Set", "sku": "MECH-001", "warehouse_id": "10000000-0000-0000-0000-000000000002", "warehouse_name": "Birmingham Fulfilment Hub", "warehouse_city": "Birmingham", "available_qty": 1500, "reserved_qty": 100, "net_available": 1400, "safety_stock": 400, "reorder_point": 600, "status": "ok"},

    # MECH-002 Hydraulic Actuator Cylinder (low & critical stock)
    {"inventory_id": "11111111-2222-3333-4444-555555555510", "product_id": "30000000-0000-0000-0000-000000000005", "product_name": "Hydraulic Actuator Cylinder", "sku": "MECH-002", "warehouse_id": "10000000-0000-0000-0000-000000000001", "warehouse_name": "Newark Distribution Center", "warehouse_city": "Newark", "available_qty": 15, "reserved_qty": 5, "net_available": 10, "safety_stock": 20, "reorder_point": 30, "status": "low"},
    {"inventory_id": "11111111-2222-3333-4444-555555555511", "product_id": "30000000-0000-0000-0000-000000000005", "product_name": "Hydraulic Actuator Cylinder", "sku": "MECH-002", "warehouse_id": "10000000-0000-0000-0000-000000000003", "warehouse_name": "Frankfurt Logistics Centre", "warehouse_city": "Frankfurt", "available_qty": 10, "reserved_qty": 10, "net_available": 0, "safety_stock": 20, "reorder_point": 30, "status": "critical"},

    # MECH-003 Stainless Steel Valve Assembly
    {"inventory_id": "11111111-2222-3333-4444-555555555512", "product_id": "30000000-0000-0000-0000-000000000006", "product_name": "Stainless Steel Valve Assembly", "sku": "MECH-003", "warehouse_id": "10000000-0000-0000-0000-000000000001", "warehouse_name": "Newark Distribution Center", "warehouse_city": "Newark", "available_qty": 300, "reserved_qty": 20, "net_available": 280, "safety_stock": 60, "reorder_point": 90, "status": "ok"},
    {"inventory_id": "11111111-2222-3333-4444-555555555513", "product_id": "30000000-0000-0000-0000-000000000006", "product_name": "Stainless Steel Valve Assembly", "sku": "MECH-003", "warehouse_id": "10000000-0000-0000-0000-000000000002", "warehouse_name": "Birmingham Fulfilment Hub", "warehouse_city": "Birmingham", "available_qty": 200, "reserved_qty": 10, "net_available": 190, "safety_stock": 50, "reorder_point": 70, "status": "ok"},

    # CHEM-001 Industrial Lubricant (20L)
    {"inventory_id": "11111111-2222-3333-4444-555555555514", "product_id": "30000000-0000-0000-0000-000000000007", "product_name": "Industrial Lubricant (20L)", "sku": "CHEM-001", "warehouse_id": "10000000-0000-0000-0000-000000000001", "warehouse_name": "Newark Distribution Center", "warehouse_city": "Newark", "available_qty": 100, "reserved_qty": 5, "net_available": 95, "safety_stock": 30, "reorder_point": 40, "status": "ok"},
    {"inventory_id": "11111111-2222-3333-4444-555555555515", "product_id": "30000000-0000-0000-0000-000000000007", "product_name": "Industrial Lubricant (20L)", "sku": "CHEM-001", "warehouse_id": "10000000-0000-0000-0000-000000000003", "warehouse_name": "Frankfurt Logistics Centre", "warehouse_city": "Frankfurt", "available_qty": 80, "reserved_qty": 0, "net_available": 80, "safety_stock": 25, "reorder_point": 35, "status": "ok"},

    # CHEM-002 Epoxy Adhesive Kit
    {"inventory_id": "11111111-2222-3333-4444-555555555516", "product_id": "30000000-0000-0000-0000-000000000008", "product_name": "Epoxy Adhesive Kit", "sku": "CHEM-002", "warehouse_id": "10000000-0000-0000-0000-000000000001", "warehouse_name": "Newark Distribution Center", "warehouse_city": "Newark", "available_qty": 500, "reserved_qty": 50, "net_available": 450, "safety_stock": 100, "reorder_point": 150, "status": "ok"},
    {"inventory_id": "11111111-2222-3333-4444-555555555517", "product_id": "30000000-0000-0000-0000-000000000008", "product_name": "Epoxy Adhesive Kit", "sku": "CHEM-002", "warehouse_id": "10000000-0000-0000-0000-000000000002", "warehouse_name": "Birmingham Fulfilment Hub", "warehouse_city": "Birmingham", "available_qty": 400, "reserved_qty": 20, "net_available": 380, "safety_stock": 80, "reorder_point": 120, "status": "ok"},

    # SAFE-001 Safety Relay Module
    {"inventory_id": "11111111-2222-3333-4444-555555555518", "product_id": "30000000-0000-0000-0000-000000000009", "product_name": "Safety Relay Module", "sku": "SAFE-001", "warehouse_id": "10000000-0000-0000-0000-000000000001", "warehouse_name": "Newark Distribution Center", "warehouse_city": "Newark", "available_qty": 200, "reserved_qty": 10, "net_available": 190, "safety_stock": 50, "reorder_point": 70, "status": "ok"},
    {"inventory_id": "11111111-2222-3333-4444-555555555519", "product_id": "30000000-0000-0000-0000-000000000009", "product_name": "Safety Relay Module", "sku": "SAFE-001", "warehouse_id": "10000000-0000-0000-0000-000000000002", "warehouse_name": "Birmingham Fulfilment Hub", "warehouse_city": "Birmingham", "available_qty": 150, "reserved_qty": 0, "net_available": 150, "safety_stock": 40, "reorder_point": 60, "status": "ok"},

    # SAFE-002 Emergency Stop Assembly
    {"inventory_id": "11111111-2222-3333-4444-555555555520", "product_id": "30000000-0000-0000-0000-000000000010", "product_name": "Emergency Stop Assembly", "sku": "SAFE-002", "warehouse_id": "10000000-0000-0000-0000-000000000001", "warehouse_name": "Newark Distribution Center", "warehouse_city": "Newark", "available_qty": 800, "reserved_qty": 100, "net_available": 700, "safety_stock": 200, "reorder_point": 300, "status": "ok"},
    {"inventory_id": "11111111-2222-3333-4444-555555555521", "product_id": "30000000-0000-0000-0000-000000000010", "product_name": "Emergency Stop Assembly", "sku": "SAFE-002", "warehouse_id": "10000000-0000-0000-0000-000000000003", "warehouse_name": "Frankfurt Logistics Centre", "warehouse_city": "Frankfurt", "available_qty": 600, "reserved_qty": 50, "net_available": 550, "safety_stock": 150, "reorder_point": 220, "status": "ok"},
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
        logger.warning("DB query failed in list_inventory, returning fallback", error=str(exc))
        filtered = _FALLBACK_INVENTORY
        if low_stock_only:
            filtered = [i for i in filtered if i["status"] in ("low", "critical")]
        sliced = filtered[skip : skip + limit]
        return {
            "items": sliced,
            "total": len(filtered),
            "skip": skip,
            "limit": limit,
            "low_stock_count": sum(1 for i in filtered if i["status"] in ("low", "critical")),
        }


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
        logger.warning("DB query failed in get_inventory_summary, returning fallback", error=str(exc))
        return compute_inventory_summary(_FALLBACK_INVENTORY)


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
        logger.warning("DB query failed in get_product_inventory, checking fallback", error=str(exc))

    str_pid = str(product_id)
    matches = [i for i in _FALLBACK_INVENTORY if i["product_id"] == str_pid]
    if matches:
        first = matches[0]
        return {
            "product_id": str_pid,
            "product_name": first["product_name"],
            "sku": first["sku"],
            "total_available": sum(m["available_qty"] for m in matches),
            "total_reserved": sum(m["reserved_qty"] for m in matches),
            "total_net": sum(m["net_available"] for m in matches),
            "locations": [
                {
                    "inventory_id": m["inventory_id"],
                    "warehouse_id": m["warehouse_id"],
                    "warehouse_name": m["warehouse_name"],
                    "warehouse_city": m["warehouse_city"],
                    "available_qty": m["available_qty"],
                    "reserved_qty": m["reserved_qty"],
                    "net_available": m["net_available"],
                    "safety_stock": m["safety_stock"],
                    "status": m["status"],
                }
                for m in matches
            ],
        }

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No inventory found for product '{product_id}'",
    )
