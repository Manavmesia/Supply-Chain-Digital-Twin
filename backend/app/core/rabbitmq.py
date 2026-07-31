"""
RabbitMQ connection management — shared infrastructure for Phase 3.

Provides:
  - ``get_rabbitmq_publisher`` — FastAPI dependency that yields a connected
    EventPublisher and disconnects on teardown.
  - ``BaseConsumer`` — async base class for agent event consumers.
  - ``connect_rabbitmq`` / ``disconnect_rabbitmq`` — app lifespan helpers.
"""

from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from typing import Any

import aio_pika
import structlog

from app.core.config import settings
from app.events.publisher import EventPublisher

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Module-level publisher singleton (owned by the FastAPI lifespan)
# ---------------------------------------------------------------------------

_publisher: EventPublisher | None = None


async def connect_rabbitmq() -> None:
    """Connect the module-level publisher.  Called from app lifespan startup."""
    global _publisher  # noqa: PLW0603
    _publisher = EventPublisher(rabbitmq_url=settings.RABBITMQ_URL)
    await _publisher.connect()
    logger.info("RabbitMQ publisher connected")


async def disconnect_rabbitmq() -> None:
    """Disconnect the module-level publisher.  Called from app lifespan shutdown."""
    global _publisher  # noqa: PLW0603
    if _publisher is not None:
        await _publisher.disconnect()
        _publisher = None
        logger.info("RabbitMQ publisher disconnected")


async def get_rabbitmq_publisher() -> EventPublisher:
    """FastAPI dependency — returns the shared connected publisher.

    Usage::

        @router.post("/orders")
        async def create_order(publisher: EventPublisher = Depends(get_rabbitmq_publisher)):
            await publisher.publish(event_type="OrderCreated", ...)
    """
    if _publisher is None:
        raise RuntimeError(
            "RabbitMQ publisher is not connected. "
            "Ensure connect_rabbitmq() is called during application startup."
        )
    return _publisher


# ---------------------------------------------------------------------------
# Base consumer — agents extend this to subscribe to events
# ---------------------------------------------------------------------------


class BaseConsumer(ABC):
    """
    Async base class for RabbitMQ consumers.

    Subclass and implement ``handle_message`` to process incoming events.

    Example::

        class OrderCreatedConsumer(BaseConsumer):
            QUEUE_NAME = "ads01.order_created"
            ROUTING_KEYS = ["OrderCreated"]

            async def handle_message(self, event_type: str, payload: dict) -> None:
                await self.order_service.process(payload)
    """

    #: Override in subclass — the durable queue name for this consumer
    QUEUE_NAME: str = ""
    #: Override in subclass — list of routing keys to bind
    ROUTING_KEYS: list[str] = []
    #: Exchange name must match EventPublisher
    EXCHANGE_NAME: str = "supply_chain_events"

    def __init__(self, rabbitmq_url: str = settings.RABBITMQ_URL) -> None:
        self._rabbitmq_url = rabbitmq_url
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None
        self._queue: aio_pika.abc.AbstractQueue | None = None
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Connect to RabbitMQ, declare queue/bindings, and start consuming."""
        if not self.QUEUE_NAME:
            raise ValueError(f"{self.__class__.__name__}.QUEUE_NAME must be set")
        if not self.ROUTING_KEYS:
            raise ValueError(f"{self.__class__.__name__}.ROUTING_KEYS must be set")

        self._connection = await aio_pika.connect_robust(self._rabbitmq_url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=10)

        exchange = await self._channel.declare_exchange(
            self.EXCHANGE_NAME,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )

        self._queue = await self._channel.declare_queue(
            self.QUEUE_NAME,
            durable=True,
            arguments={"x-dead-letter-exchange": "supply_chain_dlq"},
        )

        for routing_key in self.ROUTING_KEYS:
            await self._queue.bind(exchange, routing_key=routing_key)

        logger.info(
            "Consumer started",
            queue=self.QUEUE_NAME,
            routing_keys=self.ROUTING_KEYS,
        )

        self._task = asyncio.create_task(self._consume())

    async def stop(self) -> None:
        """Cancel the consumer task and close the connection."""
        if self._task is not None:
            self._task.cancel()
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
        logger.info("Consumer stopped", queue=self.QUEUE_NAME)

    async def _consume(self) -> None:
        if self._queue is None:
            return
        async with self._queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process(requeue=False):
                    try:
                        body: dict[str, Any] = json.loads(message.body.decode())
                        event_type: str = body.get("event_type", "")
                        payload: dict[str, Any] = body.get("payload", {})
                        await self.handle_message(event_type=event_type, payload=body)
                    except Exception:  # noqa: BLE001
                        logger.exception(
                            "Consumer failed to process message",
                            queue=self.QUEUE_NAME,
                            routing_key=message.routing_key,
                        )

    @abstractmethod
    async def handle_message(self, event_type: str, payload: dict[str, Any]) -> None:
        """Process a single incoming event message.

        Args:
            event_type: The canonical event type string from the message body.
            payload:    The full deserialized message body (includes event_id,
                        correlation_id, payload sub-dict, etc.).
        """
