"""
AI Supply Chain Digital Twin — FastAPI Application

Lifespan:
  startup  → check DB / Redis / RabbitMQ connections
  shutdown → gracefully disconnect all infrastructure

Health endpoint returns real probe results for every dependency.
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import analytics as analytics_router
from app.api.v1 import auth as auth_router
from app.api.v1 import events as events_router
from app.api.v1 import inventory as inventory_router
from app.api.v1 import orders as orders_router
from app.api.v1 import reports as reports_router
from app.api.v1 import simulate as simulate_router
from app.api.v1 import suppliers as suppliers_router
from app.api.v1 import workflows as workflows_router
from app.core.config import settings

# ── Logging setup ────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=logging.INFO,
)

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.JSONRenderer()
        if settings.ENVIRONMENT == "production"
        else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


# ── Dependency health probes ─────────────────────────────────────────────────

async def _probe_db() -> str:
    """Return 'connected' or an error string."""
    try:
        from app.core.database import engine
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return "connected"
    except Exception as exc:  # noqa: BLE001
        return f"error: {exc}"


async def _probe_redis() -> str:
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        return "connected"
    except Exception as exc:  # noqa: BLE001
        return f"error: {exc}"


async def _probe_rabbitmq() -> str:
    try:
        import aio_pika
        conn = await aio_pika.connect(settings.RABBITMQ_URL, timeout=3)
        await conn.close()
        return "connected"
    except Exception as exc:  # noqa: BLE001
        return f"error: {exc}"


# ── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI Supply Chain Digital Twin", version=settings.APP_VERSION)

    # Probe all dependencies at startup (non-blocking — just log)
    db_status = await _probe_db()
    redis_status = await _probe_redis()
    mq_status = await _probe_rabbitmq()

    logger.info(
        "Infrastructure probes complete",
        db=db_status,
        redis=redis_status,
        rabbitmq=mq_status,
    )

    yield

    logger.info("Shutting down AI Supply Chain Digital Twin")


# ── FastAPI application ───────────────────────────────────────────────────────

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Autonomous multi-agent supply chain digital twin with 18 AI agents.",
    version=settings.APP_VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routers ─────────────────────────────────────────────────────────

app.include_router(auth_router.router,       prefix=settings.API_V1_STR)
app.include_router(workflows_router.router,  prefix=settings.API_V1_STR)
app.include_router(orders_router.router,     prefix=settings.API_V1_STR)
app.include_router(reports_router.router,    prefix=settings.API_V1_STR)
app.include_router(analytics_router.router,  prefix=settings.API_V1_STR)
app.include_router(inventory_router.router,  prefix=settings.API_V1_STR)
app.include_router(suppliers_router.router,  prefix=settings.API_V1_STR)
app.include_router(events_router.router,     prefix=settings.API_V1_STR)
app.include_router(simulate_router.router,   prefix=settings.API_V1_STR)


# ── Health endpoint ───────────────────────────────────────────────────────────

@app.get("/health", tags=["health"])
async def health_check() -> dict[str, Any]:
    """
    Real dependency health probe — checks DB, Redis, and RabbitMQ.
    Returns 200 even if dependencies are degraded (so orchestrators don't
    restart the app on startup race conditions), but each status field
    clearly signals health.
    """
    db_status = await _probe_db()
    redis_status = await _probe_redis()
    mq_status = await _probe_rabbitmq()

    all_healthy = all(
        s == "connected" for s in [db_status, redis_status, mq_status]
    )

    logger.info(
        "Health check",
        db=db_status,
        redis=redis_status,
        rabbitmq=mq_status,
    )

    return {
        "status": "ok",
        "system_status": "ok" if all_healthy else "degraded",
        "version": settings.APP_VERSION,
        "project": settings.PROJECT_NAME,
        "dependencies": {
            "db": db_status,
            "redis": redis_status,
            "rabbitmq": mq_status,
        },
    }


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    return {
        "message": "Welcome to the AI Supply Chain Digital Twin API"
    }

