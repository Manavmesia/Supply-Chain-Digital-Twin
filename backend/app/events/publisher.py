"""
EventPublisher — US-66 / EP-14

Publishes domain events to RabbitMQ with:
  - Runtime validation against the canonical event registry
  - Structured AMQP message (routing key = event_type)
  - Idempotency via event_id (UUID)
  - Automatic DB persistence to the events table (append-only)

Usage:
    publisher = EventPublisher(rabbitmq_url=settings.RABBITMQ_URL, session=db_session)
    await publisher.publish(
        event_type="OrderCreated",
        source_agent="ADS-01",
        correlation_id=uuid4(),
        payload={"order_id": str(order.order_id)},
    )
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any, Self

import aio_pika
import structlog
from app.events.registry import CANONICAL_EVENT_NAMES
from app.models.event import Event

logger = structlog.get_logger(__name__)


class UnregisteredEventTypeError(ValueError):
    """Raised when an event_type is not in the canonical registry."""

    def __init__(self, event_type: str) -> None:
        closest = _closest_match(event_type, CANONICAL_EVENT_NAMES)
        hint = f" Did you mean '{closest}'?" if closest else ""
        super().__init__(
            f"Event type '{event_type}' is not registered in the canonical glossary.{hint} "
            f"Add it to app/events/registry.py before publishing."
        )
        self.event_type = event_type


def _closest_match(name: str, candidates: frozenset[str]) -> str | None:
    """Return the candidate with the smallest Levenshtein distance to *name*."""
    if not candidates:
        return None

    def _lev(a: str, b: str) -> int:
        if len(a) < len(b):
            return _lev(b, a)
        if len(b) == 0:
            return len(a)
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a):
            curr = [i + 1]
            for j, cb in enumerate(b):
                curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (ca != cb)))
            prev = curr
        return prev[-1]

    return min(candidates, key=lambda c: _lev(name.lower(), c.lower()))


class EventPublisher:
    """
    Async event publisher.

    Lifecycle:
        1. Validate event_type against registry.
        2. Persist to events table (append-only).
        3. Publish to RabbitMQ exchange.

    The DB write happens before the AMQP publish so that if the broker
    is temporarily unavailable the event is never silently lost — it
    can be replayed from the events table.
    """

    EXCHANGE_NAME = "supply_chain_events"

    def __init__(
        self,
        rabbitmq_url: str,
        session: Any | None = None,     # AsyncSession — optional for unit tests
    ) -> None:
        self._rabbitmq_url = rabbitmq_url
        self._session = session
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None
        self._exchange: aio_pika.abc.AbstractExchange | None = None

    # ── Connection management ────────────────────────────────────────────────

    async def connect(self) -> None:
        """Open a persistent RobustConnection to the broker."""
        self._connection = await aio_pika.connect_robust(self._rabbitmq_url)
        self._channel = await self._connection.channel()
        self._exchange = await self._channel.declare_exchange(
            self.EXCHANGE_NAME,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )
        logger.info("EventPublisher connected", exchange=self.EXCHANGE_NAME)

    async def disconnect(self) -> None:
        """Close connection gracefully."""
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            logger.info("EventPublisher disconnected")

    async def __aenter__(self) -> Self:
        await self.connect()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.disconnect()

    # ── Core publish ─────────────────────────────────────────────────────────

    async def publish(
        self,
        event_type: str,
        source_agent: str,
        correlation_id: uuid.UUID,
        payload: dict[str, Any],
        *,
        target_agent: str | None = None,
        workflow_id: uuid.UUID | None = None,
        priority: str = "medium",
        version: str = "1.0",
        simulation_id: uuid.UUID | None = None,
        event_id: uuid.UUID | None = None,
    ) -> Event:
        """
        Validate, persist, and publish a single event.

        Returns the persisted Event ORM object so callers can inspect
        event_id for idempotency or logging purposes.

        Raises:
            UnregisteredEventTypeError: if event_type is not in the registry.
            RuntimeError: if connect() has not been called.
        """
        # 1. Registry validation (US-66)
        if event_type not in CANONICAL_EVENT_NAMES:
            raise UnregisteredEventTypeError(event_type)

        eid = event_id or uuid.uuid4()
        now = datetime.now(tz=UTC)

        # 2. Persist to events table
        event = Event(
            event_id=eid,
            correlation_id=correlation_id,
            workflow_id=workflow_id,
            event_type=event_type,
            source_agent=source_agent,
            target_agent=target_agent,
            priority=priority,
            version=version,
            payload=payload,
            event_metadata={
                "published_at": now.isoformat(),
                "simulation_id": str(simulation_id) if simulation_id else None,
            },
            simulation_id=simulation_id,
            created_at=now,
        )

        if self._session is not None:
            self._session.add(event)
            await self._session.flush()

        # 3. Publish to AMQP broker
        if self._exchange is None:
            raise RuntimeError(
                "EventPublisher is not connected. Call connect() or use as async context manager."
            )

        body = json.dumps(
            {
                "event_id": str(eid),
                "event_type": event_type,
                "version": version,
                "correlation_id": str(correlation_id),
                "workflow_id": str(workflow_id) if workflow_id else None,
                "simulation_id": str(simulation_id) if simulation_id else None,
                "source_agent": source_agent,
                "target_agent": target_agent,
                "priority": priority,
                "payload": payload,
                "published_at": now.isoformat(),
            }
        ).encode()

        message = aio_pika.Message(
            body=body,
            message_id=str(eid),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            headers={
                "event_type": event_type,
                "source_agent": source_agent,
                "version": version,
            },
        )

        await self._exchange.publish(message, routing_key=event_type)

        logger.info(
            "Event published",
            event_type=event_type,
            event_id=str(eid),
            source_agent=source_agent,
            correlation_id=str(correlation_id),
        )

        return event
