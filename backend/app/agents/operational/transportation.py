"""
ADS-06 — Transportation Agent

Responsibilities (from AIS-06 spec):
  - Select carrier based on order priority:
      standard  → cheapest available carrier with matching freight mode
      high      → fastest carrier (minimum transit days)
      critical  → air freight mandatory
  - Find optimal route (origin warehouse → customer region)
  - Create Shipment record with tracking ID and ETA
  - Update order status to in_transit
  - Publish ShipmentCreated + ShipmentDispatched events
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_agent import BaseAgent
from app.graph.state import SupplyChainState
from app.models.carrier import Carrier
from app.models.order import Order
from app.models.shipment import Shipment
from app.models.transportation_route import TransportationRoute

logger = structlog.get_logger(__name__)


class TransportationAgent(BaseAgent):
    agent_code = "ADS-06"
    agent_name = "Transportation Agent"

    async def _execute(self, state: SupplyChainState) -> dict[str, Any]:
        session: AsyncSession = self.session
        order: dict = state.get("order") or {}
        warehouse_state: dict = state.get("warehouse") or {}

        order_id_str = order.get("order_id")
        priority = order.get("priority", "standard")
        warehouse_id_str = warehouse_state.get("warehouse_id")
        warehouse_city = warehouse_state.get("city", "Newark")
        warehouse_country = warehouse_state.get("country", "US")

        if not order_id_str:
            raise ValueError("No order_id in state")

        origin_location = f"{warehouse_city}, {warehouse_country}"

        # ── 1. Determine required freight mode ────────────────────────────────
        required_mode: str | None = None
        if priority == "critical":
            required_mode = "air"  # AIS-06 rule: critical → always air

        # ── 2. Find active carriers ───────────────────────────────────────────
        carrier_query = select(Carrier).where(Carrier.status == "active")
        if required_mode:
            from sqlalchemy import cast, String
            from sqlalchemy.dialects.postgresql import ARRAY
            # Filter carriers that include the required freight mode in their array
            carrier_query = carrier_query.where(
                Carrier.freight_modes.any(required_mode)  # type: ignore[arg-type]
            )
        carrier_result = await session.execute(carrier_query)
        carriers = carrier_result.scalars().all()

        if not carriers:
            # Fallback: any active carrier
            r = await session.execute(
                select(Carrier).where(Carrier.status == "active").limit(1)
            )
            carriers = r.scalars().all()

        # ── 3. Find available routes ──────────────────────────────────────────
        route_query = select(TransportationRoute).where(
            TransportationRoute.is_active.is_(True),
            TransportationRoute.origin_location == origin_location,
        )
        if required_mode:
            route_query = route_query.where(
                TransportationRoute.freight_mode == required_mode
            )

        route_result = await session.execute(route_query)
        routes = route_result.scalars().all()

        # ── 4. Select optimal route + carrier ─────────────────────────────────
        selected_route: TransportationRoute | None = None
        selected_carrier: Carrier | None = None

        if routes and carriers:
            carrier_ids = {c.carrier_id for c in carriers}
            eligible_routes = [r for r in routes if r.carrier_id in carrier_ids]

            if eligible_routes:
                if priority in ("high", "critical"):
                    # Fastest route
                    selected_route = min(eligible_routes, key=lambda r: r.transit_days)
                else:
                    # Cheapest route
                    selected_route = min(eligible_routes, key=lambda r: r.base_cost)

                # Find carrier for selected route
                for c in carriers:
                    if c.carrier_id == selected_route.carrier_id:
                        selected_carrier = c
                        break

        # Fallback if no route found — use first available carrier
        if selected_carrier is None and carriers:
            selected_carrier = max(carriers, key=lambda c: c.reliability_score)

        # ── 5. Calculate ETA ──────────────────────────────────────────────────
        transit_days = selected_route.transit_days if selected_route else 5
        eta = datetime.now(tz=timezone.utc) + timedelta(days=transit_days)

        # ── 6. Generate tracking ID ───────────────────────────────────────────
        tracking_raw = f"{order_id_str}-{uuid.uuid4().hex[:8].upper()}"
        tracking_id = tracking_raw

        freight_mode = selected_route.freight_mode if selected_route else (required_mode or "road")

        # ── 7. Create Shipment record ─────────────────────────────────────────
        shipment_id = uuid.uuid4()
        shipment = Shipment(
            shipment_id=shipment_id,
            order_id=uuid.UUID(order_id_str),
            warehouse_id=uuid.UUID(warehouse_id_str) if warehouse_id_str else None,
            carrier=selected_carrier.name if selected_carrier else "Unknown",
            carrier_tracking_id=tracking_id,
            route=f"{origin_location} → {selected_route.destination if selected_route else 'TBD'}",
            freight_mode=freight_mode,
            eta=eta,
            status="dispatched",
        )
        session.add(shipment)

        # ── 8. Update order status to in_transit ──────────────────────────────
        await session.execute(
            update(Order)
            .where(Order.order_id == uuid.UUID(order_id_str))
            .values(status="in_transit")
        )
        await session.flush()

        # ── 9. Publish events ─────────────────────────────────────────────────
        created_payload = {
            "shipment_id": str(shipment_id),
            "order_id": order_id_str,
            "carrier": selected_carrier.name if selected_carrier else "Unknown",
            "carrier_id": str(selected_carrier.carrier_id) if selected_carrier else None,
            "freight_mode": freight_mode,
            "tracking_id": tracking_id,
            "eta": eta.isoformat(),
            "transit_days": transit_days,
        }
        dispatched_payload = {**created_payload, "dispatched_at": datetime.now(tz=timezone.utc).isoformat()}

        await self._publish(state, "ShipmentCreated", created_payload)
        await self._publish(state, "ShipmentDispatched", dispatched_payload)
        # Build event_history incrementally: start from state, add both events
        event_history = self._append_event(state, "ShipmentCreated", created_payload)
        # Create a temporary state snapshot with first event to chain off correctly
        _tmp_state = {**state, "event_history": event_history}
        event_history = self._append_event(_tmp_state, "ShipmentDispatched", dispatched_payload)

        decisions = self._record_decision(
            state, "shipment_dispatched",
            f"Shipment {shipment_id} dispatched via {selected_carrier.name if selected_carrier else 'Unknown'} "
            f"(ETA {eta.strftime('%Y-%m-%d')})",
            created_payload,
        )

        logger.info(
            "Shipment dispatched",
            shipment_id=str(shipment_id),
            carrier=selected_carrier.name if selected_carrier else "Unknown",
            eta=eta.isoformat(),
            workflow_id=state.get("workflow_id"),
        )

        return {
            "shipment": {
                "shipment_id": str(shipment_id),
                "order_id": order_id_str,
                "carrier": selected_carrier.name if selected_carrier else "Unknown",
                "tracking_id": tracking_id,
                "freight_mode": freight_mode,
                "eta": eta.isoformat(),
                "transit_days": transit_days,
                "status": "dispatched",
            },
            "order": {**order, "status": "in_transit"},
            "decisions": decisions,
            "event_history": event_history,
        }
