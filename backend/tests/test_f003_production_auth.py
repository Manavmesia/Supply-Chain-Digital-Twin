"""
Test suite for F-003: Verification that production mode authentication works
seamlessly against persistent storage without lockout.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings
from app.core import persistence
from app.api.v1.auth import hash_password, _DEV_USERS


@pytest.mark.asyncio
async def test_production_mode_login_succeeds_with_persistent_user(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    # In production, _DEV_USERS is empty
    monkeypatch.setattr("app.api.v1.auth._DEV_USERS", {})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Login with persistent admin
        res = await client.post(
            "/api/v1/auth/token",
            data={"username": "admin", "password": "admin123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert res.status_code == 200, f"Production login failed: {res.text}"
        data = res.json()
        assert "access_token" in data
        assert data["role"] == "admin"
        token = data["access_token"]

        # 2. Access /auth/me with the token
        me_res = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_res.status_code == 200
        me_data = me_res.json()
        assert me_data["username"] == "admin"
        assert me_data["role"] == "admin"


@pytest.mark.asyncio
async def test_production_mode_custom_created_user_authentication(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr("app.api.v1.auth._DEV_USERS", {})

    # Create a new production operator in persistent storage
    pwd_hash = hash_password("SecurePass456!")
    persistence.save_user({
        "username": "prod_operator",
        "password_hash": pwd_hash,
        "role": "operator",
        "full_name": "Production Operations Lead",
        "is_active": True,
    })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Invalid password rejected
        bad_res = await client.post(
            "/api/v1/auth/token",
            data={"username": "prod_operator", "password": "WrongPassword"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert bad_res.status_code == 401

        # Valid password authenticated
        good_res = await client.post(
            "/api/v1/auth/token",
            data={"username": "prod_operator", "password": "SecurePass456!"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert good_res.status_code == 200
        token = good_res.json()["access_token"]

        # Verify access to protected route with role operator
        order_res = await client.post(
            "/api/v1/workflows/orders",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "customer_id": "50000000-0000-0000-0000-000000000001",
                "items": [{"product_id": "30000000-0000-0000-0000-000000000001", "quantity": 1}],
            },
        )
        assert order_res.status_code == 202
