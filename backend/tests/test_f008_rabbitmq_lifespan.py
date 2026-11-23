"""
Custom verification test suite for Finding F-008:
Missing Lifespan Initialization of Shared RabbitMQ Event Publisher.
"""
from unittest.mock import AsyncMock, patch
import pytest

from app.core import rabbitmq
from app.main import lifespan, app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_lifespan_connects_and_disconnects_rabbitmq_publisher():
    """Verify lifespan calls connect_rabbitmq on startup and disconnect_rabbitmq on shutdown."""
    with patch("app.core.rabbitmq.connect_rabbitmq", new_callable=AsyncMock) as mock_connect, \
         patch("app.core.rabbitmq.disconnect_rabbitmq", new_callable=AsyncMock) as mock_disconnect:

        async with lifespan(app):
            mock_connect.assert_awaited_once()
            mock_disconnect.assert_not_awaited()

        mock_disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_publisher_dependency_lifecycle():
    """Verify get_rabbitmq_publisher returns connected instance during active lifespan and cleans up after."""
    mock_publisher = AsyncMock()

    with patch("app.core.rabbitmq.EventPublisher", return_value=mock_publisher):
        # 1. Before startup, calling dependency raises RuntimeError
        with pytest.raises(RuntimeError, match="RabbitMQ publisher is not connected"):
            await rabbitmq.get_rabbitmq_publisher()

        # 2. During lifespan, publisher is initialized and returned
        async with lifespan(app):
            publisher = await rabbitmq.get_rabbitmq_publisher()
            assert publisher is mock_publisher
            mock_publisher.connect.assert_awaited_once()

        # 3. After lifespan shutdown, publisher is disconnected
        mock_publisher.disconnect.assert_awaited_once()
        with pytest.raises(RuntimeError, match="RabbitMQ publisher is not connected"):
            await rabbitmq.get_rabbitmq_publisher()


@pytest.mark.asyncio
async def test_lifespan_graceful_on_rabbitmq_offline():
    """Verify application startup is non-blocking even if RabbitMQ is completely offline."""
    with patch("app.core.rabbitmq.EventPublisher.connect", side_effect=ConnectionRefusedError("RabbitMQ offline")):
        async with lifespan(app):
            # Application successfully enters active lifespan despite RabbitMQ offline
            assert True
