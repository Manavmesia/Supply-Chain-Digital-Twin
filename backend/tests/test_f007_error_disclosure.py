"""
Custom verification test suite for Finding F-007:
Information Disclosure via Raw Exception Strings in Global Exception Handler.
"""
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.config import settings


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_production_mode_masks_raw_internal_exception(monkeypatch):
    """Verify that in production mode, raw exception strings are masked with an opaque message."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    # Define a temporary route that throws an internal error with sensitive paths
    @app.get("/api/v1/test-fault-internal")
    async def throw_fault():
        raise RuntimeError("Internal crash: failed opening /var/secrets/keys/root.key (disk full)")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/test-fault-internal")

    assert resp.status_code == 500
    data = resp.json()
    assert "error_id" in data
    # Ensure raw filesystem paths or exception strings are completely absent
    assert "/var/secrets/keys/root.key" not in data["detail"]
    assert "Internal crash" not in data["detail"]
    assert "internal server error" in data["detail"].lower()
    # Verify error_id format
    val_uuid = uuid.UUID(data["error_id"])
    assert str(val_uuid) == data["error_id"]


@pytest.mark.asyncio
async def test_development_mode_sanitizes_credentials(monkeypatch):
    """Verify that development mode includes exception info but still sanitizes database passwords."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")

    @app.get("/api/v1/test-fault-db")
    async def throw_db_fault():
        raise RuntimeError("Failed to connect: postgresql://admin:super_secret_password@db:5432")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/test-fault-db")

    assert resp.status_code == 500
    data = resp.json()
    assert "error_id" in data
    assert "super_secret_password" not in data["detail"]
    assert data["detail"] == "Database communication error"


@pytest.mark.asyncio
async def test_development_mode_returns_descriptive_error_non_sensitive(monkeypatch):
    """Verify that development mode returns standard debugging errors for non-sensitive faults."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")

    @app.get("/api/v1/test-fault-debug")
    async def throw_debug_fault():
        raise ValueError("Invalid parameter range: value must be between 1 and 100")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/test-fault-debug")

    assert resp.status_code == 500
    data = resp.json()
    assert "error_id" in data
    assert "Invalid parameter range" in data["detail"]
