"""
Legacy compatibility agent for the decentralized workflow.

This module preserves the previous agent interface for tests and older integrations,
but it does not act as a central decision-maker. Instead it records a peer-review
style decision note that can be surfaced through the shared blackboard.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.agents.base_agent import BaseAgent
from app.graph.state import SupplyChainState


class CEOAgent(BaseAgent):
    """Compatibility shim for older integrations.

    In the decentralized architecture this is treated as a legacy adapter rather
    than a privileged executive node. It writes a decision record to the shared
    state and leaves the actual coordination to the blackboard / consensus loop.
    """

    agent_code = "ADS-17"
    agent_name = "Legacy Compatibility Agent"

    async def _execute(self, state: SupplyChainState) -> dict[str, Any]:
        order = state.get("order") or {}
        risk = state.get("risk") or {}
        errors = state.get("errors") or []

        total_amount = Decimal(str(order.get("total_amount") or "0"))
        priority = order.get("priority") or "standard"
        risk_score = float(risk.get("score", 0.0) or 0.0)

        approved = True
        approval_tier = "auto"
        requires_human_approval = False
        workflow_status = "completed"
        rationale = "Order satisfied standard approval criteria."
        order_status = str(order.get("status") or "")

        if risk_score > 85.0:
            approved = False
            approval_tier = "risk_denied"
            workflow_status = "failed"
            rationale = f"Risk score {risk_score} exceeds policy limit."
        elif errors and priority != "critical":
            approved = False
            approval_tier = "error_denied"
            workflow_status = "failed"
            rationale = "Standard workflow contains unresolved errors."
        elif total_amount >= Decimal("500000.00"):
            approved = True
            approval_tier = "human_required"
            requires_human_approval = True
            rationale = "Very high-value order requires human oversight."
        elif total_amount >= Decimal("10000.00"):
            approved = True
            approval_tier = "finance_review"
            rationale = "Mid-value order requires finance review."

        if approved:
            order_status = "delivered" if order_status not in {"delivered", "cancelled", "failed"} else order_status
        elif order_status not in {"delivered", "cancelled", "failed"}:
            order_status = "cancelled"

        decisions = self._record_decision(
            state,
            "legacy_peer_review",
            rationale,
            {
                "approval_tier": approval_tier,
                "requires_human_approval": requires_human_approval,
                "rationale": rationale,
            },
        )

        result = {
            "executive_decision": {
                "approved": approved,
                "approval_tier": approval_tier,
                "rationale": rationale,
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            },
            "decisions": decisions,
            "workflow_status": workflow_status,
            "order": {
                **order,
                "status": order_status,
            },
        }
        if requires_human_approval:
            result["requires_human_approval"] = True
        return result
