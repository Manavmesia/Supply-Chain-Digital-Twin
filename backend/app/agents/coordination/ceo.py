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

        from pydantic import BaseModel

        class CEODecisionSchema(BaseModel):
            approved: bool
            approval_tier: str
            requires_human_approval: bool
            workflow_status: str
            rationale: str

        def _fallback_ceo() -> CEODecisionSchema:
            wf_st = state.get("workflow_status") if state.get("workflow_status") in {"escalated", "failed"} else "completed"
            req_h = bool(state.get("requires_human_approval"))
            if risk_score > 85.0:
                return CEODecisionSchema(
                    approved=False,
                    approval_tier="risk_denied",
                    requires_human_approval=False,
                    workflow_status="failed",
                    rationale=f"Risk score {risk_score} exceeds policy limit of 85.0.",
                )
            elif errors and priority != "critical":
                return CEODecisionSchema(
                    approved=False,
                    approval_tier="error_denied",
                    requires_human_approval=False,
                    workflow_status="failed",
                    rationale="Standard workflow contains unresolved errors.",
                )
            elif total_amount >= Decimal("500000.00"):
                return CEODecisionSchema(
                    approved=True,
                    approval_tier="human_required",
                    requires_human_approval=True,
                    workflow_status=wf_st,
                    rationale="Very high-value order requires human executive oversight.",
                )
            elif (wf_st == "escalated" or req_h) and not (
                state.get("planning", {}).get("remanufacture_required") and "ADS-07" in (state.get("active_agents") or [])
            ):
                return CEODecisionSchema(
                    approved=True,
                    approval_tier="human_required",
                    requires_human_approval=True,
                    workflow_status="escalated",
                    rationale="Workflow escalated for human review and approval.",
                )
            elif total_amount >= Decimal("10000.00"):
                return CEODecisionSchema(
                    approved=True,
                    approval_tier="finance_review",
                    requires_human_approval=False,
                    workflow_status="completed",
                    rationale="Mid-value order requires finance review.",
                )
            else:
                return CEODecisionSchema(
                    approved=True,
                    approval_tier="auto",
                    requires_human_approval=False,
                    workflow_status="completed",
                    rationale="Order satisfied standard approval criteria.",
                )

        ceo_context = {
            "order_id": order.get("order_id"),
            "total_amount": str(total_amount),
            "priority": priority,
            "risk_score": risk_score,
            "error_count": len(errors),
            "requires_human_approval": bool(state.get("requires_human_approval")),
            "workflow_status": state.get("workflow_status"),
        }
        ceo_rules = [
            "If risk_score > 85.0: approved must be False, approval_tier must be 'risk_denied', workflow_status must be 'failed'.",
            "If errors exist and priority is not 'critical': approved must be False, approval_tier must be 'error_denied', workflow_status must be 'failed'.",
            "If total_amount >= 500000.00: approved must be True, approval_tier must be 'human_required', requires_human_approval must be True.",
            "If total_amount >= 10000.00: approved must be True, approval_tier must be 'finance_review', workflow_status must be 'completed'.",
            "Otherwise: approved must be True, approval_tier must be 'auto', workflow_status must be 'completed'.",
            "Rationale must clearly justify the approval tier based on order value, risk, and error constraints.",
        ]

        llm_ceo_dec, ceo_src = await self.decide_with_llm(
            decision_topic="Execute executive peer review and final order sign-off",
            context=ceo_context,
            rules=ceo_rules,
            schema=CEODecisionSchema,
            fallback_callable=_fallback_ceo,
            state=state,
        )

        approved = llm_ceo_dec.approved
        approval_tier = llm_ceo_dec.approval_tier
        requires_human_approval = llm_ceo_dec.requires_human_approval
        workflow_status = llm_ceo_dec.workflow_status
        rationale = llm_ceo_dec.rationale
        order_status = str(order.get("status") or "")

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
            source=ceo_src,
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
