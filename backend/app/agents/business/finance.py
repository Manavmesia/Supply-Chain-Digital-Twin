"""
ADS-09 — Finance Agent

Responsibilities (from AIS-09 spec):
  - Calculate total operational costs: product procurement + warehousing + shipping
  - Validate against corporate budget constraints
  - Calculate estimated gross margin % = (revenue - total_cost) / revenue * 100
  - Emit FinancialApprovalGranted (margin >= 15%), CostOptimizationSuggested (margin < 15%), or BudgetExceeded
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

import structlog

from app.agents.base_agent import BaseAgent
from app.graph.state import SupplyChainState

logger = structlog.get_logger(__name__)


class FinanceAgent(BaseAgent):
    agent_code = "ADS-09"
    agent_name = "Finance Agent"

    async def _execute(self, state: SupplyChainState) -> dict[str, Any]:
        order: dict = state.get("order") or {}
        supplier_state: dict = state.get("supplier") or {}
        shipment_state: dict = state.get("shipment") or {}

        order_id_str = order.get("order_id")
        total_revenue = Decimal(str(order.get("total_amount", "0.00")))

        # ── 1. Calculate operational costs ────────────────────────────────────
        procurement_cost = Decimal("0.00")
        pos = supplier_state.get("purchase_orders") or []
        for po in pos:
            unit_cost = Decimal(str(po.get("unit_cost", "0.00")))
            qty = Decimal(str(po.get("quantity", 0)))
            procurement_cost += (unit_cost * qty).quantize(Decimal("0.01"))

        # Estimated shipping & handling cost
        shipping_cost = Decimal("150.00") if shipment_state else Decimal("0.00")
        if shipment_state.get("freight_mode") == "air":
            shipping_cost = Decimal("650.00")

        # Warehouse handling overhead per item
        item_count = sum(int(i.get("quantity", 1)) for i in (order.get("items") or []))
        warehouse_cost = (Decimal(str(item_count)) * Decimal("5.00")).quantize(Decimal("0.01"))

        # Default COGS fallback if no purchase orders (in-stock items)
        if procurement_cost == Decimal("0.00") and total_revenue > Decimal("0.00"):
            procurement_cost = (total_revenue * Decimal("0.65")).quantize(Decimal("0.01"))  # 65% standard COGS

        procurement_cost = procurement_cost.quantize(Decimal("0.01"))
        shipping_cost = shipping_cost.quantize(Decimal("0.01"))
        warehouse_cost = warehouse_cost.quantize(Decimal("0.01"))
        total_cost = (procurement_cost + shipping_cost + warehouse_cost).quantize(Decimal("0.01"))

        # ── 2. Gross Margin % ─────────────────────────────────────────────────
        if total_revenue > Decimal("0.00"):
            gross_margin_amount = (total_revenue - total_cost).quantize(Decimal("0.01"))
            gross_margin_pct = round(float((gross_margin_amount / total_revenue) * Decimal("100.0")), 2)
        else:
            gross_margin_amount = Decimal("0.00")
            gross_margin_pct = 0.0

        # ── 3. Evaluate budget and profitability (LLM-driven if API key present) ──
        from pydantic import BaseModel

        class FinanceDecisionSchema(BaseModel):
            is_approved: bool
            budget_exceeded: bool
            action: str
            rationale: str

        budget_exceeded_default = total_cost > Decimal("1000000.00")
        is_approved_default = gross_margin_pct >= 15.0 and not budget_exceeded_default

        finance_context = {
            "order_id": order_id_str,
            "revenue": str(total_revenue),
            "total_cost": str(total_cost),
            "gross_margin_pct": gross_margin_pct,
            "budget_cap": "1000000.00",
            "minimum_margin_hurdle_pct": 15.0,
        }
        finance_rules = [
            "If total_cost > 1000000.00, budget_exceeded must be True, is_approved must be False, action must be 'budget_exceeded'.",
            "If gross_margin_pct >= 15.0 and not budget_exceeded, is_approved must be True, action must be 'financial_approval_granted'.",
            "If gross_margin_pct < 15.0 and not budget_exceeded, is_approved must be False, action must be 'cost_optimization_suggested'.",
            "Rationale must detail the exact margin %, revenue, and cost amounts.",
        ]

        def _fallback_finance() -> FinanceDecisionSchema:
            if budget_exceeded_default:
                act = "budget_exceeded"
                rat = f"Order cost ${total_cost} exceeds single-order budget limit of $1,000,000"
            elif is_approved_default:
                act = "financial_approval_granted"
                rat = f"Financial approval granted with gross margin of {gross_margin_pct}%"
            else:
                act = "cost_optimization_suggested"
                rat = f"Low gross margin {gross_margin_pct}% (< 15%) — cost optimization suggested"
            return FinanceDecisionSchema(
                is_approved=is_approved_default,
                budget_exceeded=budget_exceeded_default,
                action=act,
                rationale=rat,
            )

        llm_fin_decision, fin_src = await self.decide_with_llm(
            decision_topic="Evaluate financial profitability and single-order budget compliance",
            context=finance_context,
            rules=finance_rules,
            schema=FinanceDecisionSchema,
            fallback_callable=_fallback_finance,
            state=state,
        )

        budget_exceeded = llm_fin_decision.budget_exceeded
        is_approved = llm_fin_decision.is_approved

        event_history = list(state.get("event_history") or [])
        decisions = list(state.get("decisions") or [])

        finance_payload = {
            "order_id": order_id_str,
            "revenue": f"{total_revenue:.2f}",
            "total_cost": f"{total_cost:.2f}",
            "procurement_cost": f"{procurement_cost:.2f}",
            "shipping_cost": f"{shipping_cost:.2f}",
            "warehouse_cost": f"{warehouse_cost:.2f}",
            "gross_margin_amount": f"{gross_margin_amount:.2f}",
            "gross_margin_pct": gross_margin_pct,
            "budget_approved": not budget_exceeded,
            "financial_approval": is_approved,
        }

        if budget_exceeded:
            await self._publish(state, "BudgetExceeded", finance_payload)
            event_history = self._append_event(event_history, "BudgetExceeded", finance_payload)
            decisions = self._record_decision(
                decisions, "budget_exceeded",
                llm_fin_decision.rationale or f"Order cost ${total_cost} exceeds single-order budget limit of $1,000,000",
                finance_payload,
                source=fin_src,
            )
            logger.warning("Budget exceeded", cost=str(total_cost))

        elif is_approved:
            await self._publish(state, "FinancialApprovalGranted", finance_payload)
            event_history = self._append_event(event_history, "FinancialApprovalGranted", finance_payload)
            decisions = self._record_decision(
                decisions, "financial_approval_granted",
                llm_fin_decision.rationale or f"Financial approval granted with gross margin of {gross_margin_pct}%",
                finance_payload,
                source=fin_src,
            )
        else:
            await self._publish(state, "CostOptimizationSuggested", finance_payload)
            event_history = self._append_event(event_history, "CostOptimizationSuggested", finance_payload)
            decisions = self._record_decision(
                decisions, "cost_optimization_suggested",
                llm_fin_decision.rationale or f"Gross margin {gross_margin_pct}% is below 15% threshold — cost optimization suggested",
                finance_payload,
                source=fin_src,
            )

        logger.info(
            "Finance evaluation complete",
            margin_pct=gross_margin_pct,
            total_cost=str(total_cost),
            approved=is_approved,
            workflow_id=state.get("workflow_id"),
        )

        return {
            "finance": finance_payload,
            "decisions": decisions,
            "event_history": event_history,
        }
