"""
Test suite for F-001: Verification of authentication and role gating on
POST /api/v1/workflows/orders and POST /api/v1/simulate.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings
from app.api.v1.auth import _create_access_token


@pytest.mark.asyncio
async def test_workflows_orders_unauthenticated_in_production(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/workflows/orders",
            json={
                "customer_id": "50000000-0000-0000-0000-000000000001",
                "items": [{"product_id": "30000000-0000-0000-0000-000000000001", "quantity": 1}],
            },
        )
        assert res.status_code == 401
        assert "not provided" in res.json().get("detail", "").lower()


@pytest.mark.asyncio
async def test_simulate_unauthenticated_in_production(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/simulate",
            json={
                "scenario_type": "demand_spike",
                "customer_id": "50000000-0000-0000-0000-000000000001",
                "items": [{"product_id": "30000000-0000-0000-0000-000000000001", "quantity": 1}],
            },
        )
        assert res.status_code == 401
        assert "not provided" in res.json().get("detail", "").lower()


@pytest.mark.asyncio
async def test_simulate_forbidden_role(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    # Generate token for role 'viewer' (not in 'admin', 'analyst')
    viewer_token = _create_access_token({"sub": "viewer", "role": "viewer"})

    # Temporarily ensure viewer user is resolvable in dev store for test
    from app.api.v1 import auth
    monkeypatch.setitem(auth._DEV_USERS, "viewer", {"username": "viewer", "role": "viewer", "full_name": "Viewer"})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/simulate",
            headers={"Authorization": f"Bearer {viewer_token}"},
            json={
                "scenario_type": "demand_spike",
                "customer_id": "50000000-0000-0000-0000-000000000001",
                "items": [{"product_id": "30000000-0000-0000-0000-000000000001", "quantity": 1}],
            },
        )
        assert res.status_code == 403
        assert "requires one of the following roles" in res.json().get("detail", "")


@pytest.mark.asyncio
async def test_workflows_orders_authenticated_success(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    from app.core import persistence
    from app.api.v1.auth import hash_password
    persistence.save_user({
        "username": "operator_test",
        "password_hash": hash_password("pass123"),
        "role": "operator",
        "full_name": "Test Operator",
        "is_active": True,
    })
    operator_token = _create_access_token({"sub": "operator_test", "role": "operator"})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/workflows/orders",
            headers={"Authorization": f"Bearer {operator_token}"},
            json={
                "customer_id": "50000000-0000-0000-0000-000000000001",
                "items": [{"product_id": "30000000-0000-0000-0000-000000000001", "quantity": 1}],
            },
        )
        assert res.status_code == 202
        data = res.json()
        assert "workflow_id" in data
