from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.graph.protocol import apply_human_override, evaluate_agentic_loop, get_blackboard_view, record_agent_message, resolve_topic_state
from app.graph.state import SupplyChainState


@dataclass
class AgentRuntime:
    state: SupplyChainState
    lock_versions: dict[str, int] = field(default_factory=dict)
    event_log: list[dict[str, Any]] = field(default_factory=list)

    def post_message(self, *, agent_id: str, topic: str, message_type: str, confidence: float, rationale: str, data: dict[str, Any]) -> dict[str, Any]:
        entry = record_agent_message(self.state, agent_id=agent_id, topic=topic, message_type=message_type, confidence=confidence, rationale=rationale, data=data)
        self.event_log.append({"event": "message", "topic": topic, "agent_id": agent_id, "message_type": message_type, "timestamp": entry["timestamp"]})
        return entry

    def apply_override(self, *, action: str, topic: str, payload: dict[str, Any]) -> SupplyChainState:
        self.event_log.append({"event": "override", "topic": topic, "action": action, "timestamp": datetime.now(tz=timezone.utc).isoformat()})
        return apply_human_override(self.state, action=action, topic=topic, payload=payload)

    def resolve(self, *, topic: str, quorum_threshold: float = 2.0) -> dict[str, Any]:
        return resolve_topic_state(self.state, topic=topic, quorum_threshold=quorum_threshold)

    def evaluate(self) -> dict[str, Any]:
        return evaluate_agentic_loop(self.state)

    def monitor(self) -> dict[str, Any]:
        view = get_blackboard_view(self.state)
        view["workflow_status"] = self.state.get("workflow_status")
        view["loop_count"] = self.state.get("loop_count")
        view["event_log"] = self.event_log[-10:]
        return view

    def lock_topic(self, topic: str, *, version: int | None = None) -> int:
        current = self.lock_versions.get(topic, 0)
        next_version = version if version is not None else current + 1
        self.lock_versions[topic] = next_version
        self.event_log.append({"event": "lock", "topic": topic, "version": next_version, "timestamp": datetime.now(tz=timezone.utc).isoformat()})
        return next_version

    def unlock_topic(self, topic: str) -> None:
        self.lock_versions.pop(topic, None)
        self.event_log.append({"event": "unlock", "topic": topic, "timestamp": datetime.now(tz=timezone.utc).isoformat()})
