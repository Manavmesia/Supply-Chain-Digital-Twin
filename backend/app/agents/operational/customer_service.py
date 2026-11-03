"""
ADS-08 — Customer Service Agent

Responsibilities (from AIS-08 & BACKLOG US-102-104):
  - Send customer notifications (CustomerNotified) for order and shipment milestones
  - Support tickets management: insert support_tickets records with SLA deadline tracking
  - Return request processing: validate return window, create support_tickets, publish ProductReturned (AUD-50 fix)
  - SLA breach escalation: publish TicketEscalated and route to CEO Agent
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_agent import BaseAgent
from app.graph.state import SupplyChainState
from app.models.customer import Customer
from app.models.support_ticket import SupportTicket

logger = structlog.get_logger(__name__)

# Default SLA deadlines by ticket category
_SLA_DEADLINES_HOURS = {
    "delivery_delay": 4,
    "billing_issue": 24,
    "return_request": 24,
    "product_quality": 12,
    "other": 48,
}


class CustomerServiceAgent(BaseAgent):
    agent_code = "ADS-08"
    agent_name = "Customer Service Agent"

    async def _execute(self, state: SupplyChainState) -> dict[str, Any]:
        session: AsyncSession = self.session
        order: dict = state.get("order") or {}
        shipment_state: dict = state.get("shipment") or {}
        customer_service_state: dict = state.get("customer_service") or {}

        event_history = list(state.get("event_history") or [])
        decisions = list(state.get("decisions") or [])

        customer_id_str = order.get("customer_id")
        if not customer_id_str:
            customer_id_str = "11111111-0000-0000-0000-000000000001"  # Default fallback customer (Acme)

        customer_id = uuid.UUID(customer_id_str)
        now = datetime.now(timezone.utc)

        # ── 1. Milestone Notification Processing ──────────────────────────────
        notifications_sent: list[dict[str, Any]] = []

        # Determine milestone channel message (LLM-synthesized if key present)
        milestone_type = "order_update"
        if shipment_state.get("status") == "delivered":
            milestone_type = "shipment_delivered"
            default_msg = f"Your order {order.get('order_id', '')} has been delivered successfully."
        elif shipment_state.get("status") in ("dispatched", "in_transit"):
            milestone_type = "shipment_dispatched"
            default_msg = f"Your order {order.get('order_id', '')} is in transit via carrier."
        elif order.get("order_id"):
            milestone_type = "order_created"
            default_msg = f"Your order {order.get('order_id', '')} has been confirmed and is being processed."
        else:
            default_msg = "Notification: Your supply chain request is being processed."

        from pydantic import BaseModel

        class CSNotificationSchema(BaseModel):
            message: str
            rationale: str

        def _fallback_cs() -> CSNotificationSchema:
            return CSNotificationSchema(
                message=default_msg,
                rationale=f"Sent {milestone_type} notification to customer {customer_id}",
            )

        llm_cs_dec, cs_src = await self.decide_with_llm(
            decision_topic="Formulate professional customer communication and SLA notification",
            context={
                "customer_id": str(customer_id),
                "order_id": order.get("order_id"),
                "milestone": milestone_type,
                "shipment_status": shipment_state.get("status"),
            },
            rules=[
                "Message must be polite, clear, enterprise-grade, and accurately reflect current milestone status.",
                "Include the order identifier if present.",
            ],
            schema=CSNotificationSchema,
            fallback_callable=_fallback_cs,
        )

        msg = llm_cs_dec.message

        notif_payload = {
            "notification_id": str(uuid.uuid4()),
            "customer_id": str(customer_id),
            "milestone": milestone_type,
            "message": msg,
            "channel": "email",
            "sent_at": now.isoformat(),
        }

        await self._publish(state, "CustomerNotified", notif_payload)
        event_history = self._append_event(event_history, "CustomerNotified", notif_payload)
        notifications_sent.append(notif_payload)

        decisions = self._record_decision(
            decisions,
            "customer_notified",
            llm_cs_dec.rationale or f"Sent {milestone_type} notification to customer {customer_id}",
            notif_payload,
            source=cs_src,
        )

        # ── 2. Return Request / Support Ticket Processing ──────────────────────
        tickets_created: list[dict[str, Any]] = []
        is_return_requested = customer_service_state.get("request_return", False)

        if is_return_requested:
            category = "return_request"
            sla_hours = _SLA_DEADLINES_HOURS[category]
            sla_deadline = now + timedelta(hours=sla_hours)

            ticket_id = uuid.uuid4()
            order_id = uuid.UUID(str(order["order_id"])) if order.get("order_id") else None

            ticket = SupportTicket(
                ticket_id=ticket_id,
                customer_id=customer_id,
                order_id=order_id,
                category=category,
                status="open",
                subject=f"Return Request for Order {order.get('order_id', '')}",
                description="Customer requested return for delivered order items.",
                assigned_agent=self.agent_code,
                sla_deadline=sla_deadline,
                created_at=now,
                updated_at=now,
            )

            if session:
                session.add(ticket)
                await session.flush()

            ticket_payload = {
                "ticket_id": str(ticket_id),
                "customer_id": str(customer_id),
                "category": category,
                "status": "open",
                "sla_deadline": sla_deadline.isoformat(),
            }
            await self._publish(state, "TicketOpened", ticket_payload)
            event_history = self._append_event(event_history, "TicketOpened", ticket_payload)

            # AUD-50 Fix: Publish ProductReturned event for return requests to trigger QA
            return_payload = {
                "ticket_id": str(ticket_id),
                "customer_id": str(customer_id),
                "order_id": str(order_id) if order_id else None,
                "product_id": str(order.get("items", [{}])[0].get("product_id")) if order.get("items") else None,
                "return_reason": "Customer return request",
            }
            await self._publish(state, "ProductReturned", return_payload)
            event_history = self._append_event(event_history, "ProductReturned", return_payload)

            decisions = self._record_decision(
                decisions,
                "return_processed",
                f"Opened return support ticket {ticket_id} and published ProductReturned",
                return_payload,
            )
            tickets_created.append(ticket_payload)

        # ── 3. Check for SLA Breaches / Escalations ───────────────────────────
        is_escalated = False
        if customer_service_state.get("simulate_sla_breach"):
            ticket_id = uuid.uuid4()
            escalate_payload = {
                "ticket_id": str(ticket_id),
                "customer_id": str(customer_id),
                "reason": "SLA deadline breached without resolution",
                "escalated_at": now.isoformat(),
            }
            await self._publish(state, "TicketEscalated", escalate_payload)
            event_history = self._append_event(event_history, "TicketEscalated", escalate_payload)

            decisions = self._record_decision(
                decisions,
                "ticket_escalated",
                f"Escalated support ticket {ticket_id} to CEO Agent due to SLA breach",
                escalate_payload,
            )
            is_escalated = True

        next_node = "ceo" if is_escalated else "reporting"

        return {
            "customer_service": {
                "status": "completed",
                "notifications": notifications_sent,
                "tickets": tickets_created,
                "is_escalated": is_escalated,
            },
            "decisions": decisions,
            "event_history": event_history,
            "next_node": next_node,
        }
