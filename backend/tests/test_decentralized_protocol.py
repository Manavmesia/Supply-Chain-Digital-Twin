from __future__ import annotations

import pytest

from app.agents.base_agent import BaseAgent
from app.graph.protocol import apply_human_override, record_agent_message
from app.graph.state import SupplyChainState


def test_record_agent_message_writes_typed_blackboard_entry() -> None:
    state: SupplyChainState = {
        "workflow_id": "workflow-1",
        "blackboard": {},
        "human_overrides": {},
        "messages": [],
    }

    record_agent_message(
        state,
        agent_id="ADS-10",
        topic="risk",
        message_type="PROPOSE",
        confidence=0.91,
        rationale="Risk is manageable",
        data={"score": 20},
    )

    entries = state["blackboard"]["risk"]
    assert len(entries) == 1
    assert entries[0]["message_type"] == "PROPOSE"
    assert entries[0]["status"] == "proposed"
    assert entries[0]["topic"] == "risk"


def test_object_messages_are_marked_contested() -> None:
    state: SupplyChainState = {
        "workflow_id": "workflow-2",
        "blackboard": {},
        "human_overrides": {},
        "messages": [],
    }

    record_agent_message(
        state,
        agent_id="ADS-11",
        topic="finance",
        message_type="OBJECT",
        confidence=0.75,
        rationale="Budget threshold breached",
        data={"approval_status": "denied"},
    )

    entry = state["blackboard"]["finance"][0]
    assert entry["status"] == "contested"
    assert entry["message_type"] == "OBJECT"


def test_apply_human_override_records_pin_and_halt_actions() -> None:
    state: SupplyChainState = {
        "workflow_id": "workflow-3",
        "blackboard": {},
        "human_overrides": {},
        "messages": [],
    }

    state = apply_human_override(state, action="PIN", topic="risk", payload={"reason": "lock decision"})
    assert state["human_overrides"]["risk"]["action"] == "PIN"
    assert state["human_overrides"]["risk"]["reason"] == "lock decision"

    state = apply_human_override(state, action="HALT", topic="risk", payload={"reason": "pause workflow"})
    assert state["human_overrides"]["risk"]["action"] == "HALT"
    assert state["human_overrides"]["risk"]["reason"] == "pause workflow"


class DummyAgent(BaseAgent):
    agent_code = "ADS-01"
    agent_name = "Dummy Agent"

    async def _execute(self, state: SupplyChainState) -> dict:
        return {"inventory": {"status": "reserved"}}


@pytest.mark.asyncio
async def test_base_agent_auto_publishes_a_protocol_entry() -> None:
    state: SupplyChainState = {
        "workflow_id": "workflow-4",
        "blackboard": {},
        "human_overrides": {},
        "messages": [],
        "active_agents": [],
        "errors": [],
    }

    agent = DummyAgent()
    await agent.run(state)

    entry = state["blackboard"]["inventory"][0]
    assert entry["message_type"] == "COMMIT"
    assert entry["status"] == "accepted"
