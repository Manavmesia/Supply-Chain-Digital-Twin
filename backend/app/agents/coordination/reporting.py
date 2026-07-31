"""
ADS-18 — Reporting Agent

Responsibilities:
  - Aggregate the entire workflow state into a structured Report
  - Create a Report record in DB (report_type="operational_kpi",
    generated_by_agent="ADS-18")
  - payload_summary contains:
      workflow_id, order_id, customer_name, total_amount, approval_tier,
      risk_score, risk_category, active_agents, event_count, decision_count,
      has_anomaly, completed_at
  - Publishes NO events (reporting only — no new workflows triggered)
  - Returns final workflow_status = "completed"
    (or keeps "failed" if CEO denied)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_agent import BaseAgent
from app.graph.state import SupplyChainState
from app.models.report import Report

logger = structlog.get_logger(__name__)


class ReportingAgent(BaseAgent):
    """ADS-18 Reporting Agent — workflow aggregation and KPI reporting."""

    agent_code = "ADS-18"
    agent_name = "Reporting Agent"

    async def _execute(self, state: SupplyChainState) -> dict[str, Any]:
        """
        Aggregate workflow state, persist a Report record, and return
        the final workflow_status.

        Does NOT publish any events.
        """
        session: AsyncSession | None = self.session

        # ── Extract key fields ────────────────────────────────────────────────
        workflow_id_str = state.get("workflow_id") or str(uuid.uuid4())
        order: dict = state.get("order") or {}
        customer: dict = state.get("customer") or {}
        finance: dict = state.get("finance") or {}
        risk: dict = state.get("risk") or {}
        forecast: dict = state.get("forecast") or {}
        executive_decision: dict = state.get("executive_decision") or {}

        order_id_str = order.get("order_id", "unknown")
        customer_name = (
            customer.get("name")
            or order.get("customer_name")
            or "Unknown"
        )
        total_amount = order.get("total_amount", "0.00")
        approval_tier = (
            finance.get("approval_tier")
            or executive_decision.get("approval_tier")
            or "unknown"
        )
        risk_score = risk.get("score", 0.0)
        risk_category = risk.get("category", "unknown")
        active_agents: list[str] = list(state.get("active_agents") or [])
        event_history: list[dict] = list(state.get("event_history") or [])
        decisions: list[dict] = list(state.get("decisions") or [])

        # Detect demand anomalies
        forecast_products: list[dict] = forecast.get("products") or []
        has_anomaly = any(p.get("is_anomaly") for p in forecast_products)

        # Final status: preserve "failed" if CEO denied, else "completed"
        current_status = state.get("workflow_status", "completed")
        final_status = current_status if current_status == "failed" else "completed"

        completed_at = datetime.now(tz=timezone.utc).isoformat()

        # ── Build payload_summary ─────────────────────────────────────────────
        payload_summary: dict[str, Any] = {
            "workflow_id": workflow_id_str,
            "order_id": order_id_str,
            "customer_name": customer_name,
            "total_amount": total_amount,
            "approval_tier": approval_tier,
            "risk_score": risk_score,
            "risk_category": risk_category,
            "active_agents": active_agents,
            "event_count": len(event_history),
            "decision_count": len(decisions),
            "has_anomaly": has_anomaly,
            "completed_at": completed_at,
            "final_status": final_status,
        }

        # ── Persist Report record ─────────────────────────────────────────────
        report_title = (
            f"Workflow KPI Report — Order {order_id_str[:8] if order_id_str != 'unknown' else 'N/A'} "
            f"— {completed_at[:10]}"
        )

        if session:
            try:
                report = Report(
                    report_id=uuid.uuid4(),
                    report_type="operational_kpi",
                    title=report_title,
                    status="ready",
                    workflow_id=(
                        uuid.UUID(workflow_id_str)
                        if workflow_id_str
                        else None
                    ),
                    correlation_id=(
                        uuid.UUID(state["correlation_id"])
                        if state.get("correlation_id")
                        else None
                    ),
                    generated_by_agent=self.agent_code,
                    payload_summary=payload_summary,
                )
                session.add(report)
                await session.flush()
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Failed to persist Report record",
                    error=str(exc),
                    workflow_id=workflow_id_str,
                )

        decisions_updated = self._record_decision(
            state,
            "report_generated",
            f"Operational KPI report generated — status={final_status}, "
            f"agents={len(active_agents)}, events={len(event_history)}",
            payload_summary,
        )

        logger.info(
            "Reporting complete",
            workflow_id=workflow_id_str,
            order_id=order_id_str,
            final_status=final_status,
            event_count=len(event_history),
            agent_count=len(active_agents),
        )

        return {
            "workflow_status": final_status,
            "decisions": decisions_updated,
        }
