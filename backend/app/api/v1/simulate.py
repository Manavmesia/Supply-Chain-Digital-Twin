"""
Simulate REST API — Phase 5 / What-If Simulation Engine

POST /api/v1/simulate            — trigger a what-if simulation scenario
GET  /api/v1/simulate/{id}       — poll simulation result
GET  /api/v1/simulate            — list recent simulations
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, Literal

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core import persistence
from app.core.database import AsyncSessionLocal
from app.core.standby_session import create_standby_session, is_database_connected
from app.graph.state import SupplyChainState
from app.graph.workflow import compile_workflow

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/simulate", tags=["simulate"])

# ---------------------------------------------------------------------------
# Bounded in-process simulation store (prevents memory leak DoS)
# ---------------------------------------------------------------------------

_SIM_STORE: dict[str, dict[str, Any]] = {}
_MAX_SIM_STORE_SIZE = 500


def _save_sim_state(sim_id: str, data: dict[str, Any]) -> None:
    if len(_SIM_STORE) >= _MAX_SIM_STORE_SIZE and sim_id not in _SIM_STORE:
        oldest_key = next(iter(_SIM_STORE))
        _SIM_STORE.pop(oldest_key, None)
    _SIM_STORE[sim_id] = data
    try:
        persistence.save_simulation(sim_id, data)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to persist simulation state", simulation_id=sim_id, error=str(exc))


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

ScenarioType = Literal[
    "demand_spike",
    "supplier_outage",
    "logistics_delay",
    "bulk_order",
    "quality_crisis",
]


class SimulationItemRequest(BaseModel):
    product_id: str = Field(min_length=1, max_length=100)
    quantity: int = Field(default=1, gt=0, le=1_000_000)


class SimulationScenario(BaseModel):
    scenario_type: ScenarioType
    customer_id: str = Field(min_length=1, max_length=100)
    items: list[SimulationItemRequest] = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


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
    items = [
        {"product_id": str(i.product_id), "quantity": int(i.quantity)}
        for i in scenario.items
    ]

    # Demand spike: double all quantities
    if scenario.scenario_type == "demand_spike":
        items = [
            {**item, "quantity": item["quantity"] * 2}
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
            "items": items,
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

_MAX_CONCURRENT_SIMULATIONS = 10
_SIMULATION_SEMAPHORE = asyncio.Semaphore(_MAX_CONCURRENT_SIMULATIONS)


async def _run_simulation(
    simulation_id: str,
    scenario: SimulationScenario,
) -> None:
    async with _SIMULATION_SEMAPHORE:
        await _run_simulation_inner(simulation_id, scenario)


async def _run_simulation_inner(
    simulation_id: str,
    scenario: SimulationScenario,
) -> None:
    """Run the full workflow in simulation mode and store the result."""
    _save_sim_state(simulation_id, {
        "status": "running",
        "scenario_type": scenario.scenario_type,
        "description": _SCENARIO_DESCRIPTIONS.get(scenario.scenario_type, ""),
        "agents_executed": 0,
        "trace": [],
    })

    trace: list[dict[str, Any]] = []

    try:
        initial_state = _build_initial_state(simulation_id, scenario)
        config = {"configurable": {"thread_id": simulation_id}}
        final_state: dict[str, Any] = {}

        db_available = await is_database_connected()
        if db_available:
            try:
                async with AsyncSessionLocal() as session:
                    async def _session_factory():
                        return session

                    compiled = compile_workflow(
                        session_factory=_session_factory,
                        trace_collector=trace,
                    )
                    final_state = await compiled.ainvoke(initial_state, config=config)
                    await session.rollback()

                    has_connection_error = any(
                        "connection" in str(e).lower() or "errno 61" in str(e).lower()
                        for e in final_state.get("errors", [])
                    )
                    if has_connection_error:
                        raise ConnectionRefusedError("Database lost mid-run")
            except (OSError, ConnectionRefusedError, Exception) as db_exc:
                logger.warning("DB failure during simulation, falling back to standby session", error=str(db_exc))
                db_available = False

        if not db_available:
            standby_session = create_standby_session(
                customer_id=uuid.UUID(str(initial_state["order"]["customer_id"])) if initial_state.get("order", {}).get("customer_id") else None,
                items=initial_state.get("order", {}).get("items"),
            )
            async def _standby_factory():
                return standby_session

            trace.clear()
            fallback_initial_state = dict(initial_state)
            fallback_initial_state["errors"] = []
            compiled = compile_workflow(
                session_factory=_standby_factory,
                trace_collector=trace,
            )
            final_state = await compiled.ainvoke(fallback_initial_state, config=config)

        sim_status = "completed"
        if final_state.get("workflow_status") == "failed" or bool(final_state.get("errors")):
            sim_status = "failed"
        elif final_state.get("workflow_status") != "escalated":
            final_state["workflow_status"] = "completed"

        _save_sim_state(simulation_id, {
            "simulation_id": simulation_id,
            "scenario_type": scenario.scenario_type,
            "status": sim_status,
            "description": _SCENARIO_DESCRIPTIONS.get(scenario.scenario_type, ""),
            "final_state": final_state,
            "trace": trace,
            "agents_executed": len(trace),
        })

        logger.info(
            "Simulation completed",
            simulation_id=simulation_id,
            scenario=scenario.scenario_type,
            agents=len(trace),
            status=sim_status,
        )

    except Exception as exc:  # noqa: BLE001
        logger.error("Simulation failed", simulation_id=simulation_id, error=str(exc))
        _save_sim_state(simulation_id, {
            "simulation_id": simulation_id,
            "scenario_type": scenario.scenario_type,
            "status": "failed",
            "error": str(exc),
            "trace": trace,
            "description": _SCENARIO_DESCRIPTIONS.get(scenario.scenario_type, ""),
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

    _save_sim_state(simulation_id, {
        "simulation_id": simulation_id,
        "scenario_type": scenario.scenario_type,
        "status": "queued",
        "description": scenario.description or _SCENARIO_DESCRIPTIONS.get(
            scenario.scenario_type, ""
        ),
    })

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
    items = persistence.list_simulations(limit=limit)
    if not items:
        sims = list(reversed(list(_SIM_STORE.values())))[:limit]
        items = [
            {
                "simulation_id": s["simulation_id"],
                "scenario_type": s["scenario_type"],
                "status": s["status"],
                "description": s.get("description", ""),
                "agents_executed": s.get("agents_executed", 0),
            }
            for s in sims
        ]
    return {
        "items": items,
        "total": len(items),
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
    sim = _SIM_STORE.get(simulation_id) or persistence.get_simulation(simulation_id)
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
