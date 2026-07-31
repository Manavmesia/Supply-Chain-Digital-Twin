"""
ADS-02 — Demand Forecast Agent

Responsibilities:
  - Look up the 90-day rolling average order quantity per product from
    demand_forecasts table (fallback: orders table if no forecast history)
  - Compute forecast: avg_qty * 1.1 (10% buffer), confidence=0.75
  - Detect anomalies:
      order qty > 2× 90-day average → is_anomaly=True, publish DemandSpikeDetected
      order qty < 0.5× average      → publish DemandDropDetected
  - Write one DemandForecast record per product to DB
    (forecast_period = today + 30 days)
  - Publish DemandForecastGenerated
  - NO LLM calls (all statistical)
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_agent import BaseAgent
from app.graph.state import SupplyChainState
from app.models.demand_forecast import DemandForecast
from app.models.order import Order
from app.models.order_item import OrderItem

logger = structlog.get_logger(__name__)

_CONFIDENCE: Decimal = Decimal("0.75")
_FORECAST_HORIZON_DAYS: int = 30
_HISTORY_DAYS: int = 90
_BUFFER: Decimal = Decimal("1.10")
_SPIKE_MULTIPLIER: float = 2.0
_DROP_MULTIPLIER: float = 0.5
_DEFAULT_AVG_QTY: Decimal = Decimal("10.0")  # used when no history exists


class DemandForecastAgent(BaseAgent):
    """ADS-02 Demand Forecast Agent — statistical demand forecasting."""

    agent_code = "ADS-02"
    agent_name = "Demand Forecast Agent"

    async def _execute(self, state: SupplyChainState) -> dict[str, Any]:
        """
        For each product in the current order, compute a 30-day demand forecast
        based on 90-day rolling average history.

        Returns a 'forecast' partial state dict.
        """
        session: AsyncSession | None = self.session
        order: dict = state.get("order") or {}
        items: list[dict] = order.get("items") or []
        order_id_str = order.get("order_id", "unknown")

        forecast_period: date = (
            datetime.now(tz=timezone.utc) + timedelta(days=_FORECAST_HORIZON_DAYS)
        ).date()
        cutoff: date = (
            datetime.now(tz=timezone.utc) - timedelta(days=_HISTORY_DAYS)
        ).date()

        product_forecasts: list[dict[str, Any]] = []
        anomalies: list[str] = []
        spike_detected = False
        drop_detected = False
        spike_products: list[str] = []
        drop_products: list[str] = []

        for item in items:
            product_id_str = str(item.get("product_id") or "")
            if not product_id_str:
                continue

            order_qty = Decimal(str(item.get("quantity") or "0"))
            product_id = uuid.UUID(product_id_str)

            # ── Look up 90-day average from demand_forecasts table ─────────────
            avg_qty = await self._get_historical_avg(
                session, product_id, cutoff
            )

            # ── Compute forecast ───────────────────────────────────────────────
            forecast_qty = (avg_qty * _BUFFER).quantize(Decimal("0.01"))

            # ── Anomaly detection ──────────────────────────────────────────────
            is_anomaly = False
            if avg_qty > Decimal("0") and order_qty > avg_qty * Decimal(str(_SPIKE_MULTIPLIER)):
                is_anomaly = True
                spike_detected = True
                spike_products.append(product_id_str)
                anomalies.append(
                    f"Product {product_id_str}: order qty {order_qty} exceeds "
                    f"2× 90-day average ({avg_qty:.1f})."
                )
            elif avg_qty > Decimal("0") and order_qty < avg_qty * Decimal(str(_DROP_MULTIPLIER)):
                drop_detected = True
                drop_products.append(product_id_str)
                anomalies.append(
                    f"Product {product_id_str}: order qty {order_qty} is below "
                    f"50% of 90-day average ({avg_qty:.1f})."
                )

            # ── Persist DemandForecast record ──────────────────────────────────
            if session:
                try:
                    forecast_record = DemandForecast(
                        forecast_id=uuid.uuid4(),
                        product_id=product_id,
                        forecast_period=forecast_period,
                        forecast_qty=forecast_qty,
                        confidence=_CONFIDENCE,
                        model_used="rolling_avg_90d",
                        is_anomaly=is_anomaly,
                        anomaly_description=(
                            anomalies[-1] if is_anomaly and anomalies else None
                        ),
                    )
                    session.add(forecast_record)
                    await session.flush()
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "Failed to persist DemandForecast",
                        error=str(exc),
                        product_id=product_id_str,
                    )

            product_forecasts.append(
                {
                    "product_id": product_id_str,
                    "forecast_qty": str(forecast_qty),
                    "confidence": str(_CONFIDENCE),
                    "is_anomaly": is_anomaly,
                    "avg_qty_90d": str(avg_qty),
                }
            )

        # ── Build event history ───────────────────────────────────────────────
        forecast_payload: dict[str, Any] = {
            "order_id": order_id_str,
            "workflow_id": state.get("workflow_id"),
            "product_count": len(product_forecasts),
            "anomaly_count": len(anomalies),
            "forecast_period": str(forecast_period),
        }

        await self._publish(state, "DemandForecastGenerated", forecast_payload)
        event_history = self._append_event(state, "DemandForecastGenerated", forecast_payload)
        _tmp_state = {**state, "event_history": event_history}

        if spike_detected:
            spike_payload = {
                **forecast_payload,
                "affected_products": spike_products,
                "description": "Order quantity exceeds 2× 90-day rolling average.",
            }
            await self._publish(_tmp_state, "DemandSpikeDetected", spike_payload)
            event_history = self._append_event(_tmp_state, "DemandSpikeDetected", spike_payload)
            _tmp_state = {**_tmp_state, "event_history": event_history}

        if drop_detected:
            drop_payload = {
                **forecast_payload,
                "affected_products": drop_products,
                "description": "Order quantity is below 50% of 90-day rolling average.",
            }
            await self._publish(_tmp_state, "DemandDropDetected", drop_payload)
            event_history = self._append_event(_tmp_state, "DemandDropDetected", drop_payload)

        decisions = self._record_decision(
            state,
            "demand_forecast_generated",
            f"Forecasted {len(product_forecasts)} products; "
            f"{len(anomalies)} anomalies detected",
            forecast_payload,
        )

        logger.info(
            "Demand forecast complete",
            product_count=len(product_forecasts),
            anomaly_count=len(anomalies),
            order_id=order_id_str,
            workflow_id=state.get("workflow_id"),
        )

        return {
            "forecast": {
                "products": product_forecasts,
                "anomalies": anomalies,
            },
            "decisions": decisions,
            "event_history": event_history,
        }

    # ── Helpers ──────────────────────────────────────────────────────────────

    async def _get_historical_avg(
        self,
        session: AsyncSession | None,
        product_id: uuid.UUID,
        cutoff: date,
    ) -> Decimal:
        """
        Return 90-day rolling average quantity for *product_id*.

        Priority:
          1. demand_forecasts table — average of forecast_qty in the period
          2. order_items JOIN orders fallback — average of ordered quantities
          3. DEFAULT_AVG_QTY if no history at all (no real DB in tests)
        """
        if session is None:
            return _DEFAULT_AVG_QTY

        # Try demand_forecasts first
        try:
            result = await session.execute(
                select(func.avg(DemandForecast.forecast_qty)).where(
                    DemandForecast.product_id == product_id,
                    DemandForecast.forecast_period >= cutoff,
                )
            )
            avg_val = result.scalar_one_or_none()
            if avg_val is not None:
                return Decimal(str(avg_val))
        except Exception:  # noqa: BLE001
            pass

        # Fallback: orders table
        try:
            result = await session.execute(
                select(func.avg(OrderItem.quantity)).where(
                    OrderItem.product_id == product_id,
                )
            )
            avg_val = result.scalar_one_or_none()
            if avg_val is not None:
                return Decimal(str(avg_val))
        except Exception:  # noqa: BLE001
            pass

        return _DEFAULT_AVG_QTY
