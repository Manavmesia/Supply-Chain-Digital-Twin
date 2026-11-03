"""
ADS-10 — Risk Management Agent

Responsibilities (from AIS-10 spec):
  - Calculate enterprise composite risk score (0 to 100)
  - Risk levels: 0-39 (Low), 40-69 (Medium), 70-89 (High), 90-100 (Critical)
  - Risk factors evaluated:
      1. Supplier reliability / status
      2. Carrier transit / mode risk
      3. Forecast confidence score
      4. Gross margin % risk
  - Publish RiskDetected (score >= 70) and ExecutiveEscalation (score >= 90)
"""

from __future__ import annotations

from typing import Any

import structlog

from app.agents.base_agent import BaseAgent
from app.graph.state import SupplyChainState

logger = structlog.get_logger(__name__)


class RiskAgent(BaseAgent):
    agent_code = "ADS-10"
    agent_name = "Risk Management Agent"

    async def _execute(self, state: SupplyChainState) -> dict[str, Any]:
        order: dict = state.get("order") or {}
        supplier_state: dict = state.get("supplier") or {}
        shipment_state: dict = state.get("shipment") or {}
        finance_state: dict = state.get("finance") or {}
        forecast_state: dict = state.get("forecast") or {}

        risk_score = 10.0  # Base low risk
        risk_factors: list[dict[str, Any]] = []

        # ── 1. Evaluate Supplier Risk ─────────────────────────────────────────
        if supplier_state.get("status") == "unavailable":
            risk_score += 40.0
            risk_factors.append({"factor": "supplier_unavailable", "points": 40.0})
        elif supplier_state.get("purchase_orders"):
            po = supplier_state["purchase_orders"][0]
            rel = float(po.get("reliability_score", 90.0))
            if rel < 85.0:
                pts = (85.0 - rel) * 2.0
                risk_score += pts
                risk_factors.append({"factor": "low_supplier_reliability", "points": pts})

        # ── 2. Evaluate Carrier & Transit Risk ────────────────────────────────
        if shipment_state.get("freight_mode") == "air":
            risk_score += 15.0  # Air transport has flight delay / customs risk
            risk_factors.append({"factor": "air_freight_delay_risk", "points": 15.0})

        transit_days = int(shipment_state.get("transit_days", 3))
        if transit_days > 10:
            risk_score += 20.0
            risk_factors.append({"factor": "long_transit_time", "points": 20.0})

        # ── 3. Evaluate Forecast Confidence Risk ──────────────────────────────
        for _, fc in forecast_state.items():
            if isinstance(fc, dict):
                conf = float(fc.get("confidence", 0.85))
                if conf < 0.70:
                    pts = (0.70 - conf) * 50.0
                    risk_score += pts
                    risk_factors.append({"factor": "low_forecast_confidence", "points": pts})

        # ── 4. Evaluate Financial Margin Risk ─────────────────────────────────
        margin_pct = float(finance_state.get("gross_margin_pct", 25.0))
        if margin_pct < 10.0:
            risk_score += 30.0
            risk_factors.append({"factor": "low_margin_exposure", "points": 30.0})

        risk_score_calc = min(100.0, round(risk_score, 1))

        # ── LLM Risk Synthesis & Level Classification ─────────────────────────
        from pydantic import BaseModel

        class RiskDecisionSchema(BaseModel):
            risk_score: float
            risk_level: str
            mitigation_recommended: bool
            action: str
            rationale: str

        def _fallback_risk_level(score: float) -> tuple[str, str, str]:
            if score >= 90.0:
                return "Critical", "executive_escalation", f"Critical risk score {score} requires executive escalation to CEO Agent"
            elif score >= 70.0:
                return "High", "risk_detected", f"High risk score {score} (High) — mitigation recommended"
            elif score >= 40.0:
                return "Medium", "risk_evaluated", f"Risk evaluated at {score} (Medium)"
            else:
                return "Low", "risk_evaluated", f"Risk evaluated at {score} (Low)"

        def _fallback_risk() -> RiskDecisionSchema:
            lvl, act, rat = _fallback_risk_level(risk_score_calc)
            return RiskDecisionSchema(
                risk_score=risk_score_calc,
                risk_level=lvl,
                mitigation_recommended=risk_score_calc >= 70.0,
                action=act,
                rationale=rat,
            )

        risk_context = {
            "order_id": order.get("order_id"),
            "calculated_score": risk_score_calc,
            "freight_mode": shipment_state.get("freight_mode"),
            "transit_days": transit_days,
            "gross_margin_pct": margin_pct,
            "risk_factors": risk_factors,
        }
        risk_rules = [
            "Score >= 90.0 must be categorized as 'Critical' with action 'executive_escalation'.",
            "Score 70.0 to 89.9 must be categorized as 'High' with action 'risk_detected' and mitigation_recommended=True.",
            "Score 40.0 to 69.9 must be categorized as 'Medium' with action 'risk_evaluated'.",
            "Score < 40.0 must be categorized as 'Low' with action 'risk_evaluated'.",
            "Rationale must detail the primary contributing risk factors and recommended mitigation posture.",
        ]

        llm_risk_dec, risk_src = await self.decide_with_llm(
            decision_topic="Synthesize composite supply chain risk and determine escalation needs",
            context=risk_context,
            rules=risk_rules,
            schema=RiskDecisionSchema,
            fallback_callable=_fallback_risk,
            state=state,
        )

        risk_score = llm_risk_dec.risk_score
        risk_level = llm_risk_dec.risk_level

        event_history = list(state.get("event_history") or [])
        decisions = list(state.get("decisions") or [])

        risk_payload = {
            "order_id": order.get("order_id"),
            "score": risk_score,
            "level": risk_level,
            "factors": risk_factors,
            "mitigation_recommended": llm_risk_dec.mitigation_recommended,
        }

        if risk_score >= 90.0:
            await self._publish(state, "ExecutiveEscalation", risk_payload)
            event_history = self._append_event(event_history, "ExecutiveEscalation", risk_payload)
            decisions = self._record_decision(
                decisions, "executive_escalation",
                llm_risk_dec.rationale,
                risk_payload,
                source=risk_src,
            )
            logger.warning("Critical risk detected — escalating to CEO", score=risk_score)

        elif risk_score >= 70.0:
            await self._publish(state, "RiskDetected", risk_payload)
            event_history = self._append_event(event_history, "RiskDetected", risk_payload)
            decisions = self._record_decision(
                decisions, "risk_detected",
                llm_risk_dec.rationale,
                risk_payload,
                source=risk_src,
            )

        else:
            decisions = self._record_decision(
                decisions, "risk_evaluated",
                llm_risk_dec.rationale,
                risk_payload,
                source=risk_src,
            )

        logger.info(
            "Risk evaluation complete",
            score=risk_score,
            level=risk_level,
            workflow_id=state.get("workflow_id"),
        )

        return {
            "risk": risk_payload,
            "decisions": decisions,
            "event_history": event_history,
        }
