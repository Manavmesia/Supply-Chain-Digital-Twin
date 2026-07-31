"""
ADS-17 — CEO Agent

Responsibilities (from AIS-17 spec + System Rules Finance Approval Thresholds):
  - Review the completed workflow state
  - Apply Finance Approval Thresholds (from System Rules §6 / seed data doc):
      ≤ $10,000                     → auto-approve
      $10,001 – $50,000             → approve with audit entry
      $50,001 – $500,000            → approve + flag for Finance review
      > $500,000                    → approve + require human escalation
  - Check risk signals from state["risk"] (Phase 4 adds actual risk data)
  - Publish CEOApprovalGranted or CEOApprovalDenied
  - Record structured decision to decisions list
  - Mark order as delivered (approved) or cancelled (denied)
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_agent import BaseAgent
from app.graph.state import SupplyChainState

logger = structlog.get_logger(__name__)

# Finance Approval Thresholds — System Rules v2.1
_AUTO_APPROVE_LIMIT   = Decimal("10000.00")
_FINANCE_REVIEW_LIMIT = Decimal("50000.00")
_HUMAN_APPROVAL_LIMIT = Decimal("500000.00")


class CEOAgent(BaseAgent):
    agent_code = "ADS-17"
    agent_name = "CEO Agent"

    async def _execute(self, state: SupplyChainState) -> dict[str, Any]:
        session: AsyncSession = self.session
        order: dict = state.get("order") or {}
        risk: dict = state.get("risk") or {}
        supplier_state: dict = state.get("supplier") or {}

        order_id_str = order.get("order_id")
        total_amount = Decimal(str(order.get("total_amount", "0")))
        priority = order.get("priority", "standard")

        # ── 1. Gather decision inputs ─────────────────────────────────────────
        risk_score: float = float(risk.get("score", 0.0))
        has_supplier_issue = supplier_state.get("status") == "unavailable"
        error_count = len(state.get("errors") or [])

        # ── 2. Determine approval and escalation ──────────────────────────────
        requires_human = False
        approval_tier = "auto"
        denial_reason: str | None = None

        if error_count > 0 and priority not in ("high", "critical"):
            denial_reason = f"Workflow has {error_count} error(s) — requires manual review"
        elif risk_score > 85:
            denial_reason = f"Risk score {risk_score:.0f} exceeds maximum threshold (85)"
        else:
            # Finance Approval Thresholds
            if total_amount <= _AUTO_APPROVE_LIMIT:
                approval_tier = "auto"
            elif total_amount <= _FINANCE_REVIEW_LIMIT:
                approval_tier = "finance_review"
            elif total_amount <= _HUMAN_APPROVAL_LIMIT:
                approval_tier = "finance_and_ceo"
            else:
                approval_tier = "human_required"
                requires_human = True

        approved = denial_reason is None
        event_type = "CEOApprovalGranted" if approved else "CEOApprovalDenied"

        # ── 3. Publish decision event ─────────────────────────────────────────
        event_payload = {
            "workflow_id": state.get("workflow_id"),
            "order_id": order_id_str,
            "approved": approved,
            "approval_tier": approval_tier,
            "total_amount": str(total_amount),
            "risk_score": risk_score,
            "reason": denial_reason or f"Approved under {approval_tier} policy",
            "requires_human_approval": requires_human,
        }

        await self._publish(state, event_type, event_payload)
        event_history = self._append_event(state, event_type, event_payload)
        decisions = self._record_decision(
            state,
            "ceo_decision",
            event_payload["reason"],
            event_payload,
        )

        # ── 4. Update order status ────────────────────────────────────────────
        if order_id_str and session:
            import uuid
            new_status = "delivered" if approved else "cancelled"
            await session.execute(
                update(__import__("app.models.order", fromlist=["Order"]).Order)
                .where(
                    __import__("app.models.order", fromlist=["Order"]).Order.order_id
                    == uuid.UUID(order_id_str)
                )
                .values(status=new_status)
            )
            await session.flush()

        log_fn = logger.info if approved else logger.warning
        log_fn(
            "CEO decision",
            approved=approved,
            tier=approval_tier,
            total_amount=str(total_amount),
            order_id=order_id_str,
            workflow_id=state.get("workflow_id"),
        )

        return {
            "executive_decision": event_payload,
            "order": {**order, "status": "delivered" if approved else "cancelled"},
            "workflow_status": "completed" if approved else "failed",
            "decisions": decisions,
            "event_history": event_history,
            "requires_human_approval": requires_human,
        }
