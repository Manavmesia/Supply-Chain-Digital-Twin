"""
Dead-Letter Queue (DLQ) Processor
=================================
Processes failed messages from the RabbitMQ DLQ exchange:
  - Establishes a connection to RabbitMQ
  - Declares the 'supply_chain_dlq' exchange
  - Declares and binds the 'supply_chain_dlq_queue'
  - Consumes messages, logs error/exception details
  - Re-routes/retries or archives the failed events

Run:
    python3 backend/scripts/dlq_processor.py
"""

from __future__ import annotations

import asyncio
import json
import sys

# Ensure app modules are importable
sys.path.insert(0, "")
sys.path.insert(0, "backend")

import aio_pika
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

DLQ_EXCHANGE_NAME = "supply_chain_dlq"
DLQ_QUEUE_NAME = "supply_chain_dlq_queue"
RETRY_EXCHANGE_NAME = "supply_chain_events"


async def process_dlq_message(message: aio_pika.abc.AbstractIncomingMessage) -> None:
    """Callback for processing dead-lettered events."""
    async with message.process(requeue=False):
        try:
            body = json.loads(message.body.decode())
            event_type = body.get("event_type", "Unknown")
            headers = message.headers
            death_info = headers.get("x-death", [{}])[0]

            reason = death_info.get("reason", "unknown")
            queue = death_info.get("queue", "unknown")
            time_death = death_info.get("time", "unknown")

            logger.warn(
                "DLQ Message Detected",
                event_type=event_type,
                reason=reason,
                original_queue=queue,
                time=str(time_death),
                body=body,
            )

            # In production: implement retry threshold or manual archive logic
            # e.g., if retries < 3, republish to main exchange
            # For now, we archive the message by logging it

        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to process DLQ message", error=str(exc))


async def main() -> None:
    logger.info("Starting Dead-Letter Queue (DLQ) Processor")

    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=5)

        # Declare DLQ Topic exchange
        dlq_exchange = await channel.declare_exchange(
            DLQ_EXCHANGE_NAME,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )

        # Declare durable DLQ queue
        dlq_queue = await channel.declare_queue(
            DLQ_QUEUE_NAME,
            durable=True,
        )

        # Bind all events dead-lettered to this queue
        await dlq_queue.bind(dlq_exchange, routing_key="#")

        logger.info(
            "DLQ Consumer listening",
            exchange=DLQ_EXCHANGE_NAME,
            queue=DLQ_QUEUE_NAME,
        )

        async with dlq_queue.iterator() as queue_iter:
            async for message in queue_iter:
                await process_dlq_message(message)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("DLQ Processor stopped by user")
