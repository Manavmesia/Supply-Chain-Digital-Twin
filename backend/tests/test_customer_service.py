"""
Unit tests for CustomerServiceAgent (ADS-08 — US-105).
"""

import uuid
import pytest
from app.agents.operational.customer_service import CustomerServiceAgent
from tests.conftest import CUSTOMER_ID, PRODUCT_LAPTOP_ID


@pytest.mark.asyncio
async def test_customer_service_notification_milestone():
    agent = CustomerServiceAgent(session=None)
    state = {
        "workflow_id": str(uuid.uuid4()),
        "order": {
            "order_id": str(uuid.uuid4()),
            "customer_id": str(CUSTOMER_ID),
        },
        "shipment": {"status": "delivered"},
    }

    result = await agent.run(state)
    assert result.get("workflow_status") != "failed"
    cs_state = result.get("customer_service", {})
    assert cs_state.get("status") == "completed"
    assert len(cs_state.get("notifications", [])) == 1
    assert cs_state["notifications"][0]["milestone"] == "shipment_delivered"

    events = [e["event_type"] for e in result.get("event_history", [])]
    assert "CustomerNotified" in events


@pytest.mark.asyncio
async def test_customer_service_return_request(db_session):
    from app.repositories.order import OrderRepository
    from tests.conftest import make_order
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
        "customer_service": {"request_return": True},
    }

    result = await agent.run(state)
    cs_state = result.get("customer_service", {})
    assert len(cs_state.get("tickets", [])) == 1
    assert cs_state["tickets"][0]["category"] == "return_request"

    events = [e["event_type"] for e in result.get("event_history", [])]
    assert "CustomerNotified" in events
    assert "TicketOpened" in events
    assert "ProductReturned" in events  # AUD-50 Fix


@pytest.mark.asyncio
async def test_customer_service_sla_breach():
    agent = CustomerServiceAgent(session=None)
    state = {
        "workflow_id": str(uuid.uuid4()),
        "order": {"order_id": str(uuid.uuid4()), "customer_id": str(CUSTOMER_ID)},
        "customer_service": {"simulate_sla_breach": True},
    }

    result = await agent.run(state)
    assert result.get("next_node") == "ceo"
    assert result.get("customer_service", {}).get("is_escalated") is True

    events = [e["event_type"] for e in result.get("event_history", [])]
    assert "TicketEscalated" in events
