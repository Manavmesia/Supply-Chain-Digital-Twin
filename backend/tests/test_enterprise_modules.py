"""
Tests for Enterprise Modules: TMS Logistics, SRM Procurement, and OMS Commercial Orders.
"""

from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.api.v1.auth import _create_access_token
from app.core import persistence


@pytest.fixture
def auth_headers():
    token = _create_access_token(data={"sub": "admin", "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_shipments_tms_lifecycle(auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. List shipments
        res = await ac.get("/api/v1/shipments")
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert data["total"] >= 1
        first_shp = data["items"][0]
        shp_id = first_shp["shipment_id"]

        # 2. Get stats
        stats_res = await ac.get("/api/v1/shipments/stats")
        assert stats_res.status_code == 200
        stats = stats_res.json()
        assert "total_shipments" in stats
        assert "on_time_rate_pct" in stats

        # 3. Update status to delayed -> triggers DeliveryDelayed event
        delay_res = await ac.post(
            f"/api/v1/shipments/{shp_id}/status",
            json={
                "status": "delayed",
                "current_location": "Midwest Junction",
                "delay_reason": "Severe blizzard conditions",
            },
            headers=auth_headers,
        )
        assert delay_res.status_code == 200
        delay_data = delay_res.json()
        assert delay_data["shipment"]["status"] == "delayed"
        assert delay_data["autonomous_remediation_event"] is not None

        # 4. Reroute shipment to air freight
        reroute_res = await ac.post(
            f"/api/v1/shipments/{shp_id}/reroute",
            json={
                "new_freight_mode": "air",
                "new_carrier": "FedEx Priority Air Cargo",
                "reason": "Bypassing blizzard corridor",
            },
            headers=auth_headers,
        )
        assert reroute_res.status_code == 200
        rerouted = reroute_res.json()
        assert rerouted["success"] is True
        assert rerouted["shipment"]["freight_mode"] == "air"


@pytest.mark.asyncio
async def test_procurement_srm_stock_receipt(auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. List POs
        res = await ac.get("/api/v1/procurement/orders")
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert len(data["items"]) >= 1

        # 2. Create new PO
        new_po_res = await ac.post(
            "/api/v1/procurement/orders",
            json={
                "supplier_id": "sup00000-0000-0000-0000-000000000001",
                "product_id": "30000000-0000-0000-0000-000000000001",
                "warehouse_id": "10000000-0000-0000-0000-000000000001",
                "quantity": 120,
                "unit_cost": 115.5,
                "lead_time_days": 3,
            },
            headers=auth_headers,
        )
        assert new_po_res.status_code == 201
        po_id = new_po_res.json()["po_id"]

        # 3. 1-Click Receive Stock
        recv_res = await ac.post(
            f"/api/v1/procurement/orders/{po_id}/receive",
            headers=auth_headers,
        )
        assert recv_res.status_code == 200
        recv_data = recv_res.json()
        assert recv_data["success"] is True
        assert recv_data["details"]["status"] == "received"
        assert recv_data["details"]["quantity_replenished"] == 120


@pytest.mark.asyncio
async def test_commercial_order_creation_oms(auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/orders",
            json={
                "customer_id": "cust0000-0000-0000-0000-000000000001",
                "items": [
                    {
                        "product_id": "30000000-0000-0000-0000-000000000001",
                        "quantity": 25,
                    }
                ],
                "priority": "high",
            },
            headers=auth_headers,
        )
        assert res.status_code == 201
        order = res.json()
        assert "order_id" in order
        assert "workflow_id" in order
        assert "shipment_id" in order
        assert float(order["total_amount"]) > 0
