from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.graph.state import BlackboardEntry, SupplyChainState


def record_agent_message(
    state: SupplyChainState,
    *,
    agent_id: str,
    topic: str,
    message_type: str,
    confidence: float,
    rationale: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """Write a typed message to the shared blackboard.

    This implements the prompt's peer-to-peer message semantics directly:
    PROPOSE and SUPPORT add proposals, OBJECT marks a contested entry,
    COMMIT marks an accepted entry, and REVERT marks a superseded one.
    """
    blackboard = dict(state.get("blackboard") or {})
    topic_entries = list(blackboard.get(topic) or [])

    status = "proposed"
    if message_type == "OBJECT":
        status = "contested"
    elif message_type == "COMMIT":
        status = "accepted"
    elif message_type == "REVERT":
        status = "superseded"

    entry: BlackboardEntry = {
        "agent_id": agent_id,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "confidence": confidence,
        "rationale": rationale,
        "status": status,
        "data": data,
        "message_type": message_type,
        "topic": topic,
    }

    topic_entries.append(entry)
    blackboard[topic] = topic_entries
    state["blackboard"] = blackboard
    return entry


def apply_human_override(
    state: SupplyChainState,
    *,
    action: str,
    topic: str,
    payload: dict[str, Any],
) -> SupplyChainState:
    """Apply a rare human override to pin or halt decentralized decisions."""
    overrides = dict(state.get("human_overrides") or {})
    overrides[topic] = {
        "action": action,
        "reason": payload.get("reason", "No reason provided"),
        "payload": payload,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }
    state["human_overrides"] = overrides
    return state


def evaluate_agentic_loop(state: SupplyChainState) -> dict[str, Any]:
    """Evaluate the blackboard for contested items and decide whether to escalate."""
    blackboard = state.get("blackboard") or {}
    contested_topics = []

    for topic, entries in blackboard.items():
        if any(entry.get("status") == "contested" for entry in entries):
            contested_topics.append(topic)

    loop_count = int(state.get("loop_count") or 0) + 1
    state["loop_count"] = loop_count

    if contested_topics:
        if loop_count >= 3:
            state["workflow_status"] = "escalated"
            return {
                "workflow_status": "escalated",
                "contested_topics": contested_topics,
                "requires_human_approval": True,
            }
        return {
            "workflow_status": "review",
            "contested_topics": contested_topics,
            "requires_human_approval": False,
        }

    state["workflow_status"] = "completed"
    return {
        "workflow_status": "completed",
        "contested_topics": [],
        "requires_human_approval": False,
    }


def resolve_topic_state(state: SupplyChainState, *, topic: str, quorum_threshold: float = 2.0) -> dict[str, Any]:
    """Resolve a topic using quorum/consensus semantics and lock behavior."""
    entries = list((state.get("blackboard") or {}).get(topic) or [])
    if not entries:
        return {"status": "idle", "accepted": False, "topic": topic}

    weights = state.get("agent_weights") or {}
    support_score = 0.0
    objection_score = 0.0
    support_count = 0

    for entry in entries:
        weight = float(weights.get(entry.get("agent_id"), 1.0))
        if entry.get("message_type") in {"SUPPORT", "COMMIT"}:
            support_score += weight * float(entry.get("confidence") or 0.0)
            support_count += 1
        elif entry.get("message_type") == "OBJECT":
            objection_score += weight * float(entry.get("confidence") or 0.0)

    has_commit = any(entry.get("message_type") == "COMMIT" for entry in entries)
    accepted = (
        has_commit
        and support_count >= 2
        and support_score >= max(1.0, quorum_threshold * 0.75)
        and objection_score <= 0.5
    )
    status = "accepted" if accepted else "contested"

    if accepted:
        return {
            "status": status,
            "accepted": True,
            "topic": topic,
            "support_score": support_score,
            "objection_score": objection_score,
        }

    return {
        "status": status,
        "accepted": False,
        "topic": topic,
        "support_score": support_score,
        "objection_score": objection_score,
    }


def get_blackboard_view(state: SupplyChainState) -> dict[str, Any]:
    """Return a monitorable view of the blackboard for the human layer."""
    blackboard = state.get("blackboard") or {}
    summary = {
        "active_proposals": 0,
        "contested_items": 0,
        "recent_commits": 0,
        "topics": [],
    }

    for topic, entries in blackboard.items():
        summary["topics"].append(topic)
        summary["active_proposals"] += sum(1 for entry in entries if entry.get("status") == "proposed")
        summary["contested_items"] += sum(1 for entry in entries if entry.get("status") == "contested")
        summary["recent_commits"] += sum(1 for entry in entries if entry.get("status") == "accepted")

    return summary
