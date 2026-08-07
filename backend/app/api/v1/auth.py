"""
Auth API — Phase 2 / Security

POST /api/v1/auth/token  — issue a JWT bearer token
GET  /api/v1/auth/me     — return the current user's profile

Uses a simple hardcoded user store for development.
In production, replace with a real user table + bcrypt.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Dev user store — replace with DB in production
# ---------------------------------------------------------------------------

_DEV_USERS: dict[str, dict[str, Any]] = {
    "admin": {
        "username": "admin",
        "password": "admin123",          # plaintext — dev only
        "role": "admin",
        "full_name": "System Administrator",
    },
    "viewer": {
        "username": "viewer",
        "password": "viewer123",
        "role": "viewer",
        "full_name": "Dashboard Viewer",
    },
    "analyst": {
        "username": "analyst",
        "password": "analyst123",
        "role": "analyst",
        "full_name": "Supply Chain Analyst",
    },
}

# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")


def _create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(tz=timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def _decode_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> dict[str, Any]:
    payload = _decode_token(token)
    username: str | None = payload.get("sub")
    if username is None or username not in _DEV_USERS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _DEV_USERS[username]


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str
    username: str


class UserProfile(BaseModel):
    username: str
    full_name: str
    role: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Issue JWT access token",
)
async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()]) -> TokenResponse:
    """
    Authenticate with username + password and receive a JWT bearer token.

    **Development credentials:**
    - `admin` / `admin123`
    - `analyst` / `analyst123`
    - `viewer` / `viewer123`
    """
    user = _DEV_USERS.get(form.username)
    if user is None or user["password"] != form.password:
        logger.warning("Failed login attempt", username=form.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    token = _create_access_token(
        {"sub": user["username"], "role": user["role"]},
        expires_delta=timedelta(minutes=expire_minutes),
    )

    logger.info("Login successful", username=user["username"], role=user["role"])

    return TokenResponse(
        access_token=token,
        expires_in=expire_minutes * 60,
        role=user["role"],
        username=user["username"],
    )


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Get current user profile",
)
async def get_me(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> UserProfile:
    """Return the profile of the currently authenticated user."""
    return UserProfile(
        username=current_user["username"],
        full_name=current_user["full_name"],
        role=current_user["role"],
    )
