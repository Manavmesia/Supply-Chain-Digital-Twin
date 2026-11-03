"""Tests for persistent storage of workflows, simulations, orders, and events."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core import persistence


@pytest.mark.asyncio
async def test_workflows_persistence_and_listing():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create a workflow
        res = await ac.post(
            "/api/v1/workflows/orders",
            json={
                "customer_id": "00000000-0000-0000-0000-000000000001",
                "items": [{"product_id": "00000000-0000-0000-0000-000000000002", "quantity": 5}],
            },
        )
        assert res.status_code == 202
        wf_id = res.json()["workflow_id"]

        # Verify it can be listed via GET /api/v1/workflows
        list_res = await ac.get("/api/v1/workflows")
        assert list_res.status_code == 200
        data = list_res.json()
        assert "items" in data
        assert any(w["workflow_id"] == wf_id for w in data["items"])

        # Fetch status
        status_res = await ac.get(f"/api/v1/workflows/{wf_id}")
        assert status_res.status_code == 200
        assert status_res.json()["workflow_id"] == wf_id

        # Verify trace endpoint
        trace_res = await ac.get(f"/api/v1/workflows/{wf_id}/trace")
        assert trace_res.status_code == 200


@pytest.mark.asyncio
async def test_simulations_persistence_and_listing():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Launch simulation
        res = await ac.post(
            "/api/v1/simulate",
            json={
                "scenario_type": "demand_spike",
                "customer_id": "00000000-0000-0000-0000-000000000001",
                "items": [{"product_id": "00000000-0000-0000-0000-000000000002", "quantity": 10}],
            },
        )
        assert res.status_code == 202
        sim_id = res.json()["simulation_id"]

        # List simulations
        list_res = await ac.get("/api/v1/simulate")
        assert list_res.status_code == 200
        sims = list_res.json()["items"]
        assert any(s["simulation_id"] == sim_id for s in sims)

        # Get simulation detail
        detail_res = await ac.get(f"/api/v1/simulate/{sim_id}")
        assert detail_res.status_code == 200


@pytest.mark.asyncio
async def test_orders_and_dashboard_persistence():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        orders_res = await ac.get("/api/v1/orders")
        assert orders_res.status_code == 200
        orders_data = orders_res.json()
        assert "items" in orders_data
        assert orders_data["total"] >= 4

        dash_res = await ac.get("/api/v1/analytics/dashboard")
        assert dash_res.status_code == 200
        dash_data = dash_res.json()
        assert "kpis" in dash_data
        assert "recent_orders" in dash_data
