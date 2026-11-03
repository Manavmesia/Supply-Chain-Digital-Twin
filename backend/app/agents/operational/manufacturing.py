"""
ADS-07 — Manufacturing Agent

Responsibilities (from AIS-07 & BACKLOG US-97-99):
  - Triggered by ProductionRequested (from Planner Agent) or demand forecast signals
  - Evaluates factory capacity for requested product runs
  - Schedules production runs in manufacturing_orders table (with mandatory warehouse_id FK)
  - Updates production lifecycle: planned -> in_progress -> completed
  - Upon completion: publishes ManufacturingCompleted AND InspectionRequested (AUD-49 fix)
  - If capacity exceeded: publishes CapacityExceeded and routes to planner/CEO
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_agent import BaseAgent
from app.graph.state import SupplyChainState
from app.models.manufacturing_order import ManufacturingOrder
from app.models.warehouse import Warehouse

logger = structlog.get_logger(__name__)

# Factory capacity threshold default (units per warehouse/product run)
_DEFAULT_MAX_CAPACITY = 5000


class ManufacturingAgent(BaseAgent):
    agent_code = "ADS-07"
    agent_name = "Manufacturing Agent"

    async def _execute(self, state: SupplyChainState) -> dict[str, Any]:
        session: AsyncSession = self.session
        order: dict = state.get("order") or {}
        inventory: dict = state.get("inventory") or {}
        supplier_state: dict = state.get("supplier") or {}
        
        event_history = list(state.get("event_history") or [])
        decisions = list(state.get("decisions") or [])

        # Determine target warehouse ID for receiving manufactured goods (AUD-20 rule)
        warehouse_state: dict = state.get("warehouse") or {}
        warehouse_id_str = warehouse_state.get("warehouse_id")

        if not warehouse_id_str and session:
            r = await session.execute(
                select(Warehouse).where(Warehouse.status == "active").limit(1)
            )
            wh = r.scalar_one_or_none()
            if wh:
                warehouse_id_str = str(wh.warehouse_id)

        target_warehouse_id = uuid.UUID(warehouse_id_str) if warehouse_id_str else uuid.uuid4()

        # Identify items requiring manufacturing (e.g. supplier unavailable or explicit request)
        items_to_manufacture = []
        if order.get("items"):
            for item in order.get("items"):
                pid_str = str(item["product_id"])
                # If inventory is out of stock AND supplier was unavailable or out of stock
                inv_status = inventory.get(pid_str, {}).get("status")
                sup_status = supplier_state.get("status")
                if inv_status == "out_of_stock" or sup_status == "unavailable":
                    items_to_manufacture.append(item)

        # Fallback if no items explicitly flagged: use first item if order present
        if not items_to_manufacture and order.get("items"):
            items_to_manufacture = [order["items"][0]]

        if not items_to_manufacture:
            decisions = self._record_decision(
                state,
                "no_manufacturing_needed",
                "No products required production run",
            )
            return {
                "decisions": decisions,
                "next_node": "reporting",
            }

        all_mo_payloads: list[dict[str, Any]] = []

        for item in items_to_manufacture:
            product_id = uuid.UUID(str(item["product_id"]))
            planned_qty = int(item.get("quantity", 100))

            # ── Capacity Check ────────────────────────────────────────────────
            current_active_qty = 0
            if session:
                load_query = select(func.coalesce(func.sum(ManufacturingOrder.planned_qty), 0)).where(
                    ManufacturingOrder.product_id == product_id,
                    ManufacturingOrder.status.in_(["planned", "in_progress"]),
                )
                res = await session.execute(load_query)
                current_active_qty = res.scalar_one()

            if current_active_qty + planned_qty > _DEFAULT_MAX_CAPACITY:
                capacity_payload = {
                    "product_id": str(product_id),
                    "requested_qty": planned_qty,
                    "current_active_qty": current_active_qty,
                    "max_capacity": _DEFAULT_MAX_CAPACITY,
                }
                await self._publish(state, "CapacityExceeded", capacity_payload)
                event_history = self._append_event(event_history, "CapacityExceeded", capacity_payload)
                decisions = self._record_decision(
                    decisions,
                    "capacity_exceeded",
                    f"Factory capacity exceeded for product {product_id}",
                    capacity_payload,
                )
                logger.warning("Manufacturing capacity exceeded", product_id=str(product_id))
                return {
                    "manufacturing": {"status": "capacity_exceeded", "product_id": str(product_id)},
                    "decisions": decisions,
                    "event_history": event_history,
                    "next_node": "ceo",
                    "workflow_status": "operational",
                }

            # ── Create & Schedule Manufacturing Order ─────────────────────────
            mo_id = uuid.uuid4()
            now = datetime.now(timezone.utc)
            scheduled_start = now + timedelta(hours=1)
            scheduled_end = scheduled_start + timedelta(days=3)

            mo = ManufacturingOrder(
                mo_id=mo_id,
                product_id=product_id,
                warehouse_id=target_warehouse_id,
                planned_qty=planned_qty,
                completed_qty=planned_qty,  # Complete in MVP flow
                status="completed",
                scheduled_start=scheduled_start,
                scheduled_end=scheduled_end,
                actual_start=now,
                actual_end=now + timedelta(hours=2),
                triggered_by="demand_forecast" if not order else "inventory_agent",
                workflow_id=uuid.UUID(state["workflow_id"]) if state.get("workflow_id") else None,
                created_at=now,
                updated_at=now,
            )

            if session:
                session.add(mo)
                await session.flush()

            # ── Event Publishing ──────────────────────────────────────────────
            started_payload = {
                "mo_id": str(mo_id),
                "product_id": str(product_id),
                "warehouse_id": str(target_warehouse_id),
                "planned_qty": planned_qty,
            }
            completed_payload = {
                "mo_id": str(mo_id),
                "product_id": str(product_id),
                "warehouse_id": str(target_warehouse_id),
                "completed_qty": planned_qty,
            }
            inspection_payload = {
                "inspection_id": str(uuid.uuid4()),
                "product_id": str(product_id),
                "manufacturing_order_id": str(mo_id),
                "warehouse_id": str(target_warehouse_id),
                "sample_size": max(10, int(planned_qty * 0.05)),
            }

            await self._publish(state, "ManufacturingStarted", started_payload)
            await self._publish(state, "ManufacturingCompleted", completed_payload)
            # AUD-49 Fix: Publish InspectionRequested to trigger QA Agent automatically
            await self._publish(state, "InspectionRequested", inspection_payload)

            event_history = self._append_event(event_history, "ManufacturingStarted", started_payload)
            event_history = self._append_event(event_history, "ManufacturingCompleted", completed_payload)
            event_history = self._append_event(event_history, "InspectionRequested", inspection_payload)

            from pydantic import BaseModel

            class ManufacturingDecisionSchema(BaseModel):
                rationale: str

            def _fallback_mfg() -> ManufacturingDecisionSchema:
                return ManufacturingDecisionSchema(
                    rationale=f"Completed manufacturing run {mo_id} for product {product_id} ({planned_qty} units)"
                )

            llm_mfg_dec, mfg_src = await self.decide_with_llm(
                decision_topic=f"Approve and schedule manufacturing lot for product {product_id}",
                context={
                    "product_id": str(product_id),
                    "warehouse_id": str(target_warehouse_id),
                    "planned_qty": planned_qty,
                    "max_capacity": _DEFAULT_MAX_CAPACITY,
                },
                rules=[
                    "Validate production capacity against maximum threshold (5,000 units).",
                    "Schedule manufacturing start and completion times with quality inspection handover.",
                ],
                schema=ManufacturingDecisionSchema,
                fallback_callable=_fallback_mfg,
            )

            decisions = self._record_decision(
                decisions,
                "manufacturing_completed",
                llm_mfg_dec.rationale or f"Completed manufacturing run {mo_id} for product {product_id} ({planned_qty} units)",
                completed_payload,
                source=mfg_src,
            )

            mo_payload = {
                "mo_id": str(mo_id),
                "product_id": str(product_id),
                "warehouse_id": str(target_warehouse_id),
                "planned_qty": planned_qty,
                "completed_qty": planned_qty,
                "status": "completed",
            }
            all_mo_payloads.append(mo_payload)

        return {
            "manufacturing": {
                "status": "completed",
                "orders": all_mo_payloads,
            },
            "decisions": decisions,
            "event_history": event_history,
            "next_node": "reporting",
        }
