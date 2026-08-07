"""
Suppliers REST API — Phase 3

GET /api/v1/suppliers            — list suppliers with health scores
GET /api/v1/suppliers/stats      — aggregate supplier health metrics
GET /api/v1/suppliers/{id}       — supplier detail + recent POs
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.supplier import Supplier
from app.models.purchase_order import PurchaseOrder

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.get(
    "",
    summary="List all suppliers with health metrics",
)
async def list_suppliers(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    active_only: bool = Query(True),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Fetch all suppliers with reliability scores and status."""
    query = select(Supplier)
    count_query = select(func.count(Supplier.supplier_id))

    if active_only:
        query = query.where(Supplier.status == "active")
        count_query = count_query.where(Supplier.status == "active")

    query = query.order_by(Supplier.reliability_score.desc()).offset(skip).limit(limit)

    result = await session.execute(query)
    suppliers = result.scalars().all()

    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0

    return {
        "items": [
            {
                "supplier_id": str(s.supplier_id),
                "name": s.name,
                "country": s.country,
                "lead_time_days": s.lead_time_days,
                "reliability_score": float(s.reliability_score),
                "rating": float(s.rating) if s.rating is not None else None,
                "status": s.status,
                "risk_tier": (
                    "low" if float(s.reliability_score) >= 90 else
                    "medium" if float(s.reliability_score) >= 75 else
                    "high"
                ),
            }
            for s in suppliers
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get(
    "/stats",
    summary="Supplier health aggregate statistics",
)
async def get_supplier_stats(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Aggregate supplier reliability and risk tier distribution."""
    result = await session.execute(
        select(
            func.count(Supplier.supplier_id),
            func.avg(Supplier.reliability_score),
            func.min(Supplier.reliability_score),
            func.max(Supplier.reliability_score),
        ).where(Supplier.status == "active")
    )
    total, avg_reliability, min_rel, max_rel = result.one()

    # Risk tier distribution
    tiers = {"low": 0, "medium": 0, "high": 0}
    all_result = await session.execute(
        select(Supplier.reliability_score).where(Supplier.status == "active")
    )
    for (score,) in all_result.all():
        score_f = float(score)
        if score_f >= 90:
            tiers["low"] += 1
        elif score_f >= 75:
            tiers["medium"] += 1
        else:
            tiers["high"] += 1

    return {
        "total_active": total or 0,
        "avg_reliability_score": round(float(avg_reliability or 0), 2),
        "min_reliability_score": round(float(min_rel or 0), 2),
        "max_reliability_score": round(float(max_rel or 0), 2),
        "risk_tier_distribution": tiers,
    }


@router.get(
    "/{supplier_id}",
    summary="Get supplier detail with recent purchase orders",
)
async def get_supplier(
    supplier_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Fetch full supplier profile and last 10 purchase orders."""
    result = await session.execute(
        select(Supplier).where(Supplier.supplier_id == supplier_id)
    )
    supplier = result.scalar_one_or_none()

    if supplier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier '{supplier_id}' not found",
        )

    # Fetch recent POs
    po_result = await session.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.supplier_id == supplier_id)
        .order_by(PurchaseOrder.created_at.desc())
        .limit(10)
    )
    pos = po_result.scalars().all()

    return {
        "supplier_id": str(supplier.supplier_id),
        "name": supplier.name,
        "country": supplier.country,
        "lead_time_days": supplier.lead_time_days,
        "reliability_score": float(supplier.reliability_score),
        "rating": float(supplier.rating) if supplier.rating is not None else None,
        "status": supplier.status,
        "risk_tier": (
            "low" if float(supplier.reliability_score) >= 90 else
            "medium" if float(supplier.reliability_score) >= 75 else
            "high"
        ),
        "recent_purchase_orders": [
            {
                "po_id": str(po.purchase_order_id),
                "status": po.status,
                "total_amount": str(po.total_amount),
                "quantity": po.quantity,
                "created_at": po.created_at.isoformat() if po.created_at else None,
            }
            for po in pos
        ],
    }
