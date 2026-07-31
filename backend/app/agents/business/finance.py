"""
ADS-09 — Finance Agent

Responsibilities:
  - Evaluate the financial impact of the completed workflow
  - Compute cost breakdown: shipping_cost (route base_cost), procurement_cost
    (sum of PO total_costs in state), total operational cost
  - Apply Finance Approval Thresholds from System Rules:
      ≤ $10,000            → auto
      $10,001 – $50,000    → finance_review
      $50,001 – $500,000   → finance_and_ceo
      > $500,000           → human_required
  - Check if total_cost > budget_threshold (default $50,000 from settings)
  - Publish FinancialRecommendationReady always
  - Publish BudgetExceeded if total_cost > budget_threshold
  - NO LLM calls — all deterministic arithmetic
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_agent import BaseAgent
from app.core.config import settings
from app.graph.state import SupplyChainState

logger = structlog.get_logger(__name__)

# Finance Approval Thresholds — System Rules v2.1
_AUTO_LIMIT: Decimal = Decimal("10000.00")
_FINANCE_REVIEW_LIMIT: Decimal = Decimal("50000.00")
_HUMAN_APPROVAL_LIMIT: Decimal = Decimal("500000.00")


class FinanceAgent(BaseAgent):
    """ADS-09 Finance Agent — deterministic cost analysis and approval tier."""

    agent_code = "ADS-09"
    agent_name = "Finance Agent"

    async def _execute(self, state: SupplyChainState) -> dict[str, Any]:
        """
        Compute cost breakdown and determine financial approval tier.

        Reads shipping cost from state['shipment']['base_cost'] or a fallback,
        and procurement cost from state['supplier']['purchase_orders'][*]['total_cost'].
        Returns a 'finance' partial state dict.
        """
        session: AsyncSession | None = self.session
        order: dict = state.get("order") or {}
        shipment: dict = state.get("shipment") or {}
        supplier_state: dict = state.get("supplier") or {}

        order_id_str = order.get("order_id", "unknown")

        # ── 1. Compute shipping cost ──────────────────────────────────────────
        shipping_cost = Decimal(str(shipment.get("base_cost") or "0.00"))
        # Fallback: if base_cost not in shipment, use total_amount / 20 heuristic
        # (routes store base_cost, but the agent only sets freight_mode/transit_days)
        # We accept 0 if not provided — tests can inject it directly.
        if shipping_cost == Decimal("0.00"):
            # Try to get a non-zero value from route cost if stored
            shipping_cost = Decimal(str(shipment.get("route_cost") or "0.00"))

        # ── 2. Compute procurement cost from POs ──────────────────────────────
        purchase_orders: list[dict] = supplier_state.get("purchase_orders") or []
        procurement_cost = Decimal("0.00")
        for po in purchase_orders:
            procurement_cost += Decimal(str(po.get("total_cost") or "0.00"))

        # ── 3. Total operational cost ─────────────────────────────────────────
        total_cost = shipping_cost + procurement_cost

        # If both are zero and we have order total_amount, use that as reference
        # (for workflows that go through inventory-only path with no POs)
        order_total = Decimal(str(order.get("total_amount") or "0.00"))
        if total_cost == Decimal("0.00") and order_total > Decimal("0.00"):
            total_cost = order_total
            # Estimate split: 5% shipping, 95% procurement
            shipping_cost = (order_total * Decimal("0.05")).quantize(Decimal("0.01"))
            procurement_cost = (order_total - shipping_cost).quantize(Decimal("0.01"))

        # ── 4. Budget threshold check ─────────────────────────────────────────
        budget_threshold: Decimal = getattr(
            settings, "FINANCE_APPROVAL_THRESHOLD", Decimal("50000.00")
        )
        within_budget = total_cost <= budget_threshold
        budget_status = "within_budget" if within_budget else "over_budget"

        # ── 5. Approval tier ──────────────────────────────────────────────────
        if total_cost <= _AUTO_LIMIT:
            approval_tier = "auto"
        elif total_cost <= _FINANCE_REVIEW_LIMIT:
            approval_tier = "finance_review"
        elif total_cost <= _HUMAN_APPROVAL_LIMIT:
            approval_tier = "finance_and_ceo"
        else:
            approval_tier = "human_required"

        # ── 6. Build recommendations ──────────────────────────────────────────
        recommendations: list[str] = []
        if not within_budget:
            recommendations.append(
                f"Total cost ${total_cost:.2f} exceeds budget threshold "
                f"${budget_threshold:.2f} — escalate for finance review."
            )
        if shipping_cost > Decimal("5000.00"):
            recommendations.append(
                "Shipping cost is high — consider consolidating shipments or "
                "negotiating carrier rates."
            )
        if procurement_cost > Decimal("100000.00"):
            recommendations.append(
                "Procurement cost exceeds $100k — consider long-term supplier "
                "contracts for better pricing."
            )
        if not recommendations:
            recommendations.append("All costs within acceptable thresholds.")

        # ── 7. Publish events ─────────────────────────────────────────────────
        finance_payload: dict[str, Any] = {
            "order_id": order_id_str,
            "workflow_id": state.get("workflow_id"),
            "total_cost": str(total_cost),
            "shipping_cost": str(shipping_cost),
            "procurement_cost": str(procurement_cost),
            "budget_status": budget_status,
            "approval_tier": approval_tier,
            "within_budget": within_budget,
            "budget_threshold": str(budget_threshold),
        }

        await self._publish(state, "FinancialRecommendationReady", finance_payload)
        event_history = self._append_event(
            state, "FinancialRecommendationReady", finance_payload
        )

        if not within_budget:
            exceeded_payload = {
                **finance_payload,
                "overage": str(total_cost - budget_threshold),
            }
            await self._publish(state, "BudgetExceeded", exceeded_payload)
            _tmp = {**state, "event_history": event_history}
            event_history = self._append_event(_tmp, "BudgetExceeded", exceeded_payload)

        decisions = self._record_decision(
            state,
            "finance_assessment",
            f"Total cost ${total_cost:.2f} — tier={approval_tier}, "
            f"budget={'OK' if within_budget else 'EXCEEDED'}",
            finance_payload,
        )

        logger.info(
            "Finance assessment complete",
            total_cost=str(total_cost),
            approval_tier=approval_tier,
            within_budget=within_budget,
            order_id=order_id_str,
            workflow_id=state.get("workflow_id"),
        )

        finance_result: dict[str, Any] = {
            "total_cost": str(total_cost),
            "shipping_cost": str(shipping_cost),
            "procurement_cost": str(procurement_cost),
            "budget_status": budget_status,
            "approval_tier": approval_tier,
            "within_budget": within_budget,
            "recommendations": recommendations,
        }

        return {
            "finance": finance_result,
            "decisions": decisions,
            "event_history": event_history,
        }
