"""
Custom verification test suite for Finding F-012:
Deprecated Logging API and Non-Standard BackgroundTasks Default Parameter Pattern.
"""
import ast
import inspect
import os
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.workflows import approve_workflow
from app.core import persistence
from app.main import app

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_no_deprecated_logger_warn_in_dlq_processor():
    """Verify scripts/dlq_processor.py does not use deprecated logger.warn."""
    dlq_path = os.path.join(BACKEND_DIR, "scripts/dlq_processor.py")
    with open(dlq_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "logger.warn(" not in content, "logger.warn is deprecated, use logger.warning"
    assert "logger.warning(" in content


def test_approve_workflow_signature_no_default_background_tasks():
    """Verify approve_workflow uses standard BackgroundTasks parameter without default instantiation."""
    sig = inspect.signature(approve_workflow)
    param = sig.parameters.get("background_tasks")
    assert param is not None, "background_tasks parameter must be present"
    assert param.default is inspect.Parameter.empty, "background_tasks should not have default value = BackgroundTasks()"


@pytest.mark.asyncio
async def test_approve_workflow_accepts_background_task_properly():
    """Verify approving an escalated workflow functions seamlessly with FastAPI dependency injection."""
    # Seed an escalated workflow in persistence
    wf_id = "wf-escalated-test-01"
    persistence.save_workflow(wf_id, {
        "workflow_id": wf_id,
        "workflow_status": "paused_for_approval",
        "current_node": "human_approval",
    })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login as admin
        login_res = await client.post(
            "/api/v1/auth/token",
            data={"username": "admin", "password": "admin123"},
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            f"/api/v1/workflows/{wf_id}/approve",
            json={"notes": "Approved in automated test"},
            headers=headers,
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "resumed"
        assert data["workflow_id"] == wf_id
