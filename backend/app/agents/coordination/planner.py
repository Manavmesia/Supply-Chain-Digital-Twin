"""
ADS-15 — Planner Agent

Responsibilities (from AIS-15 & BACKLOG EP-29 US-127-131):
  - Act as multi-agent coordinator: synthesise outputs from Forecast, Inventory,
    Supplier, Quality, and Risk agents into an actionable execution plan
  - If quality failed → add 'remanufacture' action to plan
  - If risk score >= 70 → add 'risk_mitigation' step with specific mitigations
  - If procurement urgency is high → elevate priority of supplier steps in plan
  - If demand spike detected → recommend inventory buffer increase
  - Publish ProductionPlanned and ExecutionPlanReady events
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

from app.agents.base_agent import BaseAgent
from app.graph.state import SupplyChainState

logger = structlog.get_logger(__name__)

# Risk threshold for mitigation step
_RISK_MITIGATION_THRESHOLD = 70.0
_HIGH_DEMAND_SPIKE_CONFIDENCE = 0.70


class PlannerAgent(BaseAgent):
    agent_code = "ADS-15"
    agent_name = "Planner Agent"

    async def _execute(self, state: SupplyChainState) -> dict[str, Any]:
        quality_state: dict = state.get("quality") or {}
        risk_state: dict = state.get("risk") or {}
        forecast_state: dict = state.get("forecast") or {}
        procurement_state: dict = state.get("procurement") or {}
        supplier_state: dict = state.get("supplier") or {}
        order: dict = state.get("order") or {}

        event_history = list(state.get("event_history") or [])
        decisions = list(state.get("decisions") or [])

        plan_actions: list[dict[str, Any]] = []
        priority_queue: list[str] = []
        estimated_completion_days = 3   # base estimate

        # ── 1. Quality Failure → Remanufacture ───────────────────────────────
        quality_failed = not quality_state.get("all_passed", True)
        if quality_failed:
            failed_count = quality_state.get("failed_count", 1)
            plan_actions.append({
                "action": "remanufacture",
                "priority": "critical",
                "reason": f"{failed_count} product batch(es) failed QA inspection",
                "estimated_days": 3,
                "agent": "ADS-07",
            })
            priority_queue.insert(0, "manufacturing")
            estimated_completion_days += 3

        # ── 2. Risk Mitigation Steps ──────────────────────────────────────────
        risk_score = float(risk_state.get("score", 0.0))
        risk_factors = risk_state.get("factors") or []

        if risk_score >= _RISK_MITIGATION_THRESHOLD:
            mitigations: list[str] = []
            for factor in risk_factors:
                f = factor.get("factor", "")
                if "supplier" in f:
                    mitigations.append("Identify backup supplier before order confirmation")
                elif "transit" in f or "carrier" in f:
                    mitigations.append("Pre-book alternative carrier as contingency")
                elif "forecast" in f:
                    mitigations.append("Increase safety stock buffer by 20%")
                elif "margin" in f:
                    mitigations.append("Request finance team cost reduction review")

            plan_actions.append({
                "action": "risk_mitigation",
                "priority": "high" if risk_score < 90.0 else "critical",
                "reason": f"Risk score {risk_score} requires active mitigation",
                "mitigations": mitigations,
                "estimated_days": 1,
                "agent": "ADS-10",
            })
            priority_queue.append("risk")
            estimated_completion_days += 1

        # ── 3. Procurement Urgency → Elevate Supplier Steps ──────────────────
        reorder_urgency = procurement_state.get("reorder_urgency", "normal")
        if reorder_urgency == "high":
            plan_actions.append({
                "action": "expedite_procurement",
                "priority": "high",
                "reason": "Reorder urgency is high — expedite supplier engagement",
                "estimated_days": 2,
                "agent": "ADS-05",
            })
            priority_queue.append("supplier")
            estimated_completion_days += 2

        # ── 4. Demand Spike → Inventory Buffer Recommendation ────────────────
        spike_detected = any(
            fc_data.get("demand_spike_detected", False)
            for fc_data in forecast_state.values()
            if isinstance(fc_data, dict)
        )
        if spike_detected:
            plan_actions.append({
                "action": "increase_inventory_buffer",
                "priority": "medium",
                "reason": "Demand spike detected — pre-stock additional units",
                "buffer_increase_pct": 25,
                "estimated_days": 5,
                "agent": "ADS-03",
            })

        # ── 5. Standard fulfillment plan (always present) ────────────────────
        plan_actions.append({
            "action": "standard_fulfillment",
            "priority": "standard",
            "reason": "Proceed with normal order fulfillment pipeline",
            "estimated_days": estimated_completion_days,
            "agent": "ADS-01",
        })

        # ── 6. Publish events ─────────────────────────────────────────────────
        production_payload = {
            "order_id": order.get("order_id"),
            "priority": order.get("priority", "standard"),
            "action_count": len(plan_actions),
            "remanufacture_required": quality_failed,
        }

        plan_payload = {
            "plan_id": str(uuid.uuid4()),
            "order_id": order.get("order_id"),
            "actions": plan_actions,
            "priority_queue": priority_queue,
            "estimated_completion_days": estimated_completion_days,
            "risk_score": risk_score,
            "quality_status": quality_state.get("status", "not_evaluated"),
        }

        await self._publish(state, "ProductionPlanned", production_payload)
        await self._publish(state, "ExecutionPlanReady", plan_payload)
        event_history = self._append_event(event_history, "ProductionPlanned", production_payload)
        event_history = self._append_event(event_history, "ExecutionPlanReady", plan_payload)

        decisions = self._record_decision(
            decisions,
            "execution_plan_ready",
            f"Execution plan created with {len(plan_actions)} action(s). "
            f"Est. completion: {estimated_completion_days} days. "
            f"Quality failed: {quality_failed}. Risk: {risk_score}",
            plan_payload,
        )

        logger.info(
            "Execution plan ready",
            actions=len(plan_actions),
            quality_failed=quality_failed,
            risk_score=risk_score,
            estimated_days=estimated_completion_days,
            workflow_id=state.get("workflow_id"),
        )

        return {
            "planning": {
                "status": "completed",
                "actions": plan_actions,
                "priority_queue": priority_queue,
                "estimated_completion_days": estimated_completion_days,
                "remanufacture_required": quality_failed,
            },
            "decisions": decisions,
            "event_history": event_history,
        }
