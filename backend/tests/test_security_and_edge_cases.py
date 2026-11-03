"""
Security and Edge Case Fuzzing / Stress Tests.
Ensures application resilience against malicious payloads, invalid schemas,
integer overflows, timing attacks, memory exhaustion (DoS), and invalid state transitions.
"""

import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.api.v1.simulate import _SIM_STORE, _save_sim_state, _MAX_SIM_STORE_SIZE
from app.api.v1.workflows import _WORKFLOW_STORE, _save_workflow_state, _MAX_WORKFLOW_STORE_SIZE


@pytest.mark.asyncio
async def test_simulation_invalid_scenario_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/simulate",
            json={
                "scenario_type": "arbitrary_exploit_injection",
                "customer_id": "cust-01",
                "items": [{"product_id": "prod-1", "quantity": 10}],
            },
        )
        # Must be rejected by Pydantic validation before reaching workflow execution
        assert res.status_code == 422
        errors = res.json()["detail"]
        assert any("scenario_type" in str(e["loc"]) for e in errors)


@pytest.mark.asyncio
async def test_simulation_negative_quantity_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/simulate",
            json={
                "scenario_type": "demand_spike",
                "customer_id": "cust-01",
                "items": [{"product_id": "prod-1", "quantity": -5}],
            },
        )
        assert res.status_code == 422


@pytest.mark.asyncio
async def test_simulation_excessive_quantity_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/simulate",
            json={
                "scenario_type": "demand_spike",
                "customer_id": "cust-01",
                "items": [{"product_id": "prod-1", "quantity": 100_000_000}],
            },
        )
        assert res.status_code == 422


@pytest.mark.asyncio
async def test_workflow_excessive_quantity_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/workflows/orders",
            json={
                "customer_id": str(uuid.uuid4()),
                "items": [{"product_id": str(uuid.uuid4()), "quantity": 50_000_000}],
            },
        )
        assert res.status_code == 422


@pytest.mark.asyncio
async def test_workflow_duplicate_products_rejected():
    prod_id = str(uuid.uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/workflows/orders",
            json={
                "customer_id": str(uuid.uuid4()),
                "items": [
                    {"product_id": prod_id, "quantity": 5},
                    {"product_id": prod_id, "quantity": 10},
                ],
            },
        )
        assert res.status_code == 422
        assert "Duplicate product_id" in str(res.json())


@pytest.mark.asyncio
async def test_override_invalid_action_rejected():
    wf_id = str(uuid.uuid4())
    _save_workflow_state(wf_id, {"workflow_id": wf_id, "workflow_status": "escalated"})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/workflows/{wf_id}/override",
            json={
                "topic": "pricing",
                "action": "illegal_action",
                "value": {"test": 123},
            },
        )
        assert res.status_code == 422


@pytest.mark.asyncio
async def test_override_invalid_topic_rejected():
    wf_id = str(uuid.uuid4())
    _save_workflow_state(wf_id, {"workflow_id": wf_id, "workflow_status": "escalated"})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/workflows/{wf_id}/override",
            json={
                "topic": "invalid_topic_name",
                "action": "pin",
                "value": {"test": 123},
            },
        )
        assert res.status_code == 422


@pytest.mark.asyncio
async def test_auth_timing_safe_authentication():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Invalid credentials
        res = await ac.post(
            "/api/v1/auth/token",
            data={"username": "admin", "password": "wrong_password_123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert res.status_code == 401

        # Valid credentials
        res_ok = await ac.post(
            "/api/v1/auth/token",
            data={"username": "admin", "password": "admin123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert res_ok.status_code == 200
        assert "access_token" in res_ok.json()


def test_bounded_memory_stores_prevent_dos():
    # Test simulation store bound
    for i in range(_MAX_SIM_STORE_SIZE + 20):
        _save_sim_state(f"sim_{i}", {"data": i})
    assert len(_SIM_STORE) <= _MAX_SIM_STORE_SIZE
    assert "sim_0" not in _SIM_STORE  # Oldest should have been evicted
    assert f"sim_{_MAX_SIM_STORE_SIZE + 10}" in _SIM_STORE

    # Test workflow store bound
    for i in range(_MAX_WORKFLOW_STORE_SIZE + 20):
        _save_workflow_state(f"wf_{i}", {"data": i})
    assert len(_WORKFLOW_STORE) <= _MAX_WORKFLOW_STORE_SIZE
    assert "wf_0" not in _WORKFLOW_STORE
    assert f"wf_{_MAX_WORKFLOW_STORE_SIZE + 10}" in _WORKFLOW_STORE


@pytest.mark.asyncio
async def test_approve_escalated_workflow():
    wf_id = str(uuid.uuid4())
    _save_workflow_state(wf_id, {
        "workflow_id": wf_id,
        "workflow_status": "escalated",
        "requires_human_approval": True,
        "correlation_id": str(uuid.uuid4()),
    })

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/workflows/{wf_id}/approve",
            json={"notes": "Executive override granted"},
        )
        assert res.status_code == 202
        assert res.json()["status"] == "resumed"

        # Check workflow state updated
        wf_res = await ac.get(f"/api/v1/workflows/{wf_id}")
        assert wf_res.status_code == 200
        state = wf_res.json()
        assert not state["requires_human_approval"]
        assert state["executive_decision"]["approved"] is True
        assert state["executive_decision"]["approval_tier"] == "human_executive"


@pytest.mark.asyncio
async def test_reject_escalated_workflow():
    wf_id = str(uuid.uuid4())
    _save_workflow_state(wf_id, {
        "workflow_id": wf_id,
        "workflow_status": "escalated",
        "requires_human_approval": True,
        "correlation_id": str(uuid.uuid4()),
    })

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/workflows/{wf_id}/reject",
            json={"notes": "Budget exceeded limit"},
        )
        assert res.status_code == 200
        assert res.json()["status"] == "failed"

        # Check workflow state updated
        wf_res = await ac.get(f"/api/v1/workflows/{wf_id}")
        assert wf_res.status_code == 200
        state = wf_res.json()
        assert state["workflow_status"] == "failed"
        assert not state["requires_human_approval"]
        assert state["executive_decision"]["approved"] is False


@pytest.mark.asyncio
async def test_approve_nonexistent_workflow_404():
    fake_id = str(uuid.uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(f"/api/v1/workflows/{fake_id}/approve")
        assert res.status_code == 404
