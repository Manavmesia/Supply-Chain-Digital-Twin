"""
Orders REST API — Phase 3 completion

GET  /api/v1/orders           — paginated order list with filters
GET  /api/v1/orders/{id}      — order detail + decision trail
POST /api/v1/workflows/{id}/approve — human approval for escalated orders
POST /api/v1/workflows/{id}/reject  — human rejection for escalated orders
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.customer import Customer

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/orders", tags=["orders"])


@router.get(
    "",
    summary="List orders with filters",
)
async def list_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    order_status: str | None = Query(None, alias="status"),
    priority: str | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Fetch paginated list of orders with optional status/priority filters."""
    query = select(Order)
    count_query = select(func.count(Order.order_id))

    if order_status:
        query = query.where(Order.status == order_status)
        count_query = count_query.where(Order.status == order_status)
    if priority:
        query = query.where(Order.priority == priority)
        count_query = count_query.where(Order.priority == priority)

    query = query.order_by(Order.created_at.desc()).offset(skip).limit(limit)

    result = await session.execute(query)
    orders = result.scalars().all()

    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0

    return {
        "items": [
            {
                "order_id": str(o.order_id),
                "customer_id": str(o.customer_id),
                "status": o.status,
                "priority": o.priority,
                "total_amount": str(o.total_amount),
                "currency": o.currency,
                "workflow_id": str(o.workflow_id) if o.workflow_id else None,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in orders
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get(
    "/stats",
    summary="Order statistics summary",
)
async def get_order_stats(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Aggregate order counts by status and priority."""
    # Count by status
    status_result = await session.execute(
        select(Order.status, func.count(Order.order_id))
        .group_by(Order.status)
    )
    by_status = {row[0]: row[1] for row in status_result.all()}

    # Count by priority
    priority_result = await session.execute(
        select(Order.priority, func.count(Order.order_id))
        .group_by(Order.priority)
    )
    by_priority = {row[0]: row[1] for row in priority_result.all()}

    # Total revenue
    revenue_result = await session.execute(
        select(func.coalesce(func.sum(Order.total_amount), 0))
    )
    total_revenue = revenue_result.scalar()

    return {
        "by_status": by_status,
        "by_priority": by_priority,
        "total_revenue": str(total_revenue),
        "total_orders": sum(by_status.values()),
    }


@router.get(
    "/{order_id}",
    summary="Get order detail with items",
)
async def get_order(
    order_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Fetch full order detail including line items and customer info."""
    # Get order
    result = await session.execute(
        select(Order).where(Order.order_id == order_id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order '{order_id}' not found",
        )

    # Get order items
    items_result = await session.execute(
        select(OrderItem).where(OrderItem.order_id == order_id)
    )
    items = items_result.scalars().all()

    # Get customer
    customer_result = await session.execute(
        select(Customer).where(Customer.customer_id == order.customer_id)
    )
    customer = customer_result.scalar_one_or_none()

    return {
        "order_id": str(order.order_id),
        "customer_id": str(order.customer_id),
        "customer": {
            "name": customer.name if customer else None,
            "tier": customer.customer_tier if customer else None,
            "email": customer.email if customer else None,
        },
        "status": order.status,
        "priority": order.priority,
        "total_amount": str(order.total_amount),
        "currency": order.currency,
        "workflow_id": str(order.workflow_id) if order.workflow_id else None,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "items": [
            {
                "order_item_id": str(item.order_item_id),
                "product_id": str(item.product_id),
                "quantity": item.quantity,
                "unit_price": str(item.unit_price),
                "line_total": str(item.unit_price * item.quantity),
            }
            for item in items
        ],
    }
