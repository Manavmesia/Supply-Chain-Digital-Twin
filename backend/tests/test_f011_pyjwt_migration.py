"""
Custom verification test suite for Finding F-011:
Use of Unmaintained and Vulnerable python-jose Cryptographic Library.
"""
from datetime import timedelta
import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import HTTPException
import jwt

from app.api.v1 import auth
from app.core.config import settings
from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_no_python_jose_in_backend_code():
    """Verify python-jose is not imported in backend/app."""
    import sys
    assert "jose" not in sys.modules, "jose should not be imported"
    import os
    pyproject_path = "backend/pyproject.toml" if os.path.exists("backend/pyproject.toml") else "pyproject.toml"
    with open(pyproject_path, "r", encoding="utf-8") as f:
        manifest = f.read()
    assert "python-jose" not in manifest
    assert "pyjwt" in manifest


def test_token_creation_and_decoding_with_pyjwt():
    """Verify PyJWT generates and decodes tokens accurately."""
    payload = {"sub": "test_user", "role": "admin"}
    token = auth._create_access_token(payload, expires_delta=timedelta(minutes=15))
    assert isinstance(token, str)
    
    decoded = auth._decode_token(token)
    assert decoded["sub"] == "test_user"
    assert decoded["role"] == "admin"
    assert "exp" in decoded


def test_expired_token_rejected():
    """Verify that an expired token raises HTTPException 401."""
    payload = {"sub": "expired_user", "role": "viewer"}
    token = auth._create_access_token(payload, expires_delta=timedelta(seconds=-10))
    with pytest.raises(HTTPException) as exc_info:
        auth._decode_token(token)
    assert exc_info.value.status_code == 401


def test_tampered_token_signature_rejected():
    """Verify token signature validation rejects altered tokens."""
    token = auth._create_access_token({"sub": "legit", "role": "viewer"})
    parts = token.split(".")
    # Tamper payload
    tampered_token = f"{parts[0]}.eyAiaW52YWxpZCI6IHRydWUgfQ.{parts[2]}"
    with pytest.raises(HTTPException) as exc_info:
        auth._decode_token(tampered_token)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_full_auth_endpoint_roundtrip_with_pyjwt():
    """Verify end-to-end auth login and protected endpoint authorization."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login
        login_res = await client.post(
            "/api/v1/auth/token",
            data={"username": "admin", "password": "admin123"},
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        assert isinstance(token, str)

        # Authenticated query
        me_res = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_res.status_code == 200
        assert me_res.json()["username"] == "admin"
