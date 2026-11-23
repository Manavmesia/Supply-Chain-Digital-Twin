"""
Custom verification test suite for Finding F-010:
Unhandled ValidationError in Commercial Order Intake Handler Returns 500 Server Error.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core import persistence
from app.api.v1.auth import hash_password
from app.core.catalog import BASELINE_PRODUCTS, BASELINE_CUSTOMERS


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_duplicate_product_ids_return_http_422():
    """Verify that submitting duplicate product IDs returns HTTP 422 instead of crashing with HTTP 500."""
    persistence.save_user({
        "username": "test_operator",
        "password_hash": hash_password("test_pass"),
        "role": "operator",
        "full_name": "Test Operator",
        "is_active": True,
    })

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Obtain auth token
        login_res = await client.post(
            "/api/v1/auth/token",
            data={"username": "test_operator", "password": "test_pass"},
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        prod_id = BASELINE_PRODUCTS[0][0]
        payload = {
            "customer_id": BASELINE_CUSTOMERS[0][0],
            "items": [
                {"product_id": prod_id, "quantity": 5},
                {"product_id": prod_id, "quantity": 10},
            ],
            "priority": "standard",
        }

        resp = await client.post("/api/v1/orders", json=payload, headers=headers)
        # MUST return 422, NEVER 500
        assert resp.status_code == 422, f"Expected 422 for duplicate items, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "duplicate product_id" in str(data).lower()


@pytest.mark.asyncio
async def test_case_insensitive_duplicate_product_ids_return_http_422():
    """Verify that duplicate product IDs in different cases return HTTP 422."""
    persistence.save_user({
        "username": "test_operator2",
        "password_hash": hash_password("test_pass"),
        "role": "operator",
        "full_name": "Test Operator 2",
        "is_active": True,
    })

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_res = await client.post(
            "/api/v1/auth/token",
            data={"username": "test_operator2", "password": "test_pass"},
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        raw_id = "10000000-0000-0000-0000-000000000001"
        payload = {
            "customer_id": BASELINE_CUSTOMERS[0][0],
            "items": [
                {"product_id": raw_id.lower(), "quantity": 2},
                {"product_id": raw_id.upper(), "quantity": 4},
            ],
            "priority": "standard",
        }

        resp = await client.post("/api/v1/orders", json=payload, headers=headers)
        assert resp.status_code == 422
        assert "duplicate product_id" in str(resp.json()).lower()


@pytest.mark.asyncio
async def test_distinct_product_ids_return_http_201():
    """Verify that submitting distinct product IDs succeeds with HTTP 201."""
    persistence.save_user({
        "username": "test_operator3",
        "password_hash": hash_password("test_pass"),
        "role": "operator",
        "full_name": "Test Operator 3",
        "is_active": True,
    })

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_res = await client.post(
            "/api/v1/auth/token",
            data={"username": "test_operator3", "password": "test_pass"},
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "customer_id": BASELINE_CUSTOMERS[0][0],
            "items": [
                {"product_id": BASELINE_PRODUCTS[0][0], "quantity": 2},
                {"product_id": BASELINE_PRODUCTS[1][0], "quantity": 3},
            ],
            "priority": "standard",
        }

        resp = await client.post("/api/v1/orders", json=payload, headers=headers)
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "order_id" in data
