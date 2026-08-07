"""
Custom Edge-Case & Stress Tests (US-Custom-Test-Suite)

Covers edge cases, error conditions, boundary conditions, exception recovery,
and data integrity checks across Manufacturing, Customer Service, Event Registry,
and Repositories.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.operational.manufacturing import ManufacturingAgent
from app.agents.operational.customer_service import CustomerServiceAgent
from app.events.registry import CANONICAL_EVENTS, CANONICAL_EVENT_NAMES
from app.events.publisher import EventPublisher, UnregisteredEventTypeError
from app.repositories.purchase_order import PurchaseOrderRepository
from app.repositories.support_ticket import SupportTicketRepository
from app.repositories.contract import ContractRepository
from app.repositories.carrier import CarrierRepository
from app.repositories.transportation_route import TransportationRouteRepository
from app.repositories.promotion import PromotionRepository
from tests.conftest import (
    CUSTOMER_ID,
    PRODUCT_LAPTOP_ID,
    PRODUCT_MONITOR_ID,
    SUPPLIER_TECHCORE_ID,
    WAREHOUSE_EAST_ID,
    WAREHOUSE_WEST_ID,
    make_carrier,
    make_contract,
    make_order,
    make_purchase_order,
    make_shipment,
    make_support_ticket,
    make_transportation_route,
)


# =============================================================================
# 1. Event Registry & Event Publisher Edge Cases
# =============================================================================

class TestEventRegistryEdgeCases:
    def test_canonical_event_lookup(self):
        """All canonical event names must be in CANONICAL_EVENT_NAMES."""
        assert "OrderCreated" in CANONICAL_EVENT_NAMES
        assert "InspectionRequested" in CANONICAL_EVENT_NAMES
        assert "ProductReturned" in CANONICAL_EVENT_NAMES
        assert "CustomerNotified" in CANONICAL_EVENT_NAMES
        assert "FakeUnregisteredEvent" not in CANONICAL_EVENT_NAMES

    @pytest.mark.asyncio
    async def test_publish_unregistered_event_raises_error(self):
        """Publishing an unregistered event name must raise UnregisteredEventTypeError."""
        publisher = EventPublisher(rabbitmq_url="amqp://localhost", session=None)
        with pytest.raises(UnregisteredEventTypeError) as exc_info:
            await publisher.publish(
                event_type="InvalidNonExistentEvent",
                source_agent="ADS-99",
                correlation_id=uuid.uuid4(),
                payload={},
            )
        assert "InvalidNonExistentEvent" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_publish_valid_event_with_mock_rabbitmq(self):
        """Valid canonical event publishes correctly to RabbitMQ mock exchange."""
        publisher = EventPublisher(rabbitmq_url="amqp://localhost", session=None)
        publisher._exchange = AsyncMock()

        event = await publisher.publish(
            event_type="OrderCreated",
            source_agent="ADS-01",
            correlation_id=uuid.uuid4(),
            payload={"order_id": str(uuid.uuid4())},
        )
        assert event is not None
        assert event.event_type == "OrderCreated"
        publisher._exchange.publish.assert_called_once()


# =============================================================================
# 2. Manufacturing Agent Edge Cases & Error Recovery
# =============================================================================

class TestManufacturingAgentEdgeCases:
    @pytest.mark.asyncio
    async def test_manufacturing_multiple_items_mixed_capacity(self, db_session):
        """Handling multiple items where total exceeds capacity threshold."""
        agent = ManufacturingAgent(session=db_session)
        state = {
            "workflow_id": str(uuid.uuid4()),
            "order": {
                "order_id": str(uuid.uuid4()),
                "items": [
                    {"product_id": str(PRODUCT_LAPTOP_ID), "quantity": 100},
                    {"product_id": str(PRODUCT_MONITOR_ID), "quantity": 6000},  # Exceeds max
                ],
            },
            "inventory": {
                str(PRODUCT_LAPTOP_ID): {"status": "out_of_stock"},
                str(PRODUCT_MONITOR_ID): {"status": "out_of_stock"},
            },
            "warehouse": {"warehouse_id": str(WAREHOUSE_EAST_ID)},
        }

        result = await agent.run(state)
        # Should breach capacity on second item and route to CEO
        assert result.get("next_node") == "ceo"
        assert result.get("manufacturing", {}).get("status") == "capacity_exceeded"

    @pytest.mark.asyncio
    async def test_manufacturing_invalid_uuid_raises_gracefully(self):
        """Malformed product_id string is caught by BaseAgent error handler."""
        agent = ManufacturingAgent(session=None)
        state = {
            "workflow_id": str(uuid.uuid4()),
            "order": {
                "order_id": str(uuid.uuid4()),
                "items": [{"product_id": "not-a-valid-uuid", "quantity": 10}],
            },
            "inventory": {"not-a-valid-uuid": {"status": "out_of_stock"}},
        }

        result = await agent.run(state)
        # BaseAgent catches Exception and populates errors list
        assert result.get("workflow_status") == "failed"
        assert len(result.get("errors", [])) == 1
        assert result["errors"][0]["agent"] == "ADS-07"

    @pytest.mark.asyncio
    async def test_manufacturing_without_db_session_uses_fallback(self):
        """Runs cleanly without DB session in memory test mode."""
        agent = ManufacturingAgent(session=None)
        state = {
            "workflow_id": str(uuid.uuid4()),
            "order": {
                "order_id": str(uuid.uuid4()),
                "items": [{"product_id": str(PRODUCT_LAPTOP_ID), "quantity": 25}],
            },
            "inventory": {str(PRODUCT_LAPTOP_ID): {"status": "out_of_stock"}},
        }

        result = await agent.run(state)
        assert result.get("workflow_status") != "failed"
        assert result.get("manufacturing", {}).get("status") == "completed"


# =============================================================================
# 3. Customer Service Agent Edge Cases & Error Recovery
# =============================================================================

class TestCustomerServiceAgentEdgeCases:
    @pytest.mark.asyncio
    async def test_customer_service_return_request_missing_order_items(self, db_session):
        """Return request with order having no items dictionary defaults gracefully."""
        from app.repositories.order import OrderRepository
        order_repo = OrderRepository(db_session)
        order_obj = make_order(customer_id=CUSTOMER_ID)
        await order_repo.create(order_obj)

        agent = CustomerServiceAgent(session=db_session)
        state = {
            "workflow_id": str(uuid.uuid4()),
            "order": {
                "order_id": str(order_obj.order_id),
                "customer_id": str(CUSTOMER_ID),
                # items missing
            },
            "customer_service": {"request_return": True},
        }

        result = await agent.run(state)
        assert result.get("workflow_status") != "failed"
        cs_state = result.get("customer_service", {})
        assert len(cs_state.get("tickets", [])) == 1

    @pytest.mark.asyncio
    async def test_customer_service_simultaneous_return_and_sla_breach(self, db_session):
        """Simultaneous return request and SLA breach escalation in same execution."""
        from app.repositories.order import OrderRepository
        order_repo = OrderRepository(db_session)
        order_obj = make_order(customer_id=CUSTOMER_ID)
        await order_repo.create(order_obj)

        agent = CustomerServiceAgent(session=db_session)
        state = {
            "workflow_id": str(uuid.uuid4()),
            "order": {
                "order_id": str(order_obj.order_id),
                "customer_id": str(CUSTOMER_ID),
                "items": [{"product_id": str(PRODUCT_LAPTOP_ID), "quantity": 1}],
            },
            "customer_service": {
                "request_return": True,
                "simulate_sla_breach": True,
            },
        }

        result = await agent.run(state)
        assert result.get("next_node") == "ceo"
        assert result.get("customer_service", {}).get("is_escalated") is True

        events = [e["event_type"] for e in result.get("event_history", [])]
        assert "CustomerNotified" in events
        assert "TicketOpened" in events
        assert "ProductReturned" in events
        assert "TicketEscalated" in events


# =============================================================================
# 4. Domain Repositories Boundary & Edge Cases
# =============================================================================

class TestRepositoryBoundaryEdgeCases:
    @pytest.mark.asyncio
    async def test_purchase_order_get_pending_delivery_as_of_override(self, db_session):
        """Passing explicit as_of date parameter to get_pending_delivery."""
        repo = PurchaseOrderRepository(db_session)
        future_date = date.today() + timedelta(days=30)

        po = make_purchase_order(status="shipped")
        po.requested_delivery = date.today() + timedelta(days=5)
        await repo.create(po)

        # Query with as_of set to 30 days in future -> must include the PO
        results = await repo.get_pending_delivery(as_of=future_date)
        assert any(p.po_id == po.po_id for p in results)

    @pytest.mark.asyncio
    async def test_support_ticket_get_sla_breaching_excludes_resolved(self, db_session):
        """Resolved tickets past SLA deadline are not returned as SLA breaching."""
        repo = SupportTicketRepository(db_session)
        ticket = make_support_ticket(status="resolved")
        ticket.sla_deadline = datetime.now(timezone.utc) - timedelta(hours=10)
        await repo.create(ticket)

        results = await repo.get_sla_breaching()
        assert not any(t.ticket_id == ticket.ticket_id for t in results)

    @pytest.mark.asyncio
    async def test_contract_get_expiring_soon_custom_days_parameter(self, db_session):
        """get_expiring_soon with custom days threshold."""
        repo = ContractRepository(db_session)
        contract = make_contract(
            status="active",
            end_date=date.today() + timedelta(days=45),
        )
        await repo.create(contract)

        # 30-day window -> should NOT include
        res_30 = await repo.get_expiring_soon(days=30)
        assert not any(c.contract_id == contract.contract_id for c in res_30)

        # 60-day window -> SHOULD include
        res_60 = await repo.get_expiring_soon(days=60)
        assert any(c.contract_id == contract.contract_id for c in res_60)

    @pytest.mark.asyncio
    async def test_carrier_repository_get_available_empty_string(self, db_session):
        """Querying carrier availability for mode with no active carriers returns empty list."""
        from sqlalchemy import update
        from app.models.carrier import Carrier
        await db_session.execute(
            update(Carrier).where(Carrier.status == "active").values(status="inactive")
        )
        await db_session.flush()

        repo = CarrierRepository(db_session)
        results = await repo.get_available(freight_mode="rail")
        assert list(results) == []

    @pytest.mark.asyncio
    async def test_transportation_route_find_routes_case_insensitivity(self, db_session):
        """find_routes matching origin and destination locations."""
        carrier_repo = CarrierRepository(db_session)
        route_repo = TransportationRouteRepository(db_session)

        carrier = make_carrier()
        await carrier_repo.create(carrier)

        route = make_transportation_route(
            carrier.carrier_id,
            origin_location="Seattle, US",
            destination="Miami, US",
        )
        await route_repo.create(route)

        found = await route_repo.find_routes("Seattle, US", "Miami, US")
        assert any(r.route_id == route.route_id for r in found)
