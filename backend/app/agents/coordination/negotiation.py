"""
ADS-16 — Negotiation Agent

Responsibilities (from AIS-16 & BACKLOG EP-30 US-132-136):
  - Read supplier state (selected supplier, PO, contract_price, reliability_score)
  - Read procurement state (recommended_qty, reorder_urgency, strategy)
  - Apply negotiation strategy based on business rules:
      1. Volume discount: order_qty > minimum_order_qty × 3 → negotiate 5–10% discount
      2. Penalty clause: reliability_score < 85 → propose SLA penalty terms
      3. Urgency override: reorder_urgency == 'high' → skip negotiation (speed > cost)
      4. Bulk strategy: procurement strategy == 'bulk' → negotiate volume pricing
  - Publish NegotiationCompleted and ContractTermsProposed (when terms changed)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import structlog

from app.agents.base_agent import BaseAgent
from app.graph.state import SupplyChainState

logger = structlog.get_logger(__name__)

# Negotiation thresholds
_VOLUME_DISCOUNT_MULTIPLIER = 3      # qty > min_qty × 3 → eligible for volume discount
_VOLUME_DISCOUNT_MIN = 0.05          # minimum 5% volume discount
_VOLUME_DISCOUNT_MAX = 0.10          # maximum 10% volume discount
_LOW_RELIABILITY_THRESHOLD = 85.0    # reliability_score < 85 → penalty clause
_PENALTY_RATE_PCT = 2.0              # penalty: 2% of PO value per SLA breach day


class NegotiationAgent(BaseAgent):
    agent_code = "ADS-16"
    agent_name = "Negotiation Agent"

    async def _execute(self, state: SupplyChainState) -> dict[str, Any]:
        supplier_state: dict = state.get("supplier") or {}
        procurement_state: dict = state.get("procurement") or {}
        order: dict = state.get("order") or {}

        event_history = list(state.get("event_history") or [])
        decisions = list(state.get("decisions") or [])

        # ── 1. Check urgency override — skip negotiation if urgent ────────────
        reorder_urgency = procurement_state.get("reorder_urgency", "normal")
        if reorder_urgency == "high":
            decisions = self._record_decision(
                decisions,
                "negotiation_skipped_urgent",
                "Reorder urgency is HIGH — skipping negotiation to prioritise delivery speed",
            )
            event_payload = {
                "order_id": order.get("order_id"),
                "strategy": "urgent_skip",
                "outcome": "skipped",
                "reason": "High urgency — speed over price",
            }
            await self._publish(state, "NegotiationCompleted", event_payload)
            event_history = self._append_event(event_history, "NegotiationCompleted", event_payload)
            return {
                "negotiation": {
                    "status": "skipped",
                    "strategy": "urgent_skip",
                    "reason": "High urgency — speed prioritised over price negotiation",
                },
                "decisions": decisions,
                "event_history": event_history,
            }

        # ── 2. Load supplier data from state ──────────────────────────────────
        pos: list[dict] = supplier_state.get("purchase_orders") or []
        if not pos:
            decisions = self._record_decision(
                decisions,
                "negotiation_skipped_no_po",
                "No purchase orders in state — supplier not engaged, skipping negotiation",
            )
            return {
                "negotiation": {"status": "skipped", "reason": "no_purchase_orders"},
                "decisions": decisions,
                "event_history": event_history,
            }

        po = pos[0]
        unit_cost = Decimal(str(po.get("unit_cost", "0.00")))
        order_qty = int(po.get("quantity", 1))
        supplier_name = supplier_state.get("purchase_orders", [{}])[0].get(
            "supplier_id", "Unknown Supplier"
        )

        # Get reliability from the SupplierUpdated event payload if available
        # (stored as part of supplier_state or looked up from event history)
        supplier_updated_events = [
            e for e in (state.get("event_history") or [])
            if e.get("event_type") == "SupplierUpdated"
        ]
        reliability_score = 90.0  # safe default
        min_order_qty = 1
        if supplier_updated_events:
            latest = supplier_updated_events[-1].get("payload", {})
            reliability_score = float(latest.get("reliability_score", 90.0))
            min_order_qty = int(latest.get("minimum_order_qty", 1))

        # ── 3. Apply negotiation rules (LLM-driven if API key present) ────────
        from pydantic import BaseModel

        class NegotiationDecisionSchema(BaseModel):
            strategy: str
            discount_pct: float
            final_unit_cost: str
            terms_proposed: list[str]
            rationale: str

        procurement_strategy = procurement_state.get("strategy", "standard")

        def _fallback_negotiation() -> NegotiationDecisionSchema:
            strat = "standard"
            disc = 0.0
            terms = []
            fp = unit_cost

            if order_qty >= min_order_qty * _VOLUME_DISCOUNT_MULTIPLIER:
                v_ratio = order_qty / max(min_order_qty, 1)
                disc = min(_VOLUME_DISCOUNT_MIN + (v_ratio - 3) * 0.01, _VOLUME_DISCOUNT_MAX)
                fp = (unit_cost * Decimal(str(1 - disc))).quantize(Decimal("0.01"))
                strat = "volume_discount"
                terms.append(f"Volume discount of {disc*100:.1f}% applied for {order_qty} units")
            elif procurement_strategy == "bulk" and disc == 0.0:
                disc = _VOLUME_DISCOUNT_MIN
                fp = (unit_cost * Decimal(str(1 - disc))).quantize(Decimal("0.01"))
                strat = "bulk_pricing"
                terms.append(f"Bulk procurement discount of {disc*100:.1f}% for strategic reorder")

            if reliability_score < _LOW_RELIABILITY_THRESHOLD:
                p_clause = (
                    f"SLA penalty clause: {_PENALTY_RATE_PCT}% of PO value per calendar day "
                    f"of delivery delay beyond agreed lead time. Applied due to supplier reliability score of {reliability_score:.1f} < 85"
                )
                terms.append(p_clause)
                strat = f"{strat}_with_penalty" if strat != "standard" else "penalty_clause"

            return NegotiationDecisionSchema(
                strategy=strat,
                discount_pct=disc,
                final_unit_cost=str(fp),
                terms_proposed=terms,
                rationale=f"Negotiation complete: strategy={strat}, discount={round(disc*100, 1)}%",
            )

        neg_context = {
            "order_id": order.get("order_id"),
            "order_qty": order_qty,
            "min_order_qty": min_order_qty,
            "original_unit_cost": str(unit_cost),
            "procurement_strategy": procurement_strategy,
            "supplier_reliability_score": reliability_score,
            "reorder_urgency": reorder_urgency,
        }
        neg_rules = [
            f"If order_qty >= min_order_qty * {_VOLUME_DISCOUNT_MULTIPLIER}: volume discount between 5% and 12% is applied.",
            "If procurement_strategy == 'bulk' and discount is 0: 5% strategic reorder discount is applied.",
            f"If supplier_reliability_score < {_LOW_RELIABILITY_THRESHOLD}: an SLA delay penalty clause ({_PENALTY_RATE_PCT}%/day) must strictly be added.",
            "final_unit_cost must equal original_unit_cost * (1 - discount_pct) rounded to 2 decimals.",
            "Rationale must detail the discounts and contractual terms negotiated.",
        ]

        llm_neg_dec, neg_src = await self.decide_with_llm(
            decision_topic="Negotiate procurement pricing and contractual SLA terms",
            context=neg_context,
            rules=neg_rules,
            schema=NegotiationDecisionSchema,
            fallback_callable=_fallback_negotiation,
            state=state,
        )

        strategy = llm_neg_dec.strategy
        discount_pct = round(float(llm_neg_dec.discount_pct), 4)
        if discount_pct > 0.0:
            final_price = (unit_cost * (Decimal("1.0000") - Decimal(str(discount_pct)))).quantize(Decimal("0.01"))
        else:
            final_price = unit_cost.quantize(Decimal("0.01"))
        terms_proposed = llm_neg_dec.terms_proposed

        # ── 4. Publish events ─────────────────────────────────────────────────
        negotiation_payload = {
            "order_id": order.get("order_id"),
            "strategy": strategy,
            "original_unit_cost": f"{unit_cost:.2f}",
            "final_unit_cost": f"{final_price:.2f}",
            "discount_pct": round(discount_pct * 100, 2),
            "terms_proposed": terms_proposed,
            "outcome": "agreed" if terms_proposed else "no_change",
            "reliability_score": reliability_score,
        }

        await self._publish(state, "NegotiationCompleted", negotiation_payload)
        event_history = self._append_event(event_history, "NegotiationCompleted", negotiation_payload)

        if terms_proposed:
            await self._publish(state, "ContractTermsProposed", negotiation_payload)
            event_history = self._append_event(event_history, "ContractTermsProposed", negotiation_payload)

        decisions = self._record_decision(
            decisions,
            "negotiation_completed",
            llm_neg_dec.rationale,
            negotiation_payload,
            source=neg_src,
        )

        logger.info(
            "Negotiation complete",
            strategy=strategy,
            discount_pct=round(discount_pct * 100, 2),
            terms_count=len(terms_proposed),
            workflow_id=state.get("workflow_id"),
        )

        return {
            "negotiation": {
                "status": "completed",
                "strategy": strategy,
                "final_unit_cost": str(final_price),
                "discount_pct": round(discount_pct * 100, 2),
                "terms_proposed": terms_proposed,
            },
            "decisions": decisions,
            "event_history": event_history,
        }
