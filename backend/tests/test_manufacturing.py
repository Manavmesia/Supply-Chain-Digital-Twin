"""
Unit tests for ManufacturingAgent (ADS-07 — US-100).
"""

import uuid
import pytest
from app.agents.operational.manufacturing import ManufacturingAgent
from tests.conftest import PRODUCT_LAPTOP_ID, WAREHOUSE_EAST_ID


@pytest.mark.asyncio
async def test_manufacturing_agent_success(db_session):
    agent = ManufacturingAgent(session=db_session)
    state = {
        "workflow_id": str(uuid.uuid4()),
        "correlation_id": str(uuid.uuid4()),
        "order": {
            "order_id": str(uuid.uuid4()),
            "items": [{"product_id": str(PRODUCT_LAPTOP_ID), "quantity": 50}],
        },
        "inventory": {
            str(PRODUCT_LAPTOP_ID): {"status": "out_of_stock"},
        },
        "supplier": {"status": "unavailable"},
        "warehouse": {"warehouse_id": str(WAREHOUSE_EAST_ID)},
    }

    result = await agent.run(state)
    assert result.get("workflow_status") != "failed"
    assert result.get("next_node") == "reporting"
    
    mfg_result = result.get("manufacturing", {})
    assert mfg_result.get("status") == "completed"
    assert len(mfg_result.get("orders", [])) == 1
    assert mfg_result["orders"][0]["planned_qty"] == 50

    # Verify event published (InspectionRequested AUD-49)
    events = [e["event_type"] for e in result.get("event_history", [])]
    assert "ManufacturingStarted" in events
    assert "ManufacturingCompleted" in events
    assert "InspectionRequested" in events


@pytest.mark.asyncio
async def test_manufacturing_capacity_exceeded(db_session):
    agent = ManufacturingAgent(session=db_session)
    state = {
        "workflow_id": str(uuid.uuid4()),
        "order": {
            "order_id": str(uuid.uuid4()),
            "items": [{"product_id": str(PRODUCT_LAPTOP_ID), "quantity": 10000}],  # Exceeds 5000 max capacity
        },
        "inventory": {
            str(PRODUCT_LAPTOP_ID): {"status": "out_of_stock"},
        },
        "warehouse": {"warehouse_id": str(WAREHOUSE_EAST_ID)},
    }

    result = await agent.run(state)
    assert result.get("next_node") == "ceo"
    assert result.get("manufacturing", {}).get("status") == "capacity_exceeded"

    events = [e["event_type"] for e in result.get("event_history", [])]
    assert "CapacityExceeded" in events


@pytest.mark.asyncio
async def test_no_manufacturing_needed():
    agent = ManufacturingAgent(session=None)
    state = {
        "workflow_id": str(uuid.uuid4()),
        "order": {},
        "inventory": {},
    }

    result = await agent.run(state)
    assert result.get("next_node") == "reporting"
