"""
ADS-02 — Demand Forecast Agent

Responsibilities (from AIS-02 spec):
  - Predict future product demand based on historical sales & active promotions
  - Calculate 30-day baseline forecast + seasonality/promotional adjustments
  - Calculate confidence score (0.00 to 1.00)
  - Detect demand anomalies:
      forecast > 2× 12-month average → publish DemandSpikeDetected
      forecast < 0.5× 12-month average → publish DemandDropDetected
  - Always publish DemandForecastGenerated event
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_agent import BaseAgent
from app.graph.state import SupplyChainState
from app.models.order_item import OrderItem
from app.models.promotion import Promotion
from app.models.promotion_product import PromotionProduct

logger = structlog.get_logger(__name__)


class DemandForecastAgent(BaseAgent):
    agent_code = "ADS-02"
    agent_name = "Demand Forecast Agent"

    async def _execute(self, state: SupplyChainState) -> dict[str, Any]:
        session: AsyncSession = self.session
        order: dict = state.get("order") or {}
        items: list[dict] = order.get("items") or []

        forecast_details: dict[str, Any] = {}
        event_history = list(state.get("event_history") or [])
        decisions = list(state.get("decisions") or [])

        for item in items:
            product_id_str = str(item["product_id"])
            product_id = uuid.UUID(product_id_str)
            order_qty = int(item.get("quantity", 1))

            # ── 1. Load historical order item volume for product ──────────────
            hist_qty = 0
            if session:
                res = await session.execute(
                    select(func.coalesce(func.sum(OrderItem.quantity), 0))
                    .where(OrderItem.product_id == product_id)
                )
                hist_qty = int(res.scalar() or 0)

            # Baseline 30-day forecast: average monthly sales + current order
            baseline_forecast = max(hist_qty, order_qty)

            # ── 2. Check active promotions for product ────────────────────────
            promo_multiplier = 1.0
            if session:
                promo_res = await session.execute(
                    select(Promotion)
                    .join(PromotionProduct, PromotionProduct.promotion_id == Promotion.promotion_id)
                    .where(
                        PromotionProduct.product_id == product_id,
                        Promotion.status == "active",
                    )
                )
                active_promos = promo_res.scalars().all()
                if active_promos:
                    # Apply promo boost based on discount percent
                    for p in active_promos:
                        disc = float(p.discount_percent or 10.0)
                        promo_multiplier += (disc / 100.0)

            adjusted_forecast = int(baseline_forecast * promo_multiplier)

            # ── 3. Confidence score ───────────────────────────────────────────
            # High historical data volume = higher confidence score
            confidence = min(0.95, 0.70 + (hist_qty / 1000.0))
            if promo_multiplier > 1.0:
                confidence = max(0.60, confidence - 0.05)  # Slightly higher variance during promotions

            confidence = round(confidence, 2)

            # ── 4. Anomaly detection ──────────────────────────────────────────
            avg_12m = max(hist_qty / 12.0, 1.0)
            is_spike = adjusted_forecast >= (2 * avg_12m)
            is_drop = adjusted_forecast <= (0.5 * avg_12m) and hist_qty > 0

            forecast_payload = {
                "product_id": product_id_str,
                "forecast_quantity": adjusted_forecast,
                "confidence": confidence,
                "baseline_quantity": float(hist_qty) if hist_qty > 0 else float(avg_12m),
                "promo_multiplier": promo_multiplier,
            }

            # Publish main event
            await self._publish(state, "DemandForecastGenerated", forecast_payload)
            event_history = self._append_event(event_history, "DemandForecastGenerated", forecast_payload)

            if is_spike:
                spike_payload = {**forecast_payload, "anomaly": "spike", "avg_12m": avg_12m}
                await self._publish(state, "DemandSpikeDetected", spike_payload)
                event_history = self._append_event(event_history, "DemandSpikeDetected", spike_payload)
                logger.warning("Demand spike detected", product_id=product_id_str, forecast=adjusted_forecast)

            elif is_drop:
                drop_payload = {**forecast_payload, "anomaly": "drop", "avg_12m": avg_12m}
                await self._publish(state, "DemandDropDetected", drop_payload)
                event_history = self._append_event(event_history, "DemandDropDetected", drop_payload)

            forecast_details[product_id_str] = forecast_payload

        from pydantic import BaseModel

        class ForecastDecisionSchema(BaseModel):
            rationale: str

        def _fallback_forecast() -> ForecastDecisionSchema:
            return ForecastDecisionSchema(
                rationale=f"Generated statistical demand forecast for {len(items)} products"
            )

        llm_fc_dec, fc_src = await self.decide_with_llm(
            decision_topic="Synthesize 30-day product demand forecast and detect demand spikes",
            context={"product_count": len(items), "details": forecast_details},
            rules=[
                "Assess forecast confidence based on historical moving averages and active promotions.",
                "Flag demand spikes when adjusted forecast >= 2x the 12-month average.",
                "Rationale must summarize forecasted volumes and any anomalies detected.",
            ],
            schema=ForecastDecisionSchema,
            fallback_callable=_fallback_forecast,
        )

        decisions = self._record_decision(
            decisions,
            "demand_forecast_generated",
            llm_fc_dec.rationale or f"Generated forecast for {len(items)} products",
            {"product_count": len(items)},
            source=fc_src,
        )

        logger.info(
            "Demand forecast generated",
            products=len(items),
            workflow_id=state.get("workflow_id"),
        )

        return {
            "forecast": forecast_details,
            "decisions": decisions,
            "event_history": event_history,
        }
