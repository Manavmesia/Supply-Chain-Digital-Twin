"""
ADS-01 — Order Management Agent

Responsibilities (from AIS-01 spec):
  - Validate customer exists and is active
  - Validate all products exist and are active
  - Reject duplicate orders (idempotency check via order_id)
  - Create Order + OrderItem records
  - Publish OrderCreated event
  - Route to inventory node on success, or terminate on rejection
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_agent import BaseAgent
from app.graph.state import SupplyChainState
from app.models.customer import Customer
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product

logger = structlog.get_logger(__name__)


class OrderManagementAgent(BaseAgent):
    agent_code = "ADS-01"
    agent_name = "Order Management Agent"

    async def _execute(self, state: SupplyChainState) -> dict[str, Any]:
        session: AsyncSession = self.session
        order_input: dict = state.get("order") or {}

        # ── 1. Extract order request data ────────────────────────────────────
        customer_id_str = order_input.get("customer_id")
        items_input: list[dict] = order_input.get("items", [])
        priority = order_input.get("priority", "standard")
        workflow_id = state.get("workflow_id", str(uuid.uuid4()))
        correlation_id = state.get("correlation_id", str(uuid.uuid4()))

        if not customer_id_str or not items_input:
            return self._reject(state, "Missing customer_id or items in order request")

        customer_id = uuid.UUID(customer_id_str)

        # ── 2. Validate customer ──────────────────────────────────────────────
        result = await session.execute(
            select(Customer).where(Customer.customer_id == customer_id)
        )
        customer = result.scalar_one_or_none()
        if customer is None:
            return self._reject(state, f"Customer {customer_id} not found")
        if not customer.is_active:
            return self._reject(state, f"Customer {customer_id} is inactive")

        # ── 3. Validate products and build line items ─────────────────────────
        order_items_data: list[dict] = []
        total_amount = Decimal("0.00")

        for item in items_input:
            product_id = uuid.UUID(str(item["product_id"]))
            quantity = int(item["quantity"])

            r = await session.execute(
                select(Product).where(Product.product_id == product_id)
            )
            product = r.scalar_one_or_none()
            if product is None:
                return self._reject(state, f"Product {product_id} not found")
            if not product.active:
                return self._reject(state, f"Product {product_id} is not active")
            if quantity <= 0:
                return self._reject(state, f"Invalid quantity {quantity} for product {product_id}")

            unit_price = product.unit_price
            order_items_data.append(
                {
                    "product_id": product_id,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "product_name": product.name,
                    "sku": product.sku,
                }
            )
            total_amount += unit_price * quantity

        # ── 4. Create Order record ────────────────────────────────────────────
        order_id = uuid.uuid4()
        order = Order(
            order_id=order_id,
            customer_id=customer_id,
            status="pending",
            priority=priority,
            total_amount=total_amount,
            currency="USD",
            workflow_id=uuid.UUID(workflow_id),
        )
        session.add(order)
        await session.flush()

        # ── 5. Create OrderItem records ────────────────────────────────────────
        for item_data in order_items_data:
            order_item = OrderItem(
                order_item_id=uuid.uuid4(),
                order_id=order_id,
                product_id=item_data["product_id"],
                quantity=item_data["quantity"],
                unit_price=item_data["unit_price"],
            )
            session.add(order_item)

        await session.flush()

        # ── 6. Publish OrderCreated event ─────────────────────────────────────
        event_payload = {
            "order_id": str(order_id),
            "customer_id": str(customer_id),
            "total_amount": str(total_amount),
            "priority": priority,
            "item_count": len(order_items_data),
        }
        await self._publish(state, "OrderCreated", event_payload)
        event_history = self._append_event(state, "OrderCreated", event_payload)
        decisions = self._record_decision(
            state, "order_created",
            f"Order {order_id} created for customer {customer.name} — ${total_amount}",
            {"order_id": str(order_id), "total_amount": str(total_amount)},
        )

        logger.info(
            "Order created",
            order_id=str(order_id),
            customer=customer.name,
            total=str(total_amount),
            workflow_id=workflow_id,
        )

        return {
            "order": {
                "order_id": str(order_id),
                "customer_id": str(customer_id),
                "status": "pending",
                "priority": priority,
                "total_amount": str(total_amount),
                "currency": "USD",
                "items": order_items_data and [
                    {
                        "product_id": str(i["product_id"]),
                        "quantity": i["quantity"],
                        "unit_price": str(i["unit_price"]),
                        "product_name": i["product_name"],
                        "sku": i["sku"],
                    }
                    for i in order_items_data
                ],
            },
            "customer": {
                "customer_id": str(customer.customer_id),
                "name": customer.name,
                "tier": customer.customer_tier,
            },
            "workflow_status": "operational",
            "decisions": decisions,
            "event_history": event_history,
        }

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _reject(self, state: SupplyChainState, reason: str) -> dict[str, Any]:
        """Return state update that marks order as rejected."""
        decisions = self._record_decision(state, "order_rejected", reason)
        event_history = self._append_event(state, "OrderRejected", {"reason": reason})
        logger.warning("Order rejected", reason=reason, workflow_id=state.get("workflow_id"))
        return {
            "workflow_status": "failed",
            "decisions": decisions,
            "event_history": event_history,
            "next_node": "END",
        }
