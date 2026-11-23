"""
Global Execution Configuration for Multi-Agent Workflows and Event Remediation.

Provides thread-safe access to agent execution speed and visual delay settings.
When tests are running (pytest), default delay is 0.0s to ensure instant test suites.
In development and production, default delay provides smooth visualization transitions.
"""

from __future__ import annotations

import os
import sys

# Pytest detection ensures unit tests execute at maximum speed
_IS_TEST = "pytest" in sys.modules or os.getenv("ENVIRONMENT", "").lower() == "test"
_DEFAULT_DELAY = 0.0 if _IS_TEST else float(os.getenv("AGENT_EXECUTION_DELAY_SECONDS", "0.8"))

_CURRENT_DELAY: float = _DEFAULT_DELAY


def get_agent_delay() -> float:
    """Return the current delay in seconds injected between agent executions."""
    return _CURRENT_DELAY


def set_agent_delay(delay: float) -> float:
    """Update the delay in seconds injected between agent executions."""
    global _CURRENT_DELAY
    _CURRENT_DELAY = max(0.0, min(10.0, float(delay)))
    return _CURRENT_DELAY
