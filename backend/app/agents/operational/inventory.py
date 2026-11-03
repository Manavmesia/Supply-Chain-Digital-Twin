"""
ADS-03 — Inventory Agent

Responsibilities (from AIS-03 spec):
  - For each order item: check availability across warehouses
  - Reserve stock (increment reserved_qty, never allow negative available)
  - Detect safety stock violations post-reservation → publish InventoryLow
  - If insufficient stock → publish InventoryOutOfStock, route to supplier
  - If all items reserved → publish InventoryAllocated, route to warehouse
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_agent import BaseAgent
from app.graph.state import SupplyChainState
from app.models.inventory import Inventory
from app.models.warehouse import Warehouse

logger = structlog.get_logger(__name__)


class InventoryAgent(BaseAgent):
    agent_code = "ADS-03"
    agent_name = "Inventory Agent"

    async def _execute(self, state: SupplyChainState) -> dict[str, Any]:
        session: AsyncSession = self.session
        order: dict = state.get("order") or {}
        items: list[dict] = order.get("items") or []

        if not items:
            return self._out_of_stock(state, "No items in order", {})

        # ── Build inventory map: for each product find best warehouse ─────────
        availability: dict[str, Any] = {}
        all_reserved = True
        out_of_stock_products: list[str] = []
        low_stock_products: list[str] = []
        selected_warehouse_id: str | None = None

        for item in items:
            product_id = uuid.UUID(str(item["product_id"]))
            needed_qty = int(item["quantity"])

            # Find all warehouses with sufficient stock (available - reserved >= needed)
            result = await session.execute(
                select(Inventory).where(
                    Inventory.product_id == product_id,
                    (Inventory.available_qty - Inventory.reserved_qty) >= needed_qty,
                )
            )
            inventory_records = result.scalars().all()

            if not inventory_records:
                # No warehouse can fulfil this item
                all_reserved = False
                out_of_stock_products.append(str(product_id))
                availability[str(product_id)] = {
                    "status": "out_of_stock",
                    "needed": needed_qty,
                    "available": 0,
                }
                continue

            # Pick first matching warehouse (warehouse agent will optimise later)
            inv = inventory_records[0]
            warehouse_id = inv.warehouse_id

            if selected_warehouse_id is None:
                selected_warehouse_id = str(warehouse_id)

            # Reserve: increment reserved_qty
            await session.execute(
                update(Inventory)
                .where(
                    Inventory.product_id == product_id,
                    Inventory.warehouse_id == warehouse_id,
                )
                .values(reserved_qty=Inventory.reserved_qty + needed_qty)
            )
            await session.flush()

            # Re-read after update
            r2 = await session.execute(
                select(Inventory).where(
                    Inventory.product_id == product_id,
                    Inventory.warehouse_id == warehouse_id,
                )
            )
            inv_after = None
            if hasattr(r2, "scalar_one_or_none") and callable(r2.scalar_one_or_none):
                inv_after = r2.scalar_one_or_none()
            if inv_after is None and hasattr(r2, "scalar_one") and callable(r2.scalar_one):
                try:
                    inv_after = r2.scalar_one()
                except Exception:
                    inv_after = None
            if inv_after is None:
                inv_after = inv

            net_available = int(inv_after.available_qty) - int(inv_after.reserved_qty)

            availability[str(product_id)] = {
                "status": "reserved",
                "warehouse_id": str(warehouse_id),
                "reserved_qty": needed_qty,
                "net_available_after": net_available,
                "safety_stock": int(inv_after.safety_stock),
            }

            # Check safety stock
            if net_available < int(inv_after.safety_stock):
                low_stock_products.append(str(product_id))

        # ── Publish low-stock events & assemble autonomous replenishment requests ──
        event_history = list(state.get("event_history") or [])
        decisions = list(state.get("decisions") or [])
        replenishment_requests: list[dict[str, Any]] = []

        for pid in low_stock_products:
            inv_data = availability.get(pid, {})
            safety_stock = int(inv_data.get("safety_stock", 200))
            net_avail = int(inv_data.get("net_available_after", 0))
            reorder_qty = max(safety_stock * 2 - net_avail, 100)
            wh_target = inv_data.get("warehouse_id") or selected_warehouse_id
            replenishment_requests.append({
                "product_id": pid,
                "warehouse_id": wh_target,
                "quantity": reorder_qty,
                "reason": "safety_stock_breach",
            })
            payload = {
                "product_id": pid,
                "warehouse_id": selected_warehouse_id,
                "reorder_qty": reorder_qty,
                "reason": "safety_stock_breach",
            }
            await self._publish(state, "InventoryLow", payload)
            event_history = self._append_event(event_history, "InventoryLow", payload)
            logger.warning("Safety stock breach — autonomous replenishment queued", product_id=pid, reorder_qty=reorder_qty)

        for pid in out_of_stock_products:
            needed = int(availability.get(pid, {}).get("needed", 50))
            reorder_qty = max(needed * 2, 100)
            replenishment_requests.append({
                "product_id": pid,
                "warehouse_id": selected_warehouse_id,
                "quantity": reorder_qty,
                "reason": "out_of_stock",
            })

        if replenishment_requests:
            rep_payload = {
                "order_id": order.get("order_id"),
                "replenishment_requests": replenishment_requests,
                "count": len(replenishment_requests),
            }
            await self._publish(state, "AutonomousReplenishmentTriggered", rep_payload)
            event_history = self._append_event(event_history, "AutonomousReplenishmentTriggered", rep_payload)

            # If all items are reserved, order proceeds directly to warehouse;
            # persist autonomous inbound replenishment PO(s) immediately.
            if all_reserved:
                from datetime import date, timedelta
                from app.core import persistence
                from app.agents.operational.supplier import PRODUCT_MAP
                for req in replenishment_requests:
                    try:
                        pid_str = str(req["product_id"])
                        qty = int(req["quantity"])
                        wh_str = str(req.get("warehouse_id") or selected_warehouse_id or "")
                        prod_info = PRODUCT_MAP.get(pid_str, ("Industrial Component", "SKU-001"))
                        po_id = str(uuid.uuid4())
                        persistence.save_purchase_order({
                            "po_id": po_id,
                            "product_id": pid_str,
                            "product_name": prod_info[0],
                            "product_sku": prod_info[1],
                            "supplier_id": str(uuid.uuid4()),
                            "supplier_name": "Apex Global Logistics & Supplies",
                            "warehouse_id": wh_str,
                            "quantity": qty,
                            "unit_cost": 120.00,
                            "total_cost": round(qty * 120.00, 2),
                            "lead_time_days": 4,
                            "requested_delivery": (date.today() + timedelta(days=4)).isoformat(),
                            "status": "in_transit",
                            "triggered_by_agent": self.agent_code,
                            "workflow_id": str(state.get("workflow_id") or ""),
                        })
                    except Exception as ex:
                        logger.warning("Could not persist autonomous PO in inventory agent", error=str(ex))

        # ── Route based on stock outcome (LLM-driven if API key present) ──────
        from pydantic import BaseModel

        class InventoryDecisionSchema(BaseModel):
            rationale: str

        def _fallback_inventory() -> InventoryDecisionSchema:
            if not all_reserved:
                return InventoryDecisionSchema(
                    rationale=f"Products {out_of_stock_products} unavailable — routing to Supplier for procurement"
                )
            rep_note = f" (Autonomous inbound replenishment triggered for {len(replenishment_requests)} low-stock SKU(s))" if replenishment_requests else ""
            return InventoryDecisionSchema(
                rationale=f"All {len(items)} items reserved from warehouse {selected_warehouse_id}{rep_note}"
            )

        inv_context = {
            "all_reserved": all_reserved,
            "out_of_stock_products": out_of_stock_products,
            "low_stock_products": low_stock_products,
            "replenishment_requests_count": len(replenishment_requests),
            "selected_warehouse_id": selected_warehouse_id,
            "item_count": len(items),
        }
        inv_rules = [
            "If any items cannot be reserved, route must escalate to supplier for procurement.",
            "If all items are reserved, route to warehouse for picking and packing (replenishment orders are created autonomously).",
            "Rationale must detail the reservation status and warehouse assignment.",
        ]

        llm_inv_dec, inv_src = await self.decide_with_llm(
            decision_topic="Evaluate multi-facility inventory allocation and reservation",
            context=inv_context,
            rules=inv_rules,
            schema=InventoryDecisionSchema,
            fallback_callable=_fallback_inventory,
        )

        if not all_reserved:
            # At least one product is out of stock — route to supplier
            payload = {
                "order_id": order.get("order_id"),
                "out_of_stock": out_of_stock_products,
                "replenishment_requests": replenishment_requests,
            }
            await self._publish(state, "InventoryOutOfStock", payload)
            event_history = self._append_event(event_history, "InventoryOutOfStock", payload)
            decisions = self._record_decision(
                decisions, "out_of_stock",
                llm_inv_dec.rationale or f"Products {out_of_stock_products} unavailable — routing to Supplier",
                {"out_of_stock_products": out_of_stock_products},
                source=inv_src,
            )
            logger.info(
                "Inventory out of stock",
                products=out_of_stock_products,
                workflow_id=state.get("workflow_id"),
            )
            return {
                "inventory": availability,
                "replenishment_requests": replenishment_requests,
                "decisions": decisions,
                "event_history": event_history,
                "next_node": "supplier",
            }

        # All items reserved — order proceeds to warehouse for picking & shipping
        target_next = "warehouse"
        payload = {
            "order_id": order.get("order_id"),
            "reserved_items": list(availability.keys()),
            "warehouse_id": selected_warehouse_id,
            "replenishment_triggered": bool(replenishment_requests),
        }
        await self._publish(state, "InventoryAllocated", payload)
        event_history = self._append_event(event_history, "InventoryAllocated", payload)
        decisions = self._record_decision(
            decisions, "inventory_allocated",
            llm_inv_dec.rationale or f"All {len(items)} items reserved from warehouse {selected_warehouse_id}"
            + (f" with {len(replenishment_requests)} autonomous replenishment PO(s) queued" if replenishment_requests else ""),
            payload,
            source=inv_src,
        )
        logger.info(
            "Inventory allocated",
            warehouse_id=selected_warehouse_id,
            replenishment_count=len(replenishment_requests),
            workflow_id=state.get("workflow_id"),
        )
        return {
            "inventory": availability,
            "replenishment_requests": replenishment_requests,
            "decisions": decisions,
            "event_history": event_history,
            "next_node": target_next,
        }

    def _out_of_stock(
        self, state: SupplyChainState, reason: str, availability: dict
    ) -> dict[str, Any]:
        decisions = self._record_decision(state, "out_of_stock", reason)
        return {
            "inventory": availability,
            "decisions": decisions,
            "next_node": "supplier",
        }
