"""Repository for SupportTicket domain queries."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from app.models.support_ticket import SupportTicket
from app.repositories.base import BaseRepository
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class SupportTicketRepository(BaseRepository[SupportTicket]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(SupportTicket, session)

    async def get_open_by_customer(
        self, customer_id: uuid.UUID
    ) -> Sequence[SupportTicket]:
        """Return all non-resolved, non-closed tickets for a customer, oldest first.

        Statuses considered 'open': open, in_progress, pending_customer, escalated.
        """
        query = (
            select(SupportTicket)
            .where(
                SupportTicket.customer_id == customer_id,
                SupportTicket.status.in_(
                    ["open", "in_progress", "pending_customer", "escalated"]
                ),
            )
            .order_by(SupportTicket.created_at.asc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_sla_breaching(self) -> Sequence[SupportTicket]:
        """Return open tickets whose SLA deadline has passed and are not yet
        resolved or escalated.

        Called periodically by the Customer Service Agent to trigger escalation.
        """
        now = datetime.now(tz=UTC)
        query = select(SupportTicket).where(
            SupportTicket.sla_deadline <= now,
            SupportTicket.status.in_(["open", "in_progress", "pending_customer"]),
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def escalate(self, ticket_id: uuid.UUID) -> SupportTicket | None:
        """Mark a ticket as escalated and record the escalation timestamp.

        Returns the updated ticket, or None if not found.
        """
        ticket = await self.get(ticket_id)
        if ticket is None:
            return None

        ticket.status = "escalated"
        ticket.escalated_at = datetime.now(tz=UTC)
        await self.session.flush()
        return ticket
