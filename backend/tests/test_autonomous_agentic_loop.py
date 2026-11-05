"""
Tests for Closed-Loop Autonomous Multi-Agent Remediation and Self-Healing Inventory.
"""

from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.events.dispatcher import dispatch_event_remediation
from app.core import persistence
from app.api.v1.auth import _create_access_token


@pytest.fixture
def auth_headers():
    token = _create_access_token(data={"sub": "admin", "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_dispatch_inventory_low_autonomous_remediation():
    """Test that InventoryLow triggers ADS-03 and ADS-05 to autonomously draft a PO."""
    event_record = {
        "event_id": str(uuid.uuid4()),
        "event_type": "InventoryLow",
        "source_agent": "system_monitor",
        "payload": {
            "sku": "ELEC-001",
            "quantity": 150,
        },
    }

    res = await dispatch_event_remediation(event_record)

    assert res["remediation_status"] == "remediated"
    assert "ADS-03" in res["subscribers"]
    assert "ADS-05" in res["subscribers"]
    assert len(res["autonomous_actions"]) >= 2
    assert "Purchase Order" in res["remediation_summary"]
    assert res["downstream_events_count"] >= 1

    # Verify PO was recorded in persistence
    pos = persistence.list_purchase_orders(limit=5)
    assert len(pos) > 0
    assert any(po["sku"] == "ELEC-001" for po in pos)


@pytest.mark.asyncio
async def test_dispatch_carrier_delay_autonomous_remediation():
    """Test that CarrierDelayed triggers ADS-06 to autonomously reroute freight."""
    event_record = {
        "event_id": str(uuid.uuid4()),
        "event_type": "CarrierDelayed",
        "source_agent": "telematics_sensor",
        "payload": {
            "shipment_id": "SHP-TEST-001",
            "delay_days": 5,
        },
    }

    res = await dispatch_event_remediation(event_record)

    assert res["remediation_status"] == "remediated"
    assert "ADS-06" in res["subscribers"]
    assert any(a["agent"] == "ADS-06" for a in res["autonomous_actions"])
    assert "expedited air" in res["remediation_summary"].lower()


@pytest.mark.asyncio
async def test_dispatch_quality_failure_autonomous_remediation():
    """Test that QualityFailed triggers ADS-14 QA quarantine and ADS-07 Remanufacturing."""
    event_record = {
        "event_id": str(uuid.uuid4()),
        "event_type": "QualityFailed",
        "source_agent": "vision_sensor_line_1",
        "payload": {
            "batch_id": "LOT-992",
            "defect_rate": 0.12,
        },
    }

    res = await dispatch_event_remediation(event_record)

    assert res["remediation_status"] == "remediated"
    assert "ADS-14" in res["subscribers"] or "ADS-07" in res["subscribers"]
    assert any(a["agent"] == "ADS-14" for a in res["autonomous_actions"])
    assert any(a["agent"] == "ADS-07" for a in res["autonomous_actions"])
    assert "quarantined" in res["remediation_summary"].lower()


@pytest.mark.asyncio
async def test_events_api_inject_triggers_autonomous_remediation(auth_headers):
    """Test that injecting an event via API returns autonomous agent actions."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        req_payload = {
            "event_type": "InventoryOutOfStock",
            "source_agent": "warehouse_scanner",
            "payload": {
                "sku": "MECH-001",
                "warehouse_id": "10000000-0000-0000-0000-000000000001",
                "quantity": 200,
            },
        }

        res = await client.post("/api/v1/events", json=req_payload, headers=auth_headers)
        assert res.status_code == 202
        data = res.json()

        assert data["status"] == "remediated"
        assert len(data["autonomous_actions"]) >= 2
        assert "ADS-03" in data["subscribers"]
        assert "Purchase Order" in data["message"]


@pytest.mark.asyncio
async def test_inventory_autonomous_scan_and_auto_heal(auth_headers):
    """Test the autonomous scan and full closed-loop replenishment auto-healing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Run autonomous inventory scan
        scan_res = await client.post("/api/v1/inventory/autonomous-scan", headers=auth_headers)
        assert scan_res.status_code == 200
        scan_data = scan_res.json()
        assert scan_data["status"] == "completed"
        assert "scanned_sku_locations" in scan_data
        assert "autonomous_remediations_executed" in scan_data

        # 2. Auto-heal pending purchase orders
        heal_res = await client.post("/api/v1/inventory/replenish/auto-heal", headers=auth_headers)
        assert heal_res.status_code == 200
        heal_data = heal_res.json()
        assert heal_data["status"] == "completed"
        assert "inventory_summary" in heal_data
