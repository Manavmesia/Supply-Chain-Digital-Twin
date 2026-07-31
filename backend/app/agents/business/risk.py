"""
ADS-10 — Risk Management Agent

Responsibilities:
  - Score the overall workflow risk (0–100) from weighted signals:
      supplier_risk:  0 if supplier status == "selected", 30 if "unavailable" — weight 0.35
      inventory_risk: 0 if all items "reserved", 20 if any "out_of_stock"   — weight 0.25
      delivery_risk:  based on shipment.transit_days —
                        0 if ≤ 3, 10 if 4–7, 25 if > 7                      — weight 0.20
      financial_risk: 0 if within_budget, 20 if not                          — weight 0.20
  - Classify risk_category: "low" <30, "medium" 30–60, "high" >60
  - Create RiskAssessment record in DB (entity_type="order")
  - Publish RiskDetected if risk_score > 60
  - NO LLM calls
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_agent import BaseAgent
from app.graph.state import SupplyChainState
from app.models.risk_assessment import RiskAssessment

logger = structlog.get_logger(__name__)

# Weights (must sum to 1.0)
_W_SUPPLIER: float = 0.35
_W_INVENTORY: float = 0.25
_W_DELIVERY: float = 0.20
_W_FINANCIAL: float = 0.20


class RiskAgent(BaseAgent):
    """ADS-10 Risk Management Agent — composite risk scoring."""

    agent_code = "ADS-10"
    agent_name = "Risk Management Agent"

    async def _execute(self, state: SupplyChainState) -> dict[str, Any]:
        """
        Compute composite risk score and persist a RiskAssessment record.

        Reads signals from supplier, inventory, shipment, and finance state slices.
        Returns a 'risk' partial state dict.
        """
        session: AsyncSession | None = self.session
        order: dict = state.get("order") or {}
        supplier_state: dict = state.get("supplier") or {}
        inventory: dict = state.get("inventory") or {}
        shipment: dict = state.get("shipment") or {}
        finance: dict = state.get("finance") or {}

        order_id_str = order.get("order_id", "unknown")

        # ── 1. Compute raw signal scores ──────────────────────────────────────

        # Supplier risk
        supplier_status = supplier_state.get("status", "selected")
        supplier_raw = 30 if supplier_status == "unavailable" else 0

        # Inventory risk
        inventory_raw = 0
        for _pid, inv_data in inventory.items():
            if isinstance(inv_data, dict) and inv_data.get("status") == "out_of_stock":
                inventory_raw = 20
                break

        # Delivery risk
        transit_days = int(shipment.get("transit_days") or 0)
        if transit_days <= 3:
            delivery_raw = 0
        elif transit_days <= 7:
            delivery_raw = 10
        else:
            delivery_raw = 25

        # Financial risk
        within_budget: bool = finance.get("within_budget", True)
        financial_raw = 0 if within_budget else 20

        # ── 2. Composite score ────────────────────────────────────────────────
        risk_score: float = (
            supplier_raw * _W_SUPPLIER
            + inventory_raw * _W_INVENTORY
            + delivery_raw * _W_DELIVERY
            + financial_raw * _W_FINANCIAL
        )

        # ── 3. Classify ───────────────────────────────────────────────────────
        if risk_score < 30:
            risk_category = "low"
        elif risk_score <= 60:
            risk_category = "medium"
        else:
            risk_category = "high"

        # ── 4. Mitigation plan ────────────────────────────────────────────────
        mitigations: list[str] = []
        if supplier_raw > 0:
            mitigations.append("Identify alternative suppliers for emergency procurement.")
        if inventory_raw > 0:
            mitigations.append("Trigger reorder workflow to replenish out-of-stock items.")
        if delivery_raw >= 10:
            mitigations.append("Notify customer of extended lead time; consider expedited shipping.")
        if financial_raw > 0:
            mitigations.append("Escalate to finance team for budget reallocation approval.")
        if not mitigations:
            mitigations.append("No immediate mitigation required — continue standard workflow.")

        mitigation_plan = " ".join(mitigations)

        # ── 5. Persist RiskAssessment record ──────────────────────────────────
        if session and order_id_str and order_id_str != "unknown":
            try:
                risk_record = RiskAssessment(
                    risk_id=uuid.uuid4(),
                    entity_type="order",
                    entity_id=uuid.UUID(order_id_str),
                    risk_score=Decimal(str(round(risk_score, 2))),
                    risk_category=risk_category,
                    description=(
                        f"Composite risk score {risk_score:.1f} "
                        f"(supplier={supplier_raw}, inventory={inventory_raw}, "
                        f"delivery={delivery_raw}, financial={financial_raw})"
                    ),
                    mitigation_plan=mitigation_plan,
                    mitigation_status="detected",
                    assessed_by_agent=self.agent_code,
                    workflow_id=(
                        uuid.UUID(state["workflow_id"])
                        if state.get("workflow_id")
                        else None
                    ),
                )
                session.add(risk_record)
                await session.flush()
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Failed to persist RiskAssessment",
                    error=str(exc),
                    order_id=order_id_str,
                )

        # ── 6. Publish events ─────────────────────────────────────────────────
        risk_payload: dict[str, Any] = {
            "order_id": order_id_str,
            "workflow_id": state.get("workflow_id"),
            "risk_score": risk_score,
            "risk_category": risk_category,
            "signals": {
                "supplier_risk": supplier_raw,
                "inventory_risk": inventory_raw,
                "delivery_risk": delivery_raw,
                "financial_risk": financial_raw,
            },
        }

        event_history = state.get("event_history") or []

        if risk_score > 60:
            await self._publish(state, "RiskDetected", risk_payload)
            event_history = self._append_event(state, "RiskDetected", risk_payload)

        decisions = self._record_decision(
            state,
            "risk_assessment",
            f"Risk score {risk_score:.1f} — category={risk_category}",
            risk_payload,
        )

        logger.info(
            "Risk assessment complete",
            risk_score=risk_score,
            risk_category=risk_category,
            order_id=order_id_str,
            workflow_id=state.get("workflow_id"),
        )

        signals_dict: dict[str, Any] = {
            "supplier_risk": supplier_raw,
            "inventory_risk": inventory_raw,
            "delivery_risk": delivery_raw,
            "financial_risk": financial_raw,
        }

        result: dict[str, Any] = {
            "risk": {
                "score": risk_score,
                "category": risk_category,
                "signals": signals_dict,
                "mitigation_plan": mitigation_plan,
                "assessed_by": self.agent_code,
            },
            "decisions": decisions,
        }
        if risk_score > 60:
            result["event_history"] = event_history
        return result
