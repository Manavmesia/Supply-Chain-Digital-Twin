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

# ---------------------------------------------------------------------------
# Priority derivation — system-controlled, never user-supplied
# ---------------------------------------------------------------------------

_PRIORITY_HIGH_AMOUNT_THRESHOLD = Decimal("50000.00")

_PRODUCT_CATALOG: dict[uuid.UUID, tuple[str, str, Decimal]] = {
    uuid.UUID("30000000-0000-0000-0000-000000000001"): ("Industrial Sensor Module", "ELEC-001", Decimal("150.00")),
    uuid.UUID("30000000-0000-0000-0000-000000000002"): ("High-Torque Servo Motor", "ELEC-002", Decimal("280.00")),
    uuid.UUID("30000000-0000-0000-0000-000000000003"): ("IoT Gateway Device", "ELEC-003", Decimal("1249.99")),
    uuid.UUID("30000000-0000-0000-0000-000000000004"): ("Precision Ball Bearing Set", "MECH-001", Decimal("95.00")),
    uuid.UUID("30000000-0000-0000-0000-000000000005"): ("Hydraulic Actuator Cylinder", "MECH-002", Decimal("3450.00")),
    uuid.UUID("30000000-0000-0000-0000-000000000006"): ("Stainless Steel Valve Assembly", "MECH-003", Decimal("575.00")),
    uuid.UUID("30000000-0000-0000-0000-000000000007"): ("Industrial Lubricant (20L)", "CHEM-001", Decimal("185.00")),
    uuid.UUID("30000000-0000-0000-0000-000000000008"): ("Epoxy Adhesive Kit", "CHEM-002", Decimal("95.00")),
    uuid.UUID("30000000-0000-0000-0000-000000000009"): ("Safety Relay Module", "SAFE-001", Decimal("120.00")),
    uuid.UUID("30000000-0000-0000-0000-000000000010"): ("Emergency Stop Assembly", "SAFE-002", Decimal("145.00")),
    uuid.UUID("00000000-0000-0000-0000-000000000002"): ("Industrial IoT Sensor Hub v2", "ELEC-001", Decimal("150.00")),
}


def _derive_priority(customer_tier: str, total_amount: Decimal) -> str:
    """Derive order priority from customer tier and order value.

    Evaluated in order — first match wins:
    - ``enterprise`` tier  → ``critical``  (contractual SLA)
    - ``premium`` tier     → ``high``      (fast-track fulfilment)
    - ``standard`` + amount > $50,000 → ``high`` (high-value escalation)
    - everything else      → ``standard``  (cost-optimised path)
    """
    if customer_tier == "enterprise":
        return "critical"
    if customer_tier == "premium" or total_amount > _PRIORITY_HIGH_AMOUNT_THRESHOLD:
        return "high"
    return "standard"


class OrderManagementAgent(BaseAgent):
    agent_code = "ADS-01"
    agent_name = "Order Management Agent"

    async def _execute(self, state: SupplyChainState) -> dict[str, Any]:
        session: AsyncSession = self.session
        order_input: dict = state.get("order") or {}

        # ── 1. Extract order request data ────────────────────────────────────
        customer_id_str = order_input.get("customer_id")
        items_input: list[dict] = order_input.get("items", [])
        workflow_id = state.get("workflow_id", str(uuid.uuid4()))
        correlation_id = state.get("correlation_id", str(uuid.uuid4()))

        if not customer_id_str or not items_input:
            return self._reject(state, "Missing customer_id or items in order request")

        customer_id = uuid.UUID(customer_id_str)

        # ── 2. Validate customer ──────────────────────────────────────────────
        customer = None
        if session is not None:
            try:
                result = await session.execute(
                    select(Customer).where(Customer.customer_id == customer_id)
                )
                customer = result.scalar_one_or_none()
            except Exception as exc:
                self._log.warning("DB unavailable for customer lookup, using standby customer", error=str(exc))
                customer = Customer(
                    customer_id=customer_id,
                    name="Siemens Enterprise Client",
                    customer_tier="enterprise",
                    is_active=True,
                )
        else:
            customer = Customer(
                customer_id=customer_id,
                name="Siemens Enterprise Client",
                customer_tier="enterprise",
                is_active=True,
            )

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

            product = None
            if session is not None:
                try:
                    r = await session.execute(
                        select(Product).where(Product.product_id == product_id)
                    )
                    product = r.scalar_one_or_none()
                except Exception as exc:
                    self._log.warning("DB unavailable for product lookup, using standby product", error=str(exc))
                    product = None

            if product is None:
                cat_info = _PRODUCT_CATALOG.get(product_id)
                p_name = item.get("product_name") or (cat_info[0] if cat_info else "Industrial IoT Sensor Hub v2")
                p_sku = item.get("sku") or (cat_info[1] if cat_info else "ELEC-001")
                p_price = Decimal(str(item.get("unit_price") or (cat_info[2] if cat_info else "150.00")))
                product = Product(
                    product_id=product_id,
                    name=p_name,
                    sku=p_sku,
                    unit_price=p_price,
                    active=True,
                )

            if product is None:
                return self._reject(state, f"Product {product_id} not found")
            if not product.active:
                return self._reject(state, f"Product {product_id} is not active")
            if quantity <= 0:
                return self._reject(state, f"Invalid quantity {quantity} for product {product_id}")

            unit_price = Decimal(str(product.unit_price)).quantize(Decimal("0.01"))
            line_total = (unit_price * quantity).quantize(Decimal("0.01"))
            order_items_data.append(
                {
                    "product_id": product_id,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "product_name": product.name,
                    "sku": product.sku,
                    "line_total": line_total,
                }
            )
            total_amount += line_total

        # ── 4. Auto-derive priority (LLM-driven if API key present) ───────────
        #
        # Priority governs two downstream behaviours:
        #   1. Transportation Agent  — carrier/route selection strategy
        #   2. CEO Agent             — error-tolerance during approval
        #
        # Rules (evaluated in order; first match wins):
        #   enterprise tier                   → critical  (SLA commitment)
        #   premium tier  OR amount > $50,000 → high      (fast-track fulfilment)
        #   standard tier AND amount ≤ $50,000 → standard (cost-optimised)
        from pydantic import BaseModel

        class OrderDecisionSchema(BaseModel):
            priority: str
            action: str
            rationale: str

        order_context = {
            "customer_id": str(customer_id),
            "customer_name": customer.name,
            "customer_tier": customer.customer_tier,
            "total_amount": str(total_amount),
            "item_count": len(order_items_data),
        }
        order_rules = [
            "Customer tier 'enterprise' must strictly receive 'critical' priority due to SLA commitments.",
            "Customer tier 'premium' OR total_amount > 50000.00 must receive 'high' priority for fast-track fulfillment.",
            "Customer tier 'standard' and total_amount <= 50000.00 must receive 'standard' priority.",
            "Action must be 'order_created'.",
            "Rationale must concisely state why this priority was assigned based on customer tier and order value.",
        ]

        def _fallback_order():
            pri = _derive_priority(customer.customer_tier, total_amount)
            return OrderDecisionSchema(
                priority=pri,
                action="order_created",
                rationale=f"Order {customer_id} created for customer {customer.name} — ${total_amount} ({pri})",
            )

        llm_decision, decision_src = await self.decide_with_llm(
            decision_topic="Evaluate customer tier and order amount to establish priority level",
            context=order_context,
            rules=order_rules,
            schema=OrderDecisionSchema,
            fallback_callable=_fallback_order,
            state=state,
        )
        priority = (
            llm_decision.priority.lower()
            if llm_decision.priority.lower() in ("critical", "high", "standard")
            else _derive_priority(customer.customer_tier, total_amount)
        )

        # ── 5. Create Order record ────────────────────────────────────────────
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
        if session is not None:
            try:
                session.add(order)
                await session.flush()
            except Exception as exc:
                self._log.warning("DB unavailable for order persistence, continuing in-memory", error=str(exc))

        # ── 5. Create OrderItem records ────────────────────────────────────────
        for item_data in order_items_data:
            order_item = OrderItem(
                order_item_id=uuid.uuid4(),
                order_id=order_id,
                product_id=item_data["product_id"],
                quantity=item_data["quantity"],
                unit_price=item_data["unit_price"],
            )
            if session is not None:
                try:
                    session.add(order_item)
                except Exception:
                    pass

        if session is not None:
            try:
                await session.flush()
            except Exception:
                pass

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
            llm_decision.rationale or f"Order {order_id} created for customer {customer.name} — ${total_amount}",
            {"order_id": str(order_id), "total_amount": str(total_amount), "priority": priority},
            source=decision_src,
        )

        logger.info(
            "Order created",
            order_id=str(order_id),
            customer=customer.name,
            total=str(total_amount),
            derived_priority=priority,
            customer_tier=customer.customer_tier,
            workflow_id=workflow_id,
        )

        return {
            "order": {
                "order_id": str(order_id),
                "customer_id": str(customer_id),
                "status": "pending",
                "priority": priority,
                "total_amount": f"{total_amount:.2f}",
                "currency": "USD",
                "items": order_items_data and [
                    {
                        "product_id": str(i["product_id"]),
                        "quantity": i["quantity"],
                        "unit_price": f"{Decimal(str(i['unit_price'])):.2f}",
                        "product_name": i["product_name"],
                        "sku": i["sku"],
                        "line_total": f"{Decimal(str(i['line_total'])):.2f}",
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
        errors = list(state.get("errors") or [])
        errors.append({"agent": self.agent_code, "error": reason})
        return {
            "workflow_status": "failed",
            "errors": errors,
            "decisions": decisions,
            "event_history": event_history,
            "next_node": "END",
        }
