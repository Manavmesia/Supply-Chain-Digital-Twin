"""
ADS-11 — Pricing Agent

Responsibilities (from AIS-11 & BACKLOG EP-25 US-107-111):
  - Read demand forecast to detect demand spikes / drops
  - Read finance state (gross_margin_pct) to detect margin pressure
  - Apply dynamic pricing rules to recommend a price adjustment
  - Write a PricingHistory record to DB
  - Publish PriceUpdated (when change recommended) or PriceStable (when optimal)

Pricing rules (all deterministic — no LLM):
  1. Demand spike (forecast > 2× baseline) AND high confidence → +5–15% increase
  2. Low gross margin (< 15%) → +8% suggested increase
  3. High gross margin (> 40%) → -5% promotional discount
  4. Otherwise → price is optimal, no change recommended
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_agent import BaseAgent
from app.graph.state import SupplyChainState
from app.models.pricing_history import PricingHistory

logger = structlog.get_logger(__name__)

# Pricing rule thresholds
_DEMAND_SPIKE_MULTIPLIER = 2.0       # forecast > 2× baseline = spike
_LOW_MARGIN_THRESHOLD = 15.0         # gross_margin_pct < 15% → price increase
_HIGH_MARGIN_THRESHOLD = 40.0        # gross_margin_pct > 40% → promotional discount
_SPIKE_INCREASE_MIN = 0.05           # +5% minimum on demand spike
_SPIKE_INCREASE_MAX = 0.15           # +15% maximum on demand spike
_LOW_MARGIN_INCREASE = 0.08          # +8% when margin is under pressure
_PROMO_DISCOUNT = 0.05               # −5% promotional discount on high margin


class PricingAgent(BaseAgent):
    agent_code = "ADS-11"
    agent_name = "Pricing Agent"

    async def _execute(self, state: SupplyChainState) -> dict[str, Any]:
        session: AsyncSession = self.session
        order: dict = state.get("order") or {}
        forecast_state: dict = state.get("forecast") or {}
        finance_state: dict = state.get("finance") or {}

        event_history = list(state.get("event_history") or [])
        decisions = list(state.get("decisions") or [])
        now = datetime.now(timezone.utc)

        items: list[dict] = order.get("items") or []
        if not items:
            decisions = self._record_decision(
                decisions, "pricing_skipped",
                "No order items to price — skipping pricing evaluation",
            )
            return {
                "pricing": {"status": "skipped", "reason": "no_items"},
                "decisions": decisions,
                "event_history": event_history,
            }

        gross_margin_pct = float(finance_state.get("gross_margin_pct", 25.0))
        pricing_results: list[dict[str, Any]] = []

        for item in items:
            product_id_str = str(item["product_id"])
            unit_price = Decimal(str(item.get("unit_price") or order.get("unit_price") or "0.00"))
            fc_data: dict = forecast_state.get(product_id_str) or {}

            forecast_qty = float(fc_data.get("forecast_quantity", 0))
            baseline_qty = float(fc_data.get("baseline_quantity", forecast_qty))
            confidence = float(fc_data.get("confidence", 0.70))

            # ── Apply pricing rules (LLM-driven if API key present) ───────────
            is_spike = (
                baseline_qty > 0
                and forecast_qty >= _DEMAND_SPIKE_MULTIPLIER * baseline_qty
                and confidence >= 0.70
            )

            from pydantic import BaseModel

            class PricingDecisionSchema(BaseModel):
                recommendation: str  # "increase", "discount", "stable"
                adjustment_pct: float
                reason: str

            def _fallback_pricing() -> PricingDecisionSchema:
                if is_spike:
                    spike_ratio = min(forecast_qty / max(baseline_qty, 1), 3.0)
                    adj = min(_SPIKE_INCREASE_MIN + (spike_ratio - 2.0) * 0.05, _SPIKE_INCREASE_MAX)
                    return PricingDecisionSchema(
                        recommendation="increase",
                        adjustment_pct=adj,
                        reason=f"Demand spike detected ({forecast_qty:.0f} vs baseline {baseline_qty:.0f}). Suggest {adj*100:.1f}% price increase.",
                    )
                elif gross_margin_pct < _LOW_MARGIN_THRESHOLD:
                    return PricingDecisionSchema(
                        recommendation="increase",
                        adjustment_pct=_LOW_MARGIN_INCREASE,
                        reason=f"Low gross margin ({gross_margin_pct:.1f}% < {_LOW_MARGIN_THRESHOLD}%). Suggest {_LOW_MARGIN_INCREASE*100:.0f}% price increase.",
                    )
                elif gross_margin_pct > _HIGH_MARGIN_THRESHOLD:
                    return PricingDecisionSchema(
                        recommendation="discount",
                        adjustment_pct=-_PROMO_DISCOUNT,
                        reason=f"High gross margin ({gross_margin_pct:.1f}% > {_HIGH_MARGIN_THRESHOLD}%). Suggest {_PROMO_DISCOUNT*100:.0f}% promotional discount.",
                    )
                else:
                    return PricingDecisionSchema(
                        recommendation="stable",
                        adjustment_pct=0.0,
                        reason="Price is optimal — no adjustment needed",
                    )

            pricing_context = {
                "product_id": product_id_str,
                "unit_price": str(unit_price),
                "baseline_qty": baseline_qty,
                "forecast_qty": forecast_qty,
                "confidence": confidence,
                "gross_margin_pct": gross_margin_pct,
                "is_spike": is_spike,
            }
            pricing_rules = [
                "If is_spike is True: recommendation must be 'increase' with adjustment_pct between 0.05 and 0.15.",
                "If gross_margin_pct < 15.0%: recommendation must be 'increase' with adjustment_pct = 0.08 (+8%).",
                "If gross_margin_pct > 35.0%: recommendation must be 'discount' with adjustment_pct = -0.05 (-5%).",
                "Otherwise: recommendation must be 'stable' with adjustment_pct = 0.0.",
                "Reason must explicitly detail the driver (spike, low margin, high margin, or optimal).",
            ]

            llm_price_dec, price_src = await self.decide_with_llm(
                decision_topic=f"Determine dynamic pricing for product {product_id_str}",
                context=pricing_context,
                rules=pricing_rules,
                schema=PricingDecisionSchema,
                fallback_callable=_fallback_pricing,
                state=state,
            )

            recommendation = llm_price_dec.recommendation
            adjustment_pct = llm_price_dec.adjustment_pct
            reason = llm_price_dec.reason

            # ── Calculate suggested price ─────────────────────────────────────
            if unit_price > Decimal("0"):
                suggested_price = unit_price * Decimal(str(1 + adjustment_pct))
                suggested_price = suggested_price.quantize(Decimal("0.01"))
            else:
                suggested_price = unit_price

            # ── Write PricingHistory DB record ────────────────────────────────
            pricing_record_id = uuid.uuid4()
            if session and unit_price > Decimal("0"):
                try:
                    record = PricingHistory(
                        price_id=pricing_record_id,
                        product_id=uuid.UUID(product_id_str),
                        previous_price=unit_price,
                        recommended_price=suggested_price,
                        approved_price=suggested_price if recommendation != "stable" else None,
                        trigger_type="demand_spike" if is_spike else ("cost_change" if adjustment_pct > 0 else "promotion"),
                        reasoning=reason,
                        created_at=now,
                    )
                    session.add(record)
                    await session.flush()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Could not persist pricing record", error=str(exc))

            # ── Build event payload ───────────────────────────────────────────
            pricing_payload = {
                "product_id": product_id_str,
                "current_price": str(unit_price),
                "suggested_price": str(suggested_price),
                "adjustment_pct": round(adjustment_pct * 100, 2),
                "recommendation": recommendation,
                "reason": reason,
                "gross_margin_pct": gross_margin_pct,
                "demand_spike_detected": is_spike,
            }

            if recommendation != "stable":
                await self._publish(state, "PriceUpdated", pricing_payload)
                event_history = self._append_event(event_history, "PriceUpdated", pricing_payload)
            else:
                await self._publish(state, "PriceStable", pricing_payload)
                event_history = self._append_event(event_history, "PriceStable", pricing_payload)

            pricing_results.append(pricing_payload)
            logger.info(
                "Pricing evaluation complete",
                product_id=product_id_str,
                recommendation=recommendation,
                adjustment_pct=round(adjustment_pct * 100, 2),
            )

        decisions = self._record_decision(
            decisions,
            "pricing_evaluated",
            f"Evaluated pricing for {len(pricing_results)} product(s). "
            f"Recommendations: {set(r['recommendation'] for r in pricing_results)}",
            {"product_count": len(pricing_results)},
            source=price_src if pricing_results else "rule_engine",
        )

        return {
            "pricing": {
                "status": "completed",
                "results": pricing_results,
                "gross_margin_pct": gross_margin_pct,
            },
            "decisions": decisions,
            "event_history": event_history,
        }
