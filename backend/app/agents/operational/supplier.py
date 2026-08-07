"""
ADS-05 — Supplier Agent

Responsibilities (from AIS-05 spec):
  - Triggered when inventory is out of stock
  - Load active suppliers that can supply the needed product
  - Score suppliers: reliability_score (40%) + lead_time (30%) + price (30%)
  - Blacklist check: never select a blacklisted supplier
  - Create PurchaseOrder (status=draft) for the best scoring supplier
  - Publish SupplierSelected + PurchaseOrderCreated
  - If no supplier available: publish SupplierUnavailable, route to END
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_agent import BaseAgent
from app.graph.state import SupplyChainState
from app.models.purchase_order import PurchaseOrder
from app.models.supplier import Supplier
from app.models.supplier_product import SupplierProduct

logger = structlog.get_logger(__name__)

# Scoring weights (per AIS-05 spec — prefer reliability, then lead time, then price)
_W_RELIABILITY = 0.40
_W_LEAD_TIME   = 0.30
_W_PRICE       = 0.30


class SupplierAgent(BaseAgent):
    agent_code = "ADS-05"
    agent_name = "Supplier Agent"

    async def _execute(self, state: SupplyChainState) -> dict[str, Any]:
        session: AsyncSession = self.session
        order: dict = state.get("order") or {}
        inventory: dict = state.get("inventory") or {}

        order_id_str = order.get("order_id")
        warehouse_state: dict = state.get("warehouse") or {}
        warehouse_id_str = warehouse_state.get("warehouse_id")

        # Fallback warehouse: use first available (warehouse agent may not have run)
        if not warehouse_id_str:
            from sqlalchemy import select as sa_select
            from app.models.warehouse import Warehouse
            r = await session.execute(
                sa_select(Warehouse).where(Warehouse.status == "active").limit(1)
            )
            wh = r.scalar_one_or_none()
            if wh:
                warehouse_id_str = str(wh.warehouse_id)

        # ── Collect out-of-stock products ─────────────────────────────────────
        out_of_stock_items = [
            item for item in (order.get("items") or [])
            if inventory.get(str(item["product_id"]), {}).get("status") == "out_of_stock"
        ]

        if not out_of_stock_items:
            # Nothing to procure — route to transportation
            decisions = self._record_decision(
                state, "no_procurement_needed",
                "All items were in stock; supplier not required",
            )
            return {"decisions": decisions}

        # ── Process each out-of-stock product ─────────────────────────────────
        all_purchase_orders: list[dict] = []
        event_history = list(state.get("event_history") or [])
        decisions = list(state.get("decisions") or [])

        for item in out_of_stock_items:
            product_id = uuid.UUID(str(item["product_id"]))
            needed_qty = int(item["quantity"])

            # Query supplier_products join suppliers for this product
            result = await session.execute(
                select(SupplierProduct, Supplier)
                .join(Supplier, Supplier.supplier_id == SupplierProduct.supplier_id)
                .where(
                    SupplierProduct.product_id == product_id,
                    Supplier.status == "active",          # AIS-05 rule: only active suppliers
                )
            )
            rows = result.all()

            if not rows:
                # No supplier available for this product
                no_supplier_payload = {
                    "product_id": str(product_id),
                    "order_id": order_id_str,
                }
                await self._publish(state, "SupplierUnavailable", no_supplier_payload)
                event_history = self._append_event(
                    state, "SupplierUnavailable", no_supplier_payload
                )
                decisions = self._record_decision(
                    state, "supplier_unavailable",
                    f"No active supplier found for product {product_id}",
                    no_supplier_payload,
                )
                logger.warning("No supplier available", product_id=str(product_id))
                return {
                    "supplier": {"status": "unavailable", "product_id": str(product_id)},
                    "decisions": decisions,
                    "event_history": event_history,
                    "next_node": "transportation",  # Still attempt transport from existing stock
                    "workflow_status": "operational",
                }

            # ── Score suppliers ───────────────────────────────────────────────
            # Normalise: higher reliability = better; lower lead_time = better; lower price = better
            max_reliability = float(max(s.reliability_score for _, s in rows) or 1)
            min_lead_time   = float(min(s.lead_time_days for _, s in rows) or 1)
            min_price       = float(min(float(sp.contract_price) for sp, _ in rows) or 1)

            def _score(sp: SupplierProduct, supplier: Supplier) -> float:
                reliability_norm = float(supplier.reliability_score) / max_reliability
                lead_time_norm = min_lead_time / max(float(supplier.lead_time_days), 1.0)
                price_norm     = min_price / max(float(sp.contract_price), 1.0)
                return (
                    _W_RELIABILITY * reliability_norm
                    + _W_LEAD_TIME * lead_time_norm
                    + _W_PRICE    * price_norm
                )

            best_sp, best_supplier = max(rows, key=lambda row: _score(row[0], row[1]))

            # ── Create PurchaseOrder ──────────────────────────────────────────
            po_id = uuid.uuid4()
            requested_delivery = date.today() + timedelta(days=best_supplier.lead_time_days)

            # Determine order quantity: max(needed_qty, minimum_order_qty)
            order_qty = max(needed_qty, best_sp.minimum_order_qty)

            po = PurchaseOrder(
                po_id=po_id,
                supplier_id=best_supplier.supplier_id,
                product_id=product_id,
                warehouse_id=uuid.UUID(warehouse_id_str) if warehouse_id_str else uuid.uuid4(),
                quantity=order_qty,
                unit_cost=best_sp.contract_price,
                currency="USD",
                status="draft",
                requested_delivery=requested_delivery,
                triggered_by_agent=self.agent_code,
                workflow_id=uuid.UUID(state["workflow_id"]) if state.get("workflow_id") else None,
            )
            session.add(po)
            await session.flush()

            # ── Publish events ────────────────────────────────────────────────
            selected_payload = {
                "supplier_id": str(best_supplier.supplier_id),
                "supplier_name": best_supplier.name,
                "product_id": str(product_id),
                "lead_time_days": best_supplier.lead_time_days,
                "reliability_score": float(best_supplier.reliability_score),
            }
            po_payload = {
                "po_id": str(po_id),
                "supplier_id": str(best_supplier.supplier_id),
                "product_id": str(product_id),
                "quantity": order_qty,
                "unit_cost": str(best_sp.contract_price),
                "requested_delivery": str(requested_delivery),
            }

            await self._publish(state, "SupplierSelected", selected_payload)
            await self._publish(state, "PurchaseOrderCreated", po_payload)
            # AUD-48 Fix: Publish SupplierUpdated whenever a supplier is engaged,
            # carrying full profile data so downstream agents can observe changes
            supplier_updated_payload = {
                "supplier_id": str(best_supplier.supplier_id),
                "supplier_name": best_supplier.name,
                "reliability_score": float(best_supplier.reliability_score),
                "lead_time_days": best_supplier.lead_time_days,
                "status": best_supplier.status,
                "minimum_order_qty": int(best_sp.minimum_order_qty),
                "source_agent": self.agent_code,
            }
            await self._publish(state, "SupplierUpdated", supplier_updated_payload)
            event_history = self._append_event(event_history, "SupplierSelected", selected_payload)
            event_history = self._append_event(event_history, "PurchaseOrderCreated", po_payload)
            event_history = self._append_event(event_history, "SupplierUpdated", supplier_updated_payload)

            decisions = self._record_decision(
                decisions, "supplier_selected",
                f"Selected {best_supplier.name} for product {product_id} "
                f"(score: {_score(best_sp, best_supplier):.2f})",
                selected_payload,
            )

            all_purchase_orders.append(po_payload)
            logger.info(
                "Supplier selected and PO created",
                supplier=best_supplier.name,
                product_id=str(product_id),
                po_id=str(po_id),
                workflow_id=state.get("workflow_id"),
            )

        return {
            "supplier": {
                "status": "selected",
                "purchase_orders": all_purchase_orders,
            },
            "decisions": decisions,
            "event_history": event_history,
            "next_node": "transportation",
        }
