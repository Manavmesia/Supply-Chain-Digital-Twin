"""
ADS-04 — Warehouse Agent

Responsibilities (from AIS-04 spec):
  - Confirm the warehouse assigned by Inventory Agent
  - Fetch warehouse details (city, country, coordinates)
  - Update warehouse.current_load += order units
  - Mark order as warehouse_assigned
  - Publish ShipmentReady event → hands off to Transportation
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_agent import BaseAgent
from app.graph.state import SupplyChainState
from app.models.order import Order
from app.models.warehouse import Warehouse

logger = structlog.get_logger(__name__)


class WarehouseAgent(BaseAgent):
    agent_code = "ADS-04"
    agent_name = "Warehouse Agent"

    async def _execute(self, state: SupplyChainState) -> dict[str, Any]:
        session: AsyncSession = self.session
        order: dict = state.get("order") or {}
        inventory: dict = state.get("inventory") or {}

        order_id_str = order.get("order_id")
        if not order_id_str:
            raise ValueError("No order_id in state")

        # ── 1. Identify the warehouse from inventory allocation ───────────────
        warehouse_id_str: str | None = None
        total_units = 0

        for product_id, inv_data in inventory.items():
            if isinstance(inv_data, dict) and inv_data.get("status") == "reserved":
                warehouse_id_str = inv_data.get("warehouse_id")
                total_units += inv_data.get("reserved_qty", 0)

        if not warehouse_id_str:
            # Fallback: pick first active warehouse
            result = await session.execute(
                select(Warehouse).where(Warehouse.status == "active").limit(1)
            )
            wh = result.scalar_one_or_none()
            if wh is None:
                raise ValueError("No active warehouses available")
            warehouse_id_str = str(wh.warehouse_id)

        warehouse_id = uuid.UUID(warehouse_id_str)

        # ── 2. Fetch warehouse details ────────────────────────────────────────
        result = await session.execute(
            select(Warehouse).where(Warehouse.warehouse_id == warehouse_id)
        )
        warehouse = result.scalar_one_or_none()
        if warehouse is None:
            raise ValueError(f"Warehouse {warehouse_id} not found")

        # ── 3. Update warehouse current_load ──────────────────────────────────
        # Only add unit count if it won't exceed capacity
        new_load = warehouse.current_load + total_units
        if new_load > warehouse.capacity_units:
            # Try to find an alternative warehouse with capacity
            result2 = await session.execute(
                select(Warehouse).where(
                    Warehouse.status == "active",
                    Warehouse.warehouse_id != warehouse_id,
                    (Warehouse.capacity_units - Warehouse.current_load) >= total_units,
                ).limit(1)
            )
            alt = result2.scalar_one_or_none()
            if alt:
                warehouse = alt
                warehouse_id = alt.warehouse_id
                warehouse_id_str = str(warehouse_id)
                new_load = warehouse.current_load + total_units

        await session.execute(
            update(Warehouse)
            .where(Warehouse.warehouse_id == warehouse_id)
            .values(current_load=new_load)
        )

        # ── 4. Mark order as warehouse_assigned ───────────────────────────────
        await session.execute(
            update(Order)
            .where(Order.order_id == uuid.UUID(order_id_str))
            .values(status="warehouse_assigned")
        )
        await session.flush()

        # ── 5. Publish ShipmentReady ──────────────────────────────────────────
        payload = {
            "order_id": order_id_str,
            "warehouse_id": warehouse_id_str,
            "warehouse_city": warehouse.city,
            "warehouse_country": warehouse.country,
            "units": total_units,
        }
        await self._publish(state, "ShipmentReady", payload)
        event_history = self._append_event(state, "ShipmentReady", payload)
        from pydantic import BaseModel

        class WarehouseDecisionSchema(BaseModel):
            rationale: str

        def _fallback_warehouse() -> WarehouseDecisionSchema:
            return WarehouseDecisionSchema(
                rationale=f"Order assigned to {warehouse.name} ({warehouse.city}, {warehouse.country})"
            )

        wh_context = {
            "warehouse_name": warehouse.name,
            "warehouse_location": f"{warehouse.city}, {warehouse.country}",
            "previous_load": warehouse.current_load,
            "new_load": new_load,
            "capacity": warehouse.capacity_units,
            "order_units": total_units,
        }
        wh_rules = [
            "Warehouse load must never exceed capacity_units.",
            "If load fits, confirm assignment to the selected facility.",
            "Rationale must detail the assigned warehouse, location, and resulting capacity load.",
        ]

        llm_wh_dec, wh_src = await self.decide_with_llm(
            decision_topic="Confirm warehouse assignment and capacity headroom",
            context=wh_context,
            rules=wh_rules,
            schema=WarehouseDecisionSchema,
            fallback_callable=_fallback_warehouse,
        )

        decisions = self._record_decision(
            state,
            "warehouse_assigned",
            llm_wh_dec.rationale or f"Order assigned to {warehouse.name} ({warehouse.city}, {warehouse.country})",
            payload,
            source=wh_src,
        )

        logger.info(
            "Warehouse assigned",
            warehouse=warehouse.name,
            order_id=order_id_str,
            workflow_id=state.get("workflow_id"),
        )

        return {
            "warehouse": {
                "warehouse_id": warehouse_id_str,
                "name": warehouse.name,
                "city": warehouse.city,
                "country": warehouse.country,
                "location": warehouse.location,
                "current_load": new_load,
                "capacity_units": warehouse.capacity_units,
            },
            "order": {**order, "status": "warehouse_assigned"},
            "decisions": decisions,
            "event_history": event_history,
        }
