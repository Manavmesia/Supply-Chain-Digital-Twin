from __future__ import annotations

from app.graph.protocol import (
    apply_human_override,
    evaluate_agentic_loop,
    record_agent_message,
    resolve_topic_state,
)
from app.graph.state import SupplyChainState


def test_quorum_and_locking_behavior() -> None:
    state: SupplyChainState = {
        "workflow_id": "workflow-spec",
        "blackboard": {},
        "human_overrides": {},
        "messages": [],
        "active_agents": [],
        "errors": [],
        "loop_count": 0,
        "agent_weights": {"ADS-10": 1.0, "ADS-11": 1.0, "ADS-12": 1.0},
    }

    record_agent_message(state, agent_id="ADS-10", topic="risk", message_type="PROPOSE", confidence=0.9, rationale="proposal", data={"score": 70})
    record_agent_message(state, agent_id="ADS-11", topic="risk", message_type="SUPPORT", confidence=0.8, rationale="support", data={"score": 70})
    record_agent_message(state, agent_id="ADS-12", topic="risk", message_type="COMMIT", confidence=0.95, rationale="commit", data={"score": 70})

    resolved = resolve_topic_state(state, topic="risk", quorum_threshold=2.0)
    assert resolved["status"] == "accepted"
    assert resolved["accepted"] is True


def test_escalation_and_halt_override() -> None:
    state: SupplyChainState = {
        "workflow_id": "workflow-spec-2",
        "blackboard": {},
        "human_overrides": {},
        "messages": [],
        "active_agents": [],
        "errors": [],
        "loop_count": 0,
        "agent_weights": {"ADS-10": 1.0, "ADS-11": 1.0},
    }

    record_agent_message(state, agent_id="ADS-10", topic="risk", message_type="PROPOSE", confidence=0.7, rationale="proposal", data={"score": 90})
    record_agent_message(state, agent_id="ADS-11", topic="risk", message_type="OBJECT", confidence=0.8, rationale="object", data={"score": 90})

    result = evaluate_agentic_loop(state)
    assert result["workflow_status"] in {"review", "escalated"}

    state = apply_human_override(state, action="HALT", topic="risk", payload={"reason": "stop loop"})
    assert state["human_overrides"]["risk"]["action"] == "HALT"
