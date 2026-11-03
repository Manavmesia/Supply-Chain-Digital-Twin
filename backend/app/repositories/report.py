"""Repository for Report domain queries."""

import uuid
from collections.abc import Sequence
from typing import Any

from app.models.report import Report
from app.repositories.base import BaseRepository
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class ReportRepository(BaseRepository[Report]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Report, session)

    async def get_by_id(self, report_id: uuid.UUID) -> Report | None:
        """Fetch report by primary key ID."""
        return await self.get(report_id)

    async def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None,
    ) -> Sequence[Report]:
        """Fetch paginated reports with optional filtering."""
        query = select(Report)
        if filters:
            if "status" in filters and filters["status"]:
                query = query.where(Report.status == filters["status"])
            if "report_type" in filters and filters["report_type"]:
                query = query.where(Report.report_type == filters["report_type"])
            if "workflow_id" in filters and filters["workflow_id"]:
                query = query.where(Report.workflow_id == filters["workflow_id"])
        query = query.order_by(Report.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count total reports matching optional filters."""
        query = select(func.count(Report.report_id))
        if filters:
            if "status" in filters and filters["status"]:
                query = query.where(Report.status == filters["status"])
            if "report_type" in filters and filters["report_type"]:
                query = query.where(Report.report_type == filters["report_type"])
            if "workflow_id" in filters and filters["workflow_id"]:
                query = query.where(Report.workflow_id == filters["workflow_id"])
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_by_type(self, report_type: str) -> Sequence[Report]:
        """Return all non-archived reports of the given *report_type*, newest first.

        Valid values: executive_summary, operational_kpi, financial, risk,
        sustainability, quality, audit, workflow, custom.
        """
        query = (
            select(Report)
            .where(
                Report.report_type == report_type,
                Report.status != "archived",
            )
            .order_by(Report.created_at.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_workflow(self, workflow_id: uuid.UUID) -> Sequence[Report]:
        """Return all reports generated within a specific workflow execution.

        Useful for the Reporting Agent to bundle all reports for a given
        supply chain run and for the CEO Agent's decision audit trail.
        """
        query = (
            select(Report)
            .where(Report.workflow_id == workflow_id)
            .order_by(Report.created_at.asc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def archive(self, report_id: uuid.UUID) -> Report | None:
        """Set a report's status to 'archived'.

        Returns the updated report, or None if it does not exist.
        Archived reports are excluded from ``get_by_type`` results but
        remain in the database for audit purposes.
        """
        report = await self.get(report_id)
        if report is None:
            return None

        report.status = "archived"
        await self.session.flush()
        return report
