"""
Tests for the event infrastructure — US-66 / EP-14

Covers:
  - Canonical registry completeness and invariants
  - EventPublisher: validation, DB persistence, AMQP publish (mocked)
  - UnregisteredEventTypeError typo suggestion
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Registry tests (no DB, no broker needed)
# ---------------------------------------------------------------------------

class TestEventRegistry:
    def test_registry_is_not_empty(self):
        from app.events.registry import CANONICAL_EVENTS
        assert len(CANONICAL_EVENTS) >= 50, "Registry should have at least 50 events"

    def test_event_names_frozenset_matches_dict_keys(self):
        from app.events.registry import CANONICAL_EVENTS, CANONICAL_EVENT_NAMES
        assert CANONICAL_EVENT_NAMES == frozenset(CANONICAL_EVENTS.keys())

    def test_every_event_has_required_fields(self):
        from app.events.registry import CANONICAL_EVENTS
        required = {"version", "publisher", "subscribers", "description"}
        for name, meta in CANONICAL_EVENTS.items():
            missing = required - meta.keys()
            assert not missing, f"Event '{name}' is missing fields: {missing}"

    def test_subscribers_is_always_a_list(self):
        from app.events.registry import CANONICAL_EVENTS
        for name, meta in CANONICAL_EVENTS.items():
            assert isinstance(meta["subscribers"], list), (
                f"Event '{name}' subscribers should be a list, got {type(meta['subscribers'])}"
            )

    def test_version_is_string(self):
        from app.events.registry import CANONICAL_EVENTS
        for name, meta in CANONICAL_EVENTS.items():
            assert isinstance(meta["version"], str), (
                f"Event '{name}' version should be a string"
            )

    def test_canonical_event_names_is_frozenset(self):
        from app.events.registry import CANONICAL_EVENT_NAMES
        assert isinstance(CANONICAL_EVENT_NAMES, frozenset)

    def test_known_events_present(self):
        """Spot-check that key events from the spec exist."""
        from app.events.registry import CANONICAL_EVENT_NAMES
        required_events = [
            "OrderCreated",
            "InventoryAllocated",
            "InventoryLow",
            "PurchaseOrderCreated",
            "ShipmentCreated",
            "ShipmentDelivered",
            "RiskDetected",
            "CEOApprovalGranted",
            "ContractExpiring",
            "PromotionStarted",
        ]
        for event in required_events:
            assert event in CANONICAL_EVENT_NAMES, f"'{event}' missing from registry"

    def test_no_duplicates_in_dict(self):
        from app.events.registry import CANONICAL_EVENTS
        names = list(CANONICAL_EVENTS.keys())
        assert len(names) == len(set(names)), "Duplicate keys detected in CANONICAL_EVENTS"


# ---------------------------------------------------------------------------
# UnregisteredEventTypeError tests
# ---------------------------------------------------------------------------

class TestUnregisteredEventTypeError:
    def test_raises_for_unknown_event(self):
        from app.events.publisher import UnregisteredEventTypeError
        with pytest.raises(UnregisteredEventTypeError, match="not registered"):
            raise UnregisteredEventTypeError("NonExistentEvent")

    def test_error_contains_event_type(self):
        from app.events.publisher import UnregisteredEventTypeError
        err = UnregisteredEventTypeError("FakeEvent")
        assert err.event_type == "FakeEvent"

    def test_suggests_closest_match_for_typo(self):
        from app.events.publisher import UnregisteredEventTypeError
        # "OrderCreted" is a typo for "OrderCreated"
        err = UnregisteredEventTypeError("OrderCreted")
        assert "OrderCreated" in str(err), (
            f"Expected 'OrderCreated' suggestion in error: {err}"
        )

    def test_message_references_registry_path(self):
        from app.events.publisher import UnregisteredEventTypeError
        err = UnregisteredEventTypeError("BogusEvent")
        assert "app/events/registry.py" in str(err)


# ---------------------------------------------------------------------------
# EventPublisher unit tests (mocked broker)
# ---------------------------------------------------------------------------

class TestEventPublisherValidation:
    """Tests that don't need a real AMQP broker."""

    def _make_publisher(self, session=None):
        from app.events.publisher import EventPublisher
        return EventPublisher(rabbitmq_url="amqp://guest:guest@localhost/", session=session)

    @pytest.mark.asyncio
    async def test_raises_for_unregistered_event(self):
        from app.events.publisher import UnregisteredEventTypeError
        pub = self._make_publisher()
        with pytest.raises(UnregisteredEventTypeError):
            await pub.publish(
                event_type="BogusEvent",
                source_agent="ADS-01",
                correlation_id=uuid.uuid4(),
                payload={},
            )

    @pytest.mark.asyncio
    async def test_raises_runtime_error_when_not_connected(self):
        from app.events.publisher import UnregisteredEventTypeError
        pub = self._make_publisher()
        # A valid event type passes validation but must fail on broker call
        with pytest.raises(RuntimeError, match="not connected"):
            await pub.publish(
                event_type="OrderCreated",
                source_agent="ADS-01",
                correlation_id=uuid.uuid4(),
                payload={"order_id": str(uuid.uuid4())},
            )

    @pytest.mark.asyncio
    async def test_publish_validates_event_type_before_broker_call(self):
        """
        Validation must happen BEFORE any broker interaction so that even
        if the broker is disconnected a bad event type is caught immediately.
        """
        from app.events.publisher import EventPublisher, UnregisteredEventTypeError

        pub = EventPublisher(rabbitmq_url="amqp://guest:guest@localhost/")
        # Set up a fake (connected) exchange so we'd reach the broker if validation passes
        pub._exchange = AsyncMock()

        with pytest.raises(UnregisteredEventTypeError):
            await pub.publish(
                event_type="NotAValidEvent",
                source_agent="ADS-01",
                correlation_id=uuid.uuid4(),
                payload={},
            )
        # Broker should never have been called
        pub._exchange.publish.assert_not_called()


class TestEventPublisherPublish:
    """Tests that mock the AMQP broker and optionally the DB session."""

    @pytest.mark.asyncio
    async def test_publish_persists_to_db_before_broker(self):
        """DB .add() must be called before exchange.publish()."""
        from app.events.publisher import EventPublisher

        call_order: list[str] = []

        session = MagicMock()
        session.add = MagicMock(side_effect=lambda _: call_order.append("db_add"))
        session.flush = AsyncMock(side_effect=lambda: call_order.append("db_flush"))

        pub = EventPublisher(rabbitmq_url="amqp://guest:guest@localhost/", session=session)
        pub._exchange = AsyncMock()
        pub._exchange.publish = AsyncMock(side_effect=lambda *a, **kw: call_order.append("amqp_publish"))

        await pub.publish(
            event_type="OrderCreated",
            source_agent="ADS-01",
            correlation_id=uuid.uuid4(),
            payload={"order_id": str(uuid.uuid4())},
        )

        assert call_order == ["db_add", "db_flush", "amqp_publish"], (
            f"Expected db_add → db_flush → amqp_publish, got: {call_order}"
        )

    @pytest.mark.asyncio
    async def test_publish_returns_event_object(self):
        from app.events.publisher import EventPublisher
        from app.models.event import Event

        pub = EventPublisher(rabbitmq_url="amqp://", session=None)
        pub._exchange = AsyncMock()

        result = await pub.publish(
            event_type="OrderCreated",
            source_agent="ADS-01",
            correlation_id=uuid.uuid4(),
            payload={"order_id": str(uuid.uuid4())},
        )

        assert isinstance(result, Event)

    @pytest.mark.asyncio
    async def test_publish_uses_provided_event_id(self):
        from app.events.publisher import EventPublisher

        fixed_id = uuid.uuid4()
        pub = EventPublisher(rabbitmq_url="amqp://", session=None)
        pub._exchange = AsyncMock()

        event = await pub.publish(
            event_type="OrderCreated",
            source_agent="ADS-01",
            correlation_id=uuid.uuid4(),
            payload={},
            event_id=fixed_id,
        )

        assert event.event_id == fixed_id

    @pytest.mark.asyncio
    async def test_amqp_message_routing_key_is_event_type(self):
        from app.events.publisher import EventPublisher

        pub = EventPublisher(rabbitmq_url="amqp://", session=None)
        pub._exchange = AsyncMock()

        await pub.publish(
            event_type="InventoryLow",
            source_agent="ADS-03",
            correlation_id=uuid.uuid4(),
            payload={"product_id": str(uuid.uuid4())},
        )

        call_args = pub._exchange.publish.call_args
        routing_key = call_args.kwargs.get("routing_key") or call_args.args[1]
        assert routing_key == "InventoryLow"

    @pytest.mark.asyncio
    async def test_amqp_message_body_is_valid_json(self):
        from app.events.publisher import EventPublisher
        import aio_pika

        captured: list[aio_pika.Message] = []

        async def capture_publish(message, *, routing_key=None):
            captured.append(message)

        pub = EventPublisher(rabbitmq_url="amqp://", session=None)
        pub._exchange = AsyncMock()
        pub._exchange.publish = AsyncMock(side_effect=capture_publish)

        await pub.publish(
            event_type="ShipmentCreated",
            source_agent="ADS-06",
            correlation_id=uuid.uuid4(),
            payload={"shipment_id": str(uuid.uuid4())},
        )

        assert captured, "No message captured"
        body = json.loads(captured[0].body.decode())
        assert body["event_type"] == "ShipmentCreated"
        assert "event_id" in body
        assert "correlation_id" in body
        assert "payload" in body

    @pytest.mark.asyncio
    async def test_publish_without_session_does_not_call_db(self):
        from app.events.publisher import EventPublisher

        pub = EventPublisher(rabbitmq_url="amqp://", session=None)
        pub._exchange = AsyncMock()

        # Should succeed without AttributeError on NoneType
        event = await pub.publish(
            event_type="RiskDetected",
            source_agent="ADS-10",
            correlation_id=uuid.uuid4(),
            payload={"risk_score": 88},
        )
        assert event is not None

    @pytest.mark.asyncio
    async def test_simulation_id_in_metadata(self):
        from app.events.publisher import EventPublisher

        sim_id = uuid.uuid4()
        pub = EventPublisher(rabbitmq_url="amqp://", session=None)
        pub._exchange = AsyncMock()

        event = await pub.publish(
            event_type="OrderCreated",
            source_agent="ADS-01",
            correlation_id=uuid.uuid4(),
            payload={},
            simulation_id=sim_id,
        )
        assert event.simulation_id == sim_id
        assert str(sim_id) in event.event_metadata.get("simulation_id", "")


# ---------------------------------------------------------------------------
# Integration smoke test — registry ↔ publisher
# ---------------------------------------------------------------------------

class TestRegistryPublisherIntegration:
    @pytest.mark.asyncio
    async def test_all_canonical_events_can_be_published_without_validation_error(self):
        """
        Every event in the canonical registry must pass validation.
        Uses a mocked exchange so no broker is needed.
        """
        from app.events.publisher import EventPublisher
        from app.events.registry import CANONICAL_EVENT_NAMES

        pub = EventPublisher(rabbitmq_url="amqp://", session=None)
        pub._exchange = AsyncMock()

        failed: list[str] = []
        for event_type in sorted(CANONICAL_EVENT_NAMES):
            try:
                await pub.publish(
                    event_type=event_type,
                    source_agent="TEST",
                    correlation_id=uuid.uuid4(),
                    payload={},
                )
            except Exception as exc:  # noqa: BLE001
                failed.append(f"{event_type}: {exc}")

        assert not failed, (
            f"These canonical events failed to publish:\n" + "\n".join(failed)
        )
