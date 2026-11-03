"""
ADS-18 — Reporting Agent

Responsibilities (from AIS-18 spec):
  - Execute post-CEO decision
  - Consolidate workflow execution metrics (order, shipment, finance, risk, decisions)
  - Create immutable Report record using ReportRepository
  - Publish ReportGenerated and DashboardUpdated events
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from app.agents.base_agent import BaseAgent
from app.graph.state import SupplyChainState
from app.repositories.report import ReportRepository

logger = structlog.get_logger(__name__)


class ReportingAgent(BaseAgent):
    agent_code = "ADS-18"
    agent_name = "Reporting & Analytics Agent"

    async def _execute(self, state: SupplyChainState) -> dict[str, Any]:
        session = self.session
        order: dict = state.get("order") or {}
        shipment: dict = state.get("shipment") or {}
        finance: dict = state.get("finance") or {}
        risk: dict = state.get("risk") or {}
        ceo: dict = state.get("executive_decision") or {}
        decisions: list = state.get("decisions") or []

        order_id_str = order.get("order_id", "N/A")
        workflow_id_str = state.get("workflow_id", str(uuid.uuid4()))

        # Safely parse correlation & workflow UUIDs
        corr_id_raw = state.get("correlation_id")
        corr_id_uuid = None
        if corr_id_raw:
            try:
                corr_id_uuid = uuid.UUID(str(corr_id_raw))
            except (ValueError, TypeError):
                corr_id_uuid = None

        wf_id_uuid = None
        if workflow_id_str:
            try:
                wf_id_uuid = uuid.UUID(str(workflow_id_str))
            except (ValueError, TypeError):
                wf_id_uuid = None

        # ── 1. Assemble immutable KPI snapshot (JSON serializable) ───────────
        payload_summary = {
            "workflow_id": str(workflow_id_str),
            "order_id": str(order_id_str),
            "order_status": str(order.get("status")) if order.get("status") else None,
            "customer_id": str(order.get("customer_id")) if order.get("customer_id") else None,
            "total_revenue": str(order.get("total_amount")) if order.get("total_amount") is not None else None,
            "total_cost": str(finance.get("total_cost")) if finance.get("total_cost") is not None else None,
            "gross_margin_pct": float(finance.get("gross_margin_pct", 0.0)),
            "risk_score": float(risk.get("score", 0.0)),
            "risk_level": str(risk.get("level")) if risk.get("level") else "Low",
            "carrier": str(shipment.get("carrier")) if shipment.get("carrier") else None,
            "tracking_id": str(shipment.get("tracking_id")) if shipment.get("tracking_id") else None,
            "eta": str(shipment.get("eta")) if shipment.get("eta") else None,
            "ceo_approved": bool(ceo.get("approved")),
            "approval_tier": str(ceo.get("approval_tier")) if ceo.get("approval_tier") else None,
            "active_agent_count": len(state.get("active_agents") or []),
            "total_decisions": len(decisions),
        }

        # ── 2. Create immutable Report DB record (LLM-synthesized when active)
        from pydantic import BaseModel

        class ReportDecisionSchema(BaseModel):
            executive_narrative: str
            audit_verdict: str
            rationale: str

        def _fallback_report() -> ReportDecisionSchema:
            return ReportDecisionSchema(
                executive_narrative=f"Order #{str(order_id_str)[:8]} completed with status '{order.get('status')}'. Margin: {finance.get('gross_margin_pct')}%, Risk: {risk.get('level')}.",
                audit_verdict="compliant",
                rationale=f"Generated executive report for order {order_id_str}",
            )

        llm_rep_dec, rep_src = await self.decide_with_llm(
            decision_topic="Synthesize executive audit report and narrative KPI summary",
            context=payload_summary,
            rules=[
                "Synthesize a clear, professional executive narrative summarizing fulfillment, revenue, margin health, risk, and delivery timeline.",
                "Verify audit compliance against company supply chain criteria.",
                "Audit verdict must be 'compliant' if CEO approved and no critical errors.",
            ],
            schema=ReportDecisionSchema,
            fallback_callable=_fallback_report,
            state=state,
        )

        payload_summary["executive_narrative"] = llm_rep_dec.executive_narrative
        payload_summary["audit_verdict"] = llm_rep_dec.audit_verdict
        payload_summary["decision_source"] = rep_src

        report_id = uuid.uuid4()
        if session:
            try:
                repo = ReportRepository(session)
                await repo.create({
                    "report_id": report_id,
                    "report_type": "executive_summary",
                    "title": f"Order Fulfillment Summary — Order #{str(order_id_str)[:8]}",
                    "status": "ready",
                    "workflow_id": wf_id_uuid,
                    "correlation_id": corr_id_uuid,
                    "generated_by_agent": self.agent_code,
                    "payload_summary": payload_summary,
                })
                await session.flush()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not persist report DB record", error=str(exc))

        event_history = list(state.get("event_history") or [])
        decisions_list = list(decisions)

        report_event_payload = {
            "report_id": str(report_id),
            "report_type": "executive_summary",
            "workflow_id": workflow_id_str,
            "order_id": order_id_str,
        }

        # ── 3. Publish events ─────────────────────────────────────────────────
        await self._publish(state, "ReportGenerated", report_event_payload)
        await self._publish(state, "DashboardUpdated", report_event_payload)
        event_history = self._append_event(event_history, "ReportGenerated", report_event_payload)
        event_history = self._append_event(event_history, "DashboardUpdated", report_event_payload)

        decisions_list = self._record_decision(
            decisions_list,
            "report_generated",
            llm_rep_dec.rationale or f"Generated executive report {report_id} for order {order_id_str}",
            report_event_payload,
            source=rep_src,
        )

        logger.info(
            "Reporting complete",
            report_id=str(report_id),
            workflow_id=workflow_id_str,
        )

        return {
            "reports": {
                "latest_report_id": str(report_id),
                "summary": payload_summary,
            },
            "decisions": decisions_list,
            "event_history": event_history,
        }
