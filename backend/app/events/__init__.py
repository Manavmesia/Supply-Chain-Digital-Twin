"""
app/events/__init__.py — Event infrastructure public API.
"""

from app.events.publisher import EventPublisher, UnregisteredEventTypeError
from app.events.registry import CANONICAL_EVENT_NAMES, CANONICAL_EVENTS

__all__ = [
    "CANONICAL_EVENTS",
    "CANONICAL_EVENT_NAMES",
    "EventPublisher",
    "UnregisteredEventTypeError",
]
