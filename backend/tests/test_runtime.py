from __future__ import annotations

from app.graph.runtime import AgentRuntime
from app.graph.state import SupplyChainState


def test_runtime_posts_messages_and_monitor_view() -> None:
    state: SupplyChainState = {
        "workflow_id": "runtime-test",
        "blackboard": {},
        "human_overrides": {},
        "messages": [],
        "active_agents": [],
        "errors": [],
        "loop_count": 0,
    }

    runtime = AgentRuntime(state)
    runtime.post_message(agent_id="ADS-10", topic="risk", message_type="PROPOSE", confidence=0.9, rationale="proposal", data={"score": 80})
    runtime.post_message(agent_id="ADS-11", topic="risk", message_type="OBJECT", confidence=0.8, rationale="object", data={"score": 90})

    monitor = runtime.monitor()
    assert monitor["contested_items"] >= 1
    assert monitor["active_proposals"] >= 1


def test_runtime_locking_and_override_round_trip() -> None:
    state: SupplyChainState = {
        "workflow_id": "runtime-test-2",
        "blackboard": {},
        "human_overrides": {},
        "messages": [],
        "active_agents": [],
        "errors": [],
        "loop_count": 0,
    }

    runtime = AgentRuntime(state)
    runtime.lock_topic("risk")
    runtime.apply_override(action="PIN", topic="risk", payload={"reason": "lock decision"})

    assert runtime.lock_versions["risk"] == 1
    assert runtime.state["human_overrides"]["risk"]["action"] == "PIN"
