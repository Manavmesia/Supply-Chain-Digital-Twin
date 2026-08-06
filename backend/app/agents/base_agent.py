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

if TYPE_CHECKING:
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
        Called by the LangGraph runtime.  Returns a *partial* state dict
        (only the keys this agent modifies).
        """
        self._log.info("Agent started", workflow_id=state.get("workflow_id"))

        active = list(state.get("active_agents") or [])
        if self.agent_code not in active:
            active.append(self.agent_code)

        try:
            result = await self._execute(state)
            result["active_agents"] = active
            result["current_node"] = self.agent_code
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
