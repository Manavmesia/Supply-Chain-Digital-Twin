"""
ADS-12 — Procurement Strategy Agent

Responsibilities (from AIS-12 & BACKLOG EP-26 US-112-116):
  - Analyse current supplier state and demand forecast to define reorder strategy
  - Check contracts table for contracts expiring within 30 days
  - Publish ContractExpiring per near-expiry contract (Celery would do this in prod;
    this agent handles it inline for synchronous workflow execution)
  - Evaluate lead time risk and recommend bulk vs standard reorder quantities
  - Publish ProcurementPlanCreated
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
from app.models.contract import Contract

logger = structlog.get_logger(__name__)

# Thresholds
_CONTRACT_EXPIRY_WARNING_DAYS = 30   # flag contracts expiring within 30 days
_BULK_REORDER_MULTIPLIER = 1.5       # if forecast > 1.5× reorder_point → bulk reorder
_HIGH_LEAD_TIME_DAYS = 14            # lead time > 14 days = high lead time risk
_STANDARD_REORDER_QTY = 100         # default reorder quantity when no forecast data


class ProcurementStrategyAgent(BaseAgent):
    agent_code = "ADS-12"
    agent_name = "Procurement Strategy Agent"

    async def _execute(self, state: SupplyChainState) -> dict[str, Any]:
        session: AsyncSession = self.session
        supplier_state: dict = state.get("supplier") or {}
        forecast_state: dict = state.get("forecast") or {}
        order: dict = state.get("order") or {}

        event_history = list(state.get("event_history") or [])
        decisions = list(state.get("decisions") or [])
        now = datetime.now(timezone.utc)
        contract_alerts: list[dict] = []

        # ── 1. Contract Expiry Check ──────────────────────────────────────────
        expiry_cutoff = now + timedelta(days=_CONTRACT_EXPIRY_WARNING_DAYS)
        if session:
            try:
                res = await session.execute(
                    select(Contract).where(
                        Contract.status == "active",
                        Contract.end_date <= expiry_cutoff.date(),
                    )
                )
                expiring = res.scalars().all()
                for contract in expiring:
                    days_remaining = (contract.end_date - now.date()).days
                    alert_payload = {
                        "contract_id": str(contract.contract_id),
                        "supplier_id": str(contract.supplier_id),
                        "end_date": str(contract.end_date),
                        "days_remaining": days_remaining,
                        "urgency": "critical" if days_remaining <= 7 else "high",
                    }
                    await self._publish(state, "ContractExpiring", alert_payload)
                    event_history = self._append_event(event_history, "ContractExpiring", alert_payload)
                    contract_alerts.append(alert_payload)
                    logger.warning(
                        "Contract expiring soon",
                        contract_id=str(contract.contract_id),
                        days_remaining=days_remaining,
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not check contracts", error=str(exc))

        # ── 2. Reorder Strategy Evaluation ───────────────────────────────────
        items: list[dict] = order.get("items") or []
        strategy = "standard"
        reorder_urgency = "normal"
        recommended_qty = _STANDARD_REORDER_QTY
        lead_time_risk = False

        # Read lead time from selected supplier
        pos = supplier_state.get("purchase_orders") or []
        if pos:
            # Extract lead time from first PO's supplier
            po_data = pos[0]
            supplier_lead_time = int(po_data.get("lead_time_days", 7))
            if supplier_lead_time > _HIGH_LEAD_TIME_DAYS:
                lead_time_risk = True
                reorder_urgency = "high"

        # Evaluate demand forecast for reorder quantity recommendation
        for item in items:
            product_id_str = str(item["product_id"])
            ordered_qty = int(item.get("quantity", 1))
            fc_data: dict = forecast_state.get(product_id_str) or {}
            forecast_qty = float(fc_data.get("forecast_quantity", 0))

            if forecast_qty > 0 and forecast_qty >= ordered_qty * _BULK_REORDER_MULTIPLIER:
                strategy = "bulk"
                recommended_qty = max(recommended_qty, int(forecast_qty * 1.2))  # 20% buffer
                reorder_urgency = "high"

        # ── 3. Build and publish procurement plan (LLM-driven if API key present) ─
        from pydantic import BaseModel

        class ProcurementDecisionSchema(BaseModel):
            strategy: str
            reorder_urgency: str
            recommended_qty: int
            rationale: str

        def _fallback_procurement() -> ProcurementDecisionSchema:
            return ProcurementDecisionSchema(
                strategy=strategy,
                reorder_urgency=reorder_urgency,
                recommended_qty=recommended_qty,
                rationale=f"Procurement strategy: {strategy}, urgency: {reorder_urgency}, contract alerts: {len(contract_alerts)}",
            )

        proc_context = {
            "order_id": order.get("order_id"),
            "strategy": strategy,
            "reorder_urgency": reorder_urgency,
            "recommended_qty": recommended_qty,
            "lead_time_risk": lead_time_risk,
            "contract_alerts": contract_alerts,
        }
        proc_rules = [
            "If forecast_qty >= ordered_qty * 3, strategy must be 'bulk' with a 20% safety buffer.",
            "If supplier lead time > 14 days, lead_time_risk is True and reorder_urgency must be 'high'.",
            "Rationale must detail the replenishment strategy and contract risk status.",
        ]

        llm_proc_dec, proc_src = await self.decide_with_llm(
            decision_topic="Determine strategic procurement posture and bulk reorder volume",
            context=proc_context,
            rules=proc_rules,
            schema=ProcurementDecisionSchema,
            fallback_callable=_fallback_procurement,
        )

        strategy = llm_proc_dec.strategy
        reorder_urgency = llm_proc_dec.reorder_urgency
        recommended_qty = llm_proc_dec.recommended_qty

        plan_payload = {
            "order_id": order.get("order_id"),
            "strategy": strategy,
            "recommended_qty": recommended_qty,
            "reorder_urgency": reorder_urgency,
            "lead_time_risk": lead_time_risk,
            "contract_alerts_count": len(contract_alerts),
            "contract_alerts": contract_alerts,
        }

        await self._publish(state, "ProcurementPlanCreated", plan_payload)
        event_history = self._append_event(event_history, "ProcurementPlanCreated", plan_payload)

        decisions = self._record_decision(
            decisions,
            "procurement_strategy_set",
            llm_proc_dec.rationale or f"Procurement strategy: {strategy}, urgency: {reorder_urgency}, contract alerts: {len(contract_alerts)}",
            plan_payload,
            source=proc_src,
        )

        logger.info(
            "Procurement strategy determined",
            strategy=strategy,
            urgency=reorder_urgency,
            contract_alerts=len(contract_alerts),
            workflow_id=state.get("workflow_id"),
        )

        return {
            "procurement": {
                "status": "completed",
                "strategy": strategy,
                "recommended_qty": recommended_qty,
                "reorder_urgency": reorder_urgency,
                "lead_time_risk": lead_time_risk,
                "contract_alerts": contract_alerts,
            },
            "decisions": decisions,
            "event_history": event_history,
        }
