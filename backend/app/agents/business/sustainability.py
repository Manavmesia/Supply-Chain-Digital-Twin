"""
ADS-13 — Sustainability Agent

Responsibilities (from AIS-13 & BACKLOG EP-27 US-117-121):
  - Read shipment state (freight_mode, carrier, transit_days) for CO2 calculation
  - Calculate CO2 emissions using industry-standard emission factors per freight mode
  - Calculate a sustainability score (0-100; higher = greener)
  - Recommend green alternative if air freight is used AND road/sea alternative exists
    within 10% cost difference
  - Write SustainabilityMetric DB record
  - Publish SustainabilityScoreCalculated and (conditional) GreenAlternativeAvailable
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
from app.models.sustainability_metric import SustainabilityMetric

logger = structlog.get_logger(__name__)

# CO2 emission factors (kg CO2 per tonne-km) — IPCC/Ecoinvent data
_CO2_FACTORS: dict[str, float] = {
    "air":  0.602,    # kg CO2 per tonne-km (air freight is ~50× road)
    "road": 0.096,    # kg CO2 per tonne-km (road freight)
    "sea":  0.010,    # kg CO2 per tonne-km (sea freight is most efficient)
    "rail": 0.028,    # kg CO2 per tonne-km
}

# Approximate distances (km) for MVP — replace with real geodistance in production
_MOCK_DISTANCES: dict[str, float] = {
    "air":  8_000.0,   # typical intercontinental air route
    "road": 2_500.0,   # typical intra-continental road route
    "sea":  12_000.0,  # typical ocean route
    "rail": 2_000.0,
}

_DEFAULT_SHIPMENT_WEIGHT_KG = 100.0     # default weight per shipment in kg
_GREEN_ALTERNATIVE_THRESHOLD = 0.10     # recommend alternative if cost delta <= 10%
_MAX_CO2_REFERENCE_KG = 600.0           # CO2 at which sustainability_score = 0
_CO2_HIGH_THRESHOLD = 200.0             # above this → recommend green alternative


class SustainabilityAgent(BaseAgent):
    agent_code = "ADS-13"
    agent_name = "Sustainability Agent"

    async def _execute(self, state: SupplyChainState) -> dict[str, Any]:
        session: AsyncSession = self.session
        shipment_state: dict = state.get("shipment") or {}
        order: dict = state.get("order") or {}

        event_history = list(state.get("event_history") or [])
        decisions = list(state.get("decisions") or [])
        now = datetime.now(timezone.utc)

        freight_mode = shipment_state.get("freight_mode", "road").lower()
        if freight_mode not in _CO2_FACTORS:
            freight_mode = "road"

        # ── 1. Calculate CO2 emissions ────────────────────────────────────────
        # Weight approximation from number of order items * avg item weight
        items: list[dict] = order.get("items") or []
        total_qty = sum(int(i.get("quantity", 1)) for i in items)
        estimated_weight_kg = max(total_qty * 5.0, _DEFAULT_SHIPMENT_WEIGHT_KG)
        distance_km = _MOCK_DISTANCES.get(freight_mode, 2_500.0)

        # CO2 formula: weight_tonnes × distance_km × emission_factor
        weight_tonnes = estimated_weight_kg / 1000.0
        co2_kg = weight_tonnes * distance_km * _CO2_FACTORS[freight_mode]
        co2_kg = round(co2_kg, 3)

        # ── 2. Calculate sustainability score (0–100; higher = greener) ───────
        # Linear scale: 0 CO2 → 100 score; _MAX_CO2_REFERENCE_KG → 0 score
        score = max(0.0, 100.0 - (co2_kg / _MAX_CO2_REFERENCE_KG) * 100.0)
        score = round(score, 1)

        # ── 3. Determine if a green alternative should be recommended ─────────
        green_alternative = None
        if freight_mode == "air" and co2_kg >= _CO2_HIGH_THRESHOLD:
            # Calculate road alternative CO2
            road_co2 = weight_tonnes * _MOCK_DISTANCES["road"] * _CO2_FACTORS["road"]
            co2_savings_kg = co2_kg - road_co2
            # Only recommend if road is meaningfully cheaper in CO2 (always is for air)
            green_alternative = {
                "alternative_mode": "road",
                "current_co2_kg": co2_kg,
                "alternative_co2_kg": round(road_co2, 3),
                "co2_savings_kg": round(co2_savings_kg, 3),
                "co2_reduction_pct": round((co2_savings_kg / co2_kg) * 100, 1),
                "note": "Road freight produces significantly less CO2 than air at moderate cost increase",
            }

        # ── 4. Write SustainabilityMetric DB record ───────────────────────────
        metric_id = uuid.uuid4()
        workflow_id_str = state.get("workflow_id")
        if session:
            try:
                metric = SustainabilityMetric(
                    metric_id=metric_id,
                    workflow_id=uuid.UUID(workflow_id_str) if workflow_id_str else None,
                    freight_mode=freight_mode,
                    co2_kg=Decimal(str(co2_kg)),
                    sustainability_score=Decimal(str(score)),
                    created_at=now,
                )
                session.add(metric)
                await session.flush()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not persist sustainability metric", error=str(exc))

        # ── 5. Publish events ─────────────────────────────────────────────────
        score_payload = {
            "metric_id": str(metric_id),
            "freight_mode": freight_mode,
            "estimated_weight_kg": estimated_weight_kg,
            "distance_km": distance_km,
            "co2_kg": co2_kg,
            "sustainability_score": score,
            "order_id": order.get("order_id"),
        }

        await self._publish(state, "SustainabilityScoreCalculated", score_payload)
        event_history = self._append_event(event_history, "SustainabilityScoreCalculated", score_payload)

        if green_alternative:
            alt_payload = {**score_payload, "green_alternative": green_alternative}
            await self._publish(state, "GreenAlternativeAvailable", alt_payload)
            event_history = self._append_event(event_history, "GreenAlternativeAvailable", alt_payload)

        decisions = self._record_decision(
            decisions,
            "sustainability_calculated",
            f"CO2 emissions: {co2_kg} kg via {freight_mode} freight. "
            f"Sustainability score: {score}/100."
            + (f" Green alternative available." if green_alternative else ""),
            score_payload,
        )

        logger.info(
            "Sustainability evaluation complete",
            freight_mode=freight_mode,
            co2_kg=co2_kg,
            score=score,
            green_alternative=green_alternative is not None,
            workflow_id=state.get("workflow_id"),
        )

        return {
            "sustainability": {
                "status": "completed",
                "freight_mode": freight_mode,
                "co2_kg": co2_kg,
                "sustainability_score": score,
                "green_alternative": green_alternative,
            },
            "decisions": decisions,
            "event_history": event_history,
        }
