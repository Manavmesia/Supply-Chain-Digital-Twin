from __future__ import annotations

import pytest

from app.graph.protocol import apply_human_override, record_agent_message
from app.graph.state import SupplyChainState


@pytest.mark.asyncio
async def test_autonomous_loop_marks_contested_items_and_escalates() -> None:
    state: SupplyChainState = {
        "workflow_id": "workflow-loop",
        "blackboard": {},
        "human_overrides": {},
        "messages": [],
        "active_agents": [],
        "errors": [],
        "loop_count": 0,
    }

    record_agent_message(
        state,
        agent_id="ADS-10",
        topic="risk",
        message_type="PROPOSE",
        confidence=0.9,
        rationale="Risk mitigation proposed",
        data={"score": 88},
    )
    record_agent_message(
        state,
        agent_id="ADS-11",
        topic="risk",
        message_type="OBJECT",
        confidence=0.8,
        rationale="Risk level is too high",
        data={"score": 92},
    )

    contested = [entry for entry in state["blackboard"]["risk"] if entry.get("status") == "contested"]
    assert contested

    state = apply_human_override(state, action="HALT", topic="risk", payload={"reason": "escalate for review"})
    assert state["human_overrides"]["risk"]["action"] == "HALT"
