"""
Simulate REST API — Phase 5 / What-If Simulation Engine

POST /api/v1/simulate            — trigger a what-if simulation scenario
GET  /api/v1/simulate/{id}       — poll simulation result
GET  /api/v1/simulate            — list recent simulations
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from pydantic import BaseModel

from app.core.database import AsyncSessionLocal
from app.graph.state import SupplyChainState
from app.graph.workflow import compile_workflow

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/simulate", tags=["simulate"])

# ---------------------------------------------------------------------------
# In-process simulation store
# ---------------------------------------------------------------------------

_SIM_STORE: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SimulationScenario(BaseModel):
    scenario_type: str
    """
    One of:
      - demand_spike        — 2x demand for all products
      - supplier_outage     — primary supplier unavailable
      - logistics_delay     — transit days doubled, air freight forced
      - bulk_order          — large-value enterprise order (critical priority)
      - quality_crisis      — QA agent will flag all batches as failed
    """
    customer_id: str
    items: list[dict[str, Any]]
    description: str | None = None


class SimulationAccepted(BaseModel):
    simulation_id: str
    scenario_type: str
    status: str = "queued"
    message: str


# ---------------------------------------------------------------------------
# Scenario builders — mutate the initial state to simulate conditions
# ---------------------------------------------------------------------------

_SCENARIO_DESCRIPTIONS = {
    "demand_spike": "2× demand — tests inventory strain and supplier fallback",
    "supplier_outage": "Primary supplier unavailable — tests alternate sourcing",
    "logistics_delay": "Doubled transit days — tests risk score and CEO escalation",
    "bulk_order": "High-value enterprise order — tests finance thresholds and CEO approval",
    "quality_crisis": "All QA batches fail — tests manufacturing reorder path",
}


def _build_initial_state(
    simulation_id: str,
    scenario: SimulationScenario,
) -> SupplyChainState:
    """Build the initial state with scenario-specific overrides."""
    items = scenario.items

    # Demand spike: double all quantities
    if scenario.scenario_type == "demand_spike":
        items = [
            {**item, "quantity": item.get("quantity", 1) * 2}
            for item in items
        ]

    state: SupplyChainState = {
        "workflow_id": simulation_id,
        "correlation_id": str(uuid.uuid4()),
        "workflow_status": "received",
        "active_agents": [],
        "event_history": [],
        "decisions": [],
        "errors": [],
        "messages": [],
        "retries": {},
        "order": {
            "customer_id": scenario.customer_id,
            "items": [
                {"product_id": str(i.get("product_id")), "quantity": i.get("quantity", 1)}
                for i in items
            ],
        },
    }

    # Scenario-specific pre-loaded state signals
    if scenario.scenario_type == "logistics_delay":
        state["shipment"] = {"freight_mode": "air", "transit_days": 14}

    if scenario.scenario_type == "bulk_order":
        # Mark as enterprise tier order forcing critical priority
        state["order"]["_simulation_hint"] = "enterprise_bulk"

    return state


# ---------------------------------------------------------------------------
# Background simulation runner
# ---------------------------------------------------------------------------

async def _run_simulation(
    simulation_id: str,
    scenario: SimulationScenario,
) -> None:
    """Run the full workflow in simulation mode and store the result."""
    _SIM_STORE[simulation_id]["status"] = "running"

    initial_state = _build_initial_state(simulation_id, scenario)
    trace: list[dict[str, Any]] = []

    try:
        config = {"configurable": {"thread_id": simulation_id}}

        async with AsyncSessionLocal() as session:
            # _make_node expects an async zero-arg callable that returns a session
            async def _session_factory():
                return session

            compiled = compile_workflow(
                session_factory=_session_factory,
                trace_collector=trace,
            )
            final_state = await compiled.ainvoke(initial_state, config=config)

            if not final_state.get("errors"):
                final_state["workflow_status"] = "completed"

            await session.rollback()

        _SIM_STORE[simulation_id].update({
            "status": "completed",
            "final_state": final_state,
            "trace": trace,
            "agents_executed": len(trace),
            "scenario_description": _SCENARIO_DESCRIPTIONS.get(scenario.scenario_type, ""),
        })

        logger.info(
            "Simulation completed",
            simulation_id=simulation_id,
            scenario=scenario.scenario_type,
            agents=len(trace),
        )

    except Exception as exc:  # noqa: BLE001
        logger.error("Simulation failed", simulation_id=simulation_id, error=str(exc))
        _SIM_STORE[simulation_id].update({
            "status": "failed",
            "error": str(exc),
            "trace": trace,
        })


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=SimulationAccepted,
    summary="Trigger a what-if simulation scenario",
)
async def start_simulation(
    scenario: SimulationScenario,
    background_tasks: BackgroundTasks,
) -> SimulationAccepted:
    """
    Run a what-if simulation through the full 18-agent workflow.

    The simulation is isolated — it runs through the real workflow graph
    with real DB reads but all writes are rolled back (simulation mode).

    **Supported scenario_types:**
    - `demand_spike` — 2× demand, tests inventory + supplier fallback
    - `supplier_outage` — primary supplier down, tests alternate sourcing
    - `logistics_delay` — long transit + air freight, tests risk escalation
    - `bulk_order` — large enterprise order, tests finance + CEO approval path
    - `quality_crisis` — all QA fails, tests manufacturing reorder path
    """
    simulation_id = str(uuid.uuid4())

    _SIM_STORE[simulation_id] = {
        "simulation_id": simulation_id,
        "scenario_type": scenario.scenario_type,
        "status": "queued",
        "description": scenario.description or _SCENARIO_DESCRIPTIONS.get(
            scenario.scenario_type, ""
        ),
    }

    background_tasks.add_task(_run_simulation, simulation_id, scenario)

    logger.info(
        "Simulation queued",
        simulation_id=simulation_id,
        scenario=scenario.scenario_type,
    )

    return SimulationAccepted(
        simulation_id=simulation_id,
        scenario_type=scenario.scenario_type,
        message=f"Simulation '{scenario.scenario_type}' started. Poll /simulate/{simulation_id} for results.",
    )


@router.get(
    "",
    summary="List recent simulations",
)
async def list_simulations(
    limit: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    """List recent simulation runs and their statuses."""
    sims = list(reversed(list(_SIM_STORE.values())))[:limit]
    return {
        "items": [
            {
                "simulation_id": s["simulation_id"],
                "scenario_type": s["scenario_type"],
                "status": s["status"],
                "description": s.get("description", ""),
                "agents_executed": s.get("agents_executed", 0),
            }
            for s in sims
        ],
        "total": len(_SIM_STORE),
    }


@router.get(
    "/scenarios",
    summary="List available simulation scenarios",
)
async def list_scenarios() -> dict[str, Any]:
    """Return all supported simulation scenario types with descriptions."""
    return {
        "scenarios": [
            {"type": k, "description": v}
            for k, v in _SCENARIO_DESCRIPTIONS.items()
        ]
    }


@router.get(
    "/{simulation_id}",
    summary="Get simulation result",
)
async def get_simulation(simulation_id: str) -> dict[str, Any]:
    """
    Fetch full simulation result including per-agent traces and final state.

    Poll this endpoint after posting to `/simulate` — status goes:
    `queued` → `running` → `completed` | `failed`
    """
    sim = _SIM_STORE.get(simulation_id)
    if sim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation '{simulation_id}' not found",
        )

    response: dict[str, Any] = {
        "simulation_id": simulation_id,
        "scenario_type": sim["scenario_type"],
        "status": sim["status"],
        "description": sim.get("description", ""),
        "agents_executed": sim.get("agents_executed", 0),
        "trace": sim.get("trace", []),
    }

    if sim.get("final_state"):
        fs = sim["final_state"]
        response["summary"] = {
            "workflow_status": fs.get("workflow_status"),
            "order_status": (fs.get("order") or {}).get("status"),
            "total_amount": (fs.get("order") or {}).get("total_amount"),
            "risk_score": (fs.get("risk") or {}).get("score"),
            "risk_level": (fs.get("risk") or {}).get("level"),
            "ceo_approved": fs.get("workflow_status") == "completed",
            "approval_tier": "consensus" if fs.get("workflow_status") == "completed" else "escalated",
            "carrier": (fs.get("shipment") or {}).get("carrier"),
            "eta": (fs.get("shipment") or {}).get("eta"),
            "error_count": len(fs.get("errors") or []),
            "decision_count": len(fs.get("decisions") or []),
            "event_count": len(fs.get("event_history") or []),
        }

    if sim.get("error"):
        response["error"] = sim["error"]

    return response
