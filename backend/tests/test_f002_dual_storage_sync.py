"""
Test suite for F-002: Dual-storage split brain and synchronization validation.
Ensures that records created via write endpoints are immediately observable
on listing endpoints under both persistent SQLite and mock/live database sessions.
"""

import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core import persistence


@pytest.mark.asyncio
async def test_order_creation_synchronization_and_visibility():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create an order
        prod_id = "30000000-0000-0000-0000-000000000001"
        cust_id = "50000000-0000-0000-0000-000000000001"
        res = await client.post(
            "/api/v1/orders",
            json={
                "customer_id": cust_id,
                "priority": "critical",
                "items": [{"product_id": prod_id, "quantity": 15}],
            },
        )
        assert res.status_code == 201
        created = res.json()
        order_id = created["order_id"]
        assert order_id.startswith("ord-")

        # Verify immediately visible in list_orders
        list_res = await client.get("/api/v1/orders")
        assert list_res.status_code == 200
        orders_data = list_res.json()
        order_ids = [o["order_id"] for o in orders_data["items"]]
        assert order_id in order_ids, f"Order {order_id} missing from list_orders"

        # Verify detail endpoint
        detail_res = await client.get(f"/api/v1/orders/{order_id}")
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["order_id"] == order_id
        assert detail["priority"] == "critical"


@pytest.mark.asyncio
async def test_shipment_creation_synchronization_and_visibility():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Dispatch a shipment
        res = await client.post(
            "/api/v1/shipments",
            json={
                "origin": "Munich Central DC",
                "destination": "London Terminal",
                "carrier": "EuroLogistics Rapid",
                "freight_mode": "road",
            },
        )
        assert res.status_code == 201
        shp = res.json()
        shp_id = shp["shipment_id"]

        # Verify immediately visible in list_shipments
        list_res = await client.get("/api/v1/shipments")
        assert list_res.status_code == 200
        shipments_data = list_res.json()
        shipment_ids = [s["shipment_id"] for s in shipments_data["items"]]
        assert shp_id in shipment_ids, f"Shipment {shp_id} missing from list_shipments"

        # Verify detail
        detail_res = await client.get(f"/api/v1/shipments/{shp_id}")
        assert detail_res.status_code == 200
        assert detail_res.json()["shipment_id"] == shp_id
