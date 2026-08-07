"""
BaseAgent — abstract base class for all 18 AI Supply Chain agents.

Every agent node in the LangGraph graph calls agent.run(state) which:
  1. Records the agent as active in state["active_agents"]
  2. Sets state["current_node"]
  3. Calls the concrete agent's _execute() method
  4. Catches errors and appends them to state["errors"]
  5. Returns the partial state update dict

Concrete agents override _execute() only — they never call super().run() manually.
"""

from __future__ import annotations

import abc
import traceback
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import structlog

from app.graph.protocol import record_agent_message
from app.graph.state import SupplyChainState

logger = structlog.get_logger(__name__)


class BaseAgent(abc.ABC):
    """
    Abstract base for every LangGraph agent node.

    Attributes:
        agent_code:  ADS-XX identifier (e.g. 'ADS-01')
        agent_name:  Human-readable name
        session:     AsyncSession — injected at workflow runtime
        publisher:   EventPublisher — injected at workflow runtime
    """

    agent_code: str = ""
    agent_name: str = ""

    def __init__(
        self,
        session: Any | None = None,
        publisher: Any | None = None,
    ) -> None:
        self.session = session
        self.publisher = publisher
        self._log = logger.bind(agent=self.agent_code)

    # ── LangGraph node entry point ───────────────────────────────────────────

    async def run(self, state: SupplyChainState) -> dict[str, Any]:
        """
        Called by the LangGraph runtime. Performs automatic blackboard pre-processing
        and post-processing to ensure peer-to-peer data flow and backward compatibility.
        """
        self._log.info("Agent started", workflow_id=state.get("workflow_id"))

        active = list(state.get("active_agents") or [])
        if self.agent_code not in active:
            active.append(self.agent_code)

        # ── Pre-processing: Mirror latest Blackboard entries to flat state keys ──
        blackboard = state.get("blackboard") or {}
        for topic, entries in blackboard.items():
            latest = None
            for entry in reversed(entries):
                if entry.get("status") != "superseded":
                    latest = entry
                    break
            if latest:
                state[topic] = latest["data"]

        try:
            result = await self._execute(state)
            result["active_agents"] = active
            result["current_node"] = self.agent_code

            if not state.get("blackboard"):
                state["blackboard"] = {}

            for key in ("order", "inventory", "warehouse", "supplier", "shipment", "finance", "risk", "forecast", "quality", "sustainability", "manufacturing", "customer_service", "pricing", "procurement", "planning", "negotiation"):
                if key in result and isinstance(result[key], dict):
                    record_agent_message(
                        state,
                        agent_id=self.agent_code,
                        topic=key,
                        message_type="COMMIT",
                        confidence=0.9,
                        rationale=f"{self.agent_name} updated {key} autonomously",
                        data=result[key],
                    )
                    break

            # ── Post-processing: Mirror result keys back to the Blackboard ─────
            new_blackboard = dict(state.get("blackboard") or {})
            topics_mapping = {
                "order": "order",
                "inventory": "inventory",
                "warehouse": "warehouse",
                "supplier": "supplier",
                "shipment": "shipment",
                "finance": "finance",
                "risk": "risk",
                "forecast": "forecast",
                "quality": "quality",
                "sustainability": "sustainability",
                "manufacturing": "manufacturing",
                "customer_service": "customer_service",
                "pricing": "pricing",
                "procurement": "procurement",
                "planning": "planning",
                "negotiation": "negotiation",
            }

            is_operational = self.agent_code in (
                "ADS-01", "ADS-03", "ADS-04", "ADS-05", "ADS-06", "ADS-07", "ADS-08"
            )

            for key, value in list(result.items()):
                if key in topics_mapping and isinstance(value, dict):
                    topic = topics_mapping[key]
                    
                    status = "accepted" if is_operational else "proposed"
                    confidence = 1.0
                    rationale = f"Updated by {self.agent_name}"
                    
                    # BI Agent constraint evaluation mapping
                    if key == "risk" and float(value.get("score", 0.0)) > 85.0:
                        status = "contested"
                        confidence = 0.3
                        rationale = f"Risk score {value.get('score')} exceeds policy limit of 85."
                    elif key == "finance" and value.get("approval_status") == "denied":
                        status = "contested"
                        confidence = 0.4
                        rationale = "Finance review failed: margin threshold breach."
                    elif key == "quality" and value.get("status") == "failed":
                        status = "contested"
                        confidence = 0.2
                        rationale = "Quality QA check failed."

                    # Human override logic
                    overrides = state.get("human_overrides") or {}
                    if topic in overrides:
                        status = "accepted"
                        value = overrides[topic]
                        rationale = "User locked this decision via override."

                    topic_entries = list(new_blackboard.get(topic) or [])
                    new_entries = []
                    for entry in topic_entries:
                        entry_copy = dict(entry)
                        if entry_copy.get("status") in ("proposed", "contested", "accepted"):
                            entry_copy["status"] = "superseded"
                        new_entries.append(entry_copy)

                    new_entries.append({
                        "agent_id": self.agent_code,
                        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                        "confidence": confidence,
                        "rationale": rationale,
                        "status": status,
                        "data": value,
                        "message_type": "PROPOSE",
                        "topic": topic,
                    })
                    new_blackboard[topic] = new_entries
                    result["blackboard"] = new_blackboard

            self._log.info("Agent completed", workflow_id=state.get("workflow_id"))
            return result

        except Exception as exc:  # noqa: BLE001
            tb = traceback.format_exc()
            self._log.error(
                "Agent error",
                workflow_id=state.get("workflow_id"),
                error=str(exc),
            )
            errors = list(state.get("errors") or [])
            errors.append(
                {
                    "agent": self.agent_code,
                    "error": str(exc),
                    "traceback": tb,
                    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                }
            )
            return {
                "active_agents": active,
                "current_node": self.agent_code,
                "errors": errors,
                "workflow_status": "failed",
            }


    # ── Abstract method every concrete agent implements ──────────────────────

    @abc.abstractmethod
    async def _execute(self, state: SupplyChainState) -> dict[str, Any]:
        """
        Core agent logic.  Must return a partial state dict.
        Raise any exception on failure — BaseAgent.run() will catch it.
        """

    # ── Helpers ──────────────────────────────────────────────────────────────

    async def _publish(
        self,
        state: SupplyChainState,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        """Publish an event and append it to state["event_history"]."""
        if self.publisher is None:
            # No publisher in unit-test mode — just record locally
            return

        correlation_id = uuid.UUID(state.get("correlation_id") or str(uuid.uuid4()))
        workflow_id_str = state.get("workflow_id")
        workflow_id = uuid.UUID(workflow_id_str) if workflow_id_str else None

        await self.publisher.publish(
            event_type=event_type,
            source_agent=self.agent_code,
            correlation_id=correlation_id,
            payload=payload,
            workflow_id=workflow_id,
        )

    def _record_decision(
        self,
        state_or_decisions: SupplyChainState | list[dict[str, Any]],
        action: str,
        reason: str,
        data: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Return an updated decisions list with this agent's decision appended.
        Callers must include it in their returned state dict.
        """
        if isinstance(state_or_decisions, list):
            decisions = list(state_or_decisions)
        else:
            decisions = list(state_or_decisions.get("decisions") or [])
        decisions.append(
            {
                "agent": self.agent_code,
                "action": action,
                "reason": reason,
                "data": data or {},
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            }
        )
        return decisions

    def _append_event(
        self,
        state_or_history: SupplyChainState | list[dict[str, Any]],
        event_type: str,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Return an updated event_history list."""
        if isinstance(state_or_history, list):
            history = list(state_or_history)
        else:
            history = list(state_or_history.get("event_history") or [])
        history.append(
            {
                "event_type": event_type,
                "source_agent": self.agent_code,
                "payload": payload,
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            }
        )
        return history

    def _write_blackboard(
        self,
        state: SupplyChainState,
        topic: str,
        status: str,
        data: dict[str, Any],
        confidence: float = 1.0,
        rationale: str = "",
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Write a new versioned entry to the shared blackboard.
        Automatically checks for human overrides and marks previous active entries as superseded.
        """
        blackboard = dict(state.get("blackboard") or {})
        topic_entries = list(blackboard.get(topic) or [])
        
        # Check human override for this topic
        overrides = state.get("human_overrides") or {}
        if topic in overrides:
            status = "accepted"
            data = overrides[topic]
            rationale = "User locked this decision via override."
            confidence = 1.0

        # Mark all previous active entries of this topic as superseded
        new_entries = []
        for entry in topic_entries:
            entry_copy = dict(entry)
            if entry_copy.get("status") in ("proposed", "contested", "accepted"):
                entry_copy["status"] = "superseded"
            new_entries.append(entry_copy)

        new_entries.append({
            "agent_id": self.agent_code,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "confidence": confidence,
            "rationale": rationale,
            "status": status,
            "data": data,
        })
        blackboard[topic] = new_entries
        return blackboard

    def _get_blackboard_latest(self, state: SupplyChainState, topic: str) -> dict[str, Any] | None:
        """
        Helper to retrieve the latest non-superseded blackboard entry for a topic.
        """
        blackboard = state.get("blackboard") or {}
        entries = blackboard.get(topic) or []
        for entry in reversed(entries):
            if entry.get("status") != "superseded":
                return entry
        return None

