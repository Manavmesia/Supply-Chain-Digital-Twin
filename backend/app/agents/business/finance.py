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
            procurement_cost += unit_cost * qty

        # Estimated shipping & handling cost
        shipping_cost = Decimal("150.00") if shipment_state else Decimal("0.00")
        if shipment_state.get("freight_mode") == "air":
            shipping_cost = Decimal("650.00")

        # Warehouse handling overhead per item
        item_count = sum(int(i.get("quantity", 1)) for i in (order.get("items") or []))
        warehouse_cost = Decimal(str(item_count * 5.00))

        total_cost = procurement_cost + shipping_cost + warehouse_cost

        # Default COGS fallback if no purchase orders (in-stock items)
        if procurement_cost == Decimal("0.00") and total_revenue > Decimal("0.00"):
            cogs_estimate = total_revenue * Decimal("0.65")  # Assume 65% COGS
            total_cost += cogs_estimate

        # ── 2. Gross Margin % ─────────────────────────────────────────────────
        if total_revenue > Decimal("0.00"):
            gross_margin_amount = total_revenue - total_cost
            gross_margin_pct = float((gross_margin_amount / total_revenue) * Decimal("100.0"))
        else:
            gross_margin_pct = 0.0

        gross_margin_pct = round(gross_margin_pct, 2)

        # ── 3. Evaluate budget and profitability ──────────────────────────────
        budget_exceeded = total_cost > Decimal("1000000.00")  # Single-order budget cap $1M
        is_approved = gross_margin_pct >= 15.0 and not budget_exceeded

        event_history = list(state.get("event_history") or [])
        decisions = list(state.get("decisions") or [])

        finance_payload = {
            "order_id": order_id_str,
            "revenue": str(total_revenue),
            "total_cost": str(total_cost),
            "procurement_cost": str(procurement_cost),
            "shipping_cost": str(shipping_cost),
            "warehouse_cost": str(warehouse_cost),
            "gross_margin_pct": gross_margin_pct,
            "budget_approved": not budget_exceeded,
            "financial_approval": is_approved,
        }

        if budget_exceeded:
            await self._publish(state, "BudgetExceeded", finance_payload)
            event_history = self._append_event(event_history, "BudgetExceeded", finance_payload)
            decisions = self._record_decision(
                decisions, "budget_exceeded",
                f"Order cost ${total_cost} exceeds single-order budget limit of $1,000,000",
                finance_payload,
            )
            logger.warning("Budget exceeded", cost=str(total_cost))

        elif is_approved:
            await self._publish(state, "FinancialApprovalGranted", finance_payload)
            event_history = self._append_event(event_history, "FinancialApprovalGranted", finance_payload)
            decisions = self._record_decision(
                decisions, "financial_approval_granted",
                f"Financial approval granted with gross margin of {gross_margin_pct}%",
                finance_payload,
            )
        else:
            await self._publish(state, "CostOptimizationSuggested", finance_payload)
            event_history = self._append_event(event_history, "CostOptimizationSuggested", finance_payload)
            decisions = self._record_decision(
                decisions, "cost_optimization_suggested",
                f"Low gross margin ({gross_margin_pct}%) — cost optimization suggested",
                finance_payload,
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
