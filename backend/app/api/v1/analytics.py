"""
Analytics REST API — Phase 4

GET /api/v1/analytics/summary
    Aggregate enterprise KPIs across orders, shipments, inventory, and reports.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.order import Order
from app.models.report import Report
from app.models.shipment import Shipment

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get(
    "/summary",
    summary="Get digital twin analytics KPI summary",
)
async def get_analytics_summary(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Aggregate high-level enterprise metrics across operational domains."""
    # Order counts and revenue
    order_res = await session.execute(
        select(
            func.count(Order.order_id),
            func.coalesce(func.sum(Order.total_amount), 0),
        )
    )
    total_orders, total_revenue = order_res.one()

    # Shipment count
    shipment_res = await session.execute(
        select(func.count(Shipment.shipment_id))
    )
    total_shipments = shipment_res.scalar() or 0

    # Total reports generated
    report_res = await session.execute(
        select(func.count(Report.report_id))
    )
    total_reports = report_res.scalar() or 0

    return {
        "kpis": {
            "total_orders": total_orders,
            "total_revenue": str(total_revenue),
            "total_shipments": total_shipments,
            "total_reports_generated": total_reports,
            "system_health": "healthy",
            "active_phase": "Phase 4 — Business Intelligence",
        }
    }
