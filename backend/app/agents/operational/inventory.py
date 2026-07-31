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
            inv_after = r2.scalar_one()
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

        # ── Publish low-stock events ──────────────────────────────────────────
        event_history = list(state.get("event_history") or [])
        decisions = list(state.get("decisions") or [])

        for pid in low_stock_products:
            payload = {"product_id": pid, "warehouse_id": selected_warehouse_id}
            await self._publish(state, "InventoryLow", payload)
            event_history = self._append_event(event_history, "InventoryLow", payload)
            logger.warning("Safety stock breach", product_id=pid)

        # ── Route based on stock outcome ──────────────────────────────────────
        if not all_reserved:
            # At least one product is out of stock — route to supplier
            payload = {
                "order_id": order.get("order_id"),
                "out_of_stock": out_of_stock_products,
            }
            await self._publish(state, "InventoryOutOfStock", payload)
            event_history = self._append_event(event_history, "InventoryOutOfStock", payload)
            decisions = self._record_decision(
                decisions, "out_of_stock",
                f"Products {out_of_stock_products} unavailable — routing to Supplier",
                {"out_of_stock_products": out_of_stock_products},
            )
            logger.info(
                "Inventory out of stock",
                products=out_of_stock_products,
                workflow_id=state.get("workflow_id"),
            )
            return {
                "inventory": availability,
                "decisions": decisions,
                "event_history": event_history,
                "next_node": "supplier",
            }

        # All items reserved — route to warehouse
        payload = {
            "order_id": order.get("order_id"),
            "reserved_items": list(availability.keys()),
            "warehouse_id": selected_warehouse_id,
        }
        await self._publish(state, "InventoryAllocated", payload)
        event_history = self._append_event(event_history, "InventoryAllocated", payload)
        decisions = self._record_decision(
            decisions, "inventory_allocated",
            f"All {len(items)} items reserved from warehouse {selected_warehouse_id}",
            payload,
        )
        logger.info(
            "Inventory allocated",
            warehouse_id=selected_warehouse_id,
            workflow_id=state.get("workflow_id"),
        )
        return {
            "inventory": availability,
            "decisions": decisions,
            "event_history": event_history,
            "next_node": "warehouse",
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
