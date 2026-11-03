"""Persistent local storage engine for Supply Chain Digital Twin.

Provides SQLite-backed persistence so workflows, simulations, orders, and
events survive server reloads, worker restarts, and browser page refreshes.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Storage directory in backend/.storage
STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / ".storage"
DB_PATH = STORAGE_DIR / "digital_twin.db"


def _get_connection() -> sqlite3.Connection:
    """Acquire a thread-safe connection to the SQLite persistent database."""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def init_db() -> None:
    """Initialize SQLite database tables and seed baseline data if empty."""
    with _get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS workflows (
                workflow_id TEXT PRIMARY KEY,
                correlation_id TEXT,
                status TEXT,
                state_json TEXT,
                trace_json TEXT,
                created_at TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS simulations (
                simulation_id TEXT PRIMARY KEY,
                scenario_type TEXT,
                status TEXT,
                description TEXT,
                data_json TEXT,
                created_at TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT,
                source_agent TEXT,
                workflow_id TEXT,
                payload_json TEXT,
                timestamp TEXT,
                status TEXT
            );

            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                customer_id TEXT,
                customer_name TEXT,
                status TEXT,
                priority TEXT,
                total_amount TEXT,
                currency TEXT,
                workflow_id TEXT,
                created_at TEXT
            );
            """
        )

        # Seed baseline orders if table is empty
        cur = conn.execute("SELECT COUNT(*) as count FROM orders")
        if cur.fetchone()["count"] == 0:
            now_iso = datetime.now(timezone.utc).isoformat()
            baseline_orders = [
                (
                    "ord00000-0000-0000-0000-000000000001",
                    "cust0000-0000-0000-0000-000000000001",
                    "Tesla Energy Solutions",
                    "delivered",
                    "high",
                    "45200.00",
                    "USD",
                    "wf000000-0000-0000-0000-000000000001",
                    "2026-11-02T08:00:00Z",
                ),
                (
                    "ord00000-0000-0000-0000-000000000002",
                    "cust0000-0000-0000-0000-000000000002",
                    "Siemens Robotics Global",
                    "in_transit",
                    "medium",
                    "28400.00",
                    "USD",
                    "wf000000-0000-0000-0000-000000000002",
                    "2026-11-02T09:30:00Z",
                ),
                (
                    "ord00000-0000-0000-0000-000000000003",
                    "cust0000-0000-0000-0000-000000000003",
                    "Schneider Power Grid",
                    "pending",
                    "high",
                    "89000.00",
                    "USD",
                    None,
                    "2026-11-02T10:15:00Z",
                ),
                (
                    "ord00000-0000-0000-0000-000000000004",
                    "cust0000-0000-0000-0000-000000000004",
                    "Honeywell Industrial Automations",
                    "delivered",
                    "low",
                    "14300.00",
                    "USD",
                    "wf000000-0000-0000-0000-000000000003",
                    "2026-11-01T15:45:00Z",
                ),
            ]
            conn.executemany(
                """
                INSERT OR IGNORE INTO orders (
                    order_id, customer_id, customer_name, status, priority,
                    total_amount, currency, workflow_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                baseline_orders,
            )

        # Seed baseline events if empty
        cur = conn.execute("SELECT COUNT(*) as count FROM events")
        if cur.fetchone()["count"] == 0:
            now_iso = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """
                INSERT OR IGNORE INTO events (
                    event_id, event_type, source_agent, workflow_id,
                    payload_json, timestamp, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    "SystemInitialized",
                    "system",
                    None,
                    json.dumps({"message": "Digital Twin persistent engine active"}),
                    now_iso,
                    "completed",
                ),
            )


# Initialize DB immediately on module import
init_db()


# ── Workflow Persistence ───────────────────────────────────────────────────────

def save_workflow(
    workflow_id: str,
    state: dict[str, Any],
    trace: list[dict[str, Any]] | None = None,
) -> None:
    """Save or update workflow state and execution trace in persistent storage."""
    now_iso = datetime.now(timezone.utc).isoformat()
    status_val = str(state.get("workflow_status") or "running")
    correlation_id = str(state.get("correlation_id") or "")
    state_str = json.dumps(state, default=str)

    with _get_connection() as conn:
        if trace is not None:
            trace_str = json.dumps(trace, default=str)
            conn.execute(
                """
                INSERT INTO workflows (workflow_id, correlation_id, status, state_json, trace_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(workflow_id) DO UPDATE SET
                    status = excluded.status,
                    state_json = excluded.state_json,
                    trace_json = excluded.trace_json,
                    updated_at = excluded.updated_at
                """,
                (workflow_id, correlation_id, status_val, state_str, trace_str, now_iso, now_iso),
            )
        else:
            conn.execute(
                """
                INSERT INTO workflows (workflow_id, correlation_id, status, state_json, trace_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, '[]', ?, ?)
                ON CONFLICT(workflow_id) DO UPDATE SET
                    status = excluded.status,
                    state_json = excluded.state_json,
                    updated_at = excluded.updated_at
                """,
                (workflow_id, correlation_id, status_val, state_str, now_iso, now_iso),
            )

        # If order exists in state, persist to orders table
        order = state.get("order")
        if order and isinstance(order, dict) and order.get("order_id"):
            items = order.get("items") or []
            calc_tot = sum(
                float(it.get("line_total") or (float(it.get("unit_price") or 150) * float(it.get("quantity") or 1)))
                for it in items
            )
            raw_tot = order.get("total_amount")
            final_total_amt = f"{float(raw_tot):.2f}" if raw_tot is not None and float(raw_tot) > 0 else (f"{calc_tot:.2f}" if calc_tot > 0 else "0.00")
            derived_status = str(order.get("status") or ("delivered" if state.get("workflow_status") == "completed" else "in_transit"))
            derived_priority = str(order.get("priority") or "standard")
            cust_name = state.get("customer", {}).get("name") if isinstance(state.get("customer"), dict) else "Enterprise Customer"

            conn.execute(
                """
                INSERT INTO orders (order_id, customer_id, customer_name, status, priority, total_amount, currency, workflow_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(order_id) DO UPDATE SET
                    status = excluded.status,
                    priority = excluded.priority,
                    total_amount = excluded.total_amount
                """,
                (
                    str(order.get("order_id")),
                    str(order.get("customer_id") or "00000000-0000-0000-0000-000000000001"),
                    cust_name,
                    derived_status,
                    derived_priority,
                    final_total_amt,
                    str(order.get("currency") or "USD"),
                    workflow_id,
                    now_iso,
                ),
            )

        # Persist event history if present
        events = state.get("event_history")
        if events and isinstance(events, list):
            for ev in events:
                if isinstance(ev, dict):
                    ev_type = ev.get("event_type") or "WorkflowEvent"
                    ev_src = ev.get("source_agent") or "system"
                    ev_payload = json.dumps(ev.get("payload") or {}, default=str)
                    ev_ts = ev.get("timestamp") or now_iso
                    ev_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{workflow_id}:{ev_type}:{ev_ts}"))
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO events (
                            event_id, event_type, source_agent, workflow_id,
                            payload_json, timestamp, status
                        ) VALUES (?, ?, ?, ?, ?, ?, 'completed')
                        """,
                        (ev_id, ev_type, ev_src, workflow_id, ev_payload, ev_ts),
                    )


def get_workflow(workflow_id: str) -> dict[str, Any] | None:
    """Retrieve workflow state from persistent database."""
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT state_json FROM workflows WHERE workflow_id = ?",
            (workflow_id,),
        ).fetchone()
        if row and row["state_json"]:
            try:
                return json.loads(row["state_json"])
            except Exception:
                return None
    return None


def get_workflow_trace(workflow_id: str) -> list[dict[str, Any]]:
    """Retrieve per-agent traces for a workflow from persistent database."""
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT trace_json FROM workflows WHERE workflow_id = ?",
            (workflow_id,),
        ).fetchone()
        if row and row["trace_json"]:
            try:
                return json.loads(row["trace_json"])
            except Exception:
                return []
    return []


def list_workflows(limit: int = 50) -> list[dict[str, Any]]:
    """List recent workflows with summary metadata."""
    with _get_connection() as conn:
        rows = conn.execute(
            """
            SELECT workflow_id, correlation_id, status, created_at, updated_at, state_json
            FROM workflows
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        items = []
        for r in rows:
            st = {}
            if r["state_json"]:
                try:
                    st = json.loads(r["state_json"])
                except Exception:
                    pass
            order = st.get("order") or {}
            items.append({
                "workflow_id": r["workflow_id"],
                "correlation_id": r["correlation_id"],
                "workflow_status": r["status"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "order_id": order.get("order_id"),
                "customer_id": order.get("customer_id"),
                "total_amount": str(order.get("total_amount") or "0.00"),
                "order_status": order.get("status"),
                "requires_human_approval": bool(st.get("requires_human_approval")),
                "active_agents": st.get("active_agents") or [],
                "event_count": len(st.get("event_history") or []),
                "error_count": len(st.get("errors") or []),
            })
        return items


# ── Simulation Persistence ─────────────────────────────────────────────────────

def save_simulation(simulation_id: str, data: dict[str, Any]) -> None:
    """Save simulation run state and traces to persistent database."""
    now_iso = datetime.now(timezone.utc).isoformat()
    scenario_type = data.get("scenario_type") or "unknown"
    sim_status = data.get("status") or "queued"
    desc = data.get("description") or ""
    data_str = json.dumps(data, default=str)

    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO simulations (simulation_id, scenario_type, status, description, data_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(simulation_id) DO UPDATE SET
                status = excluded.status,
                description = excluded.description,
                data_json = excluded.data_json,
                updated_at = excluded.updated_at
            """,
            (simulation_id, scenario_type, sim_status, desc, data_str, now_iso, now_iso),
        )


def get_simulation(simulation_id: str) -> dict[str, Any] | None:
    """Retrieve simulation run data from persistent database."""
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT data_json FROM simulations WHERE simulation_id = ?",
            (simulation_id,),
        ).fetchone()
        if row and row["data_json"]:
            try:
                return json.loads(row["data_json"])
            except Exception:
                return None
    return None


def list_simulations(limit: int = 50) -> list[dict[str, Any]]:
    """List recent simulation runs from persistent database."""
    with _get_connection() as conn:
        rows = conn.execute(
            """
            SELECT simulation_id, scenario_type, status, description, updated_at, data_json
            FROM simulations
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        items = []
        for r in rows:
            agents_executed = 0
            if r["data_json"]:
                try:
                    d = json.loads(r["data_json"])
                    agents_executed = d.get("agents_executed", len(d.get("trace", [])))
                except Exception:
                    pass
            items.append({
                "simulation_id": r["simulation_id"],
                "scenario_type": r["scenario_type"],
                "status": r["status"],
                "description": r["description"],
                "agents_executed": agents_executed,
                "updated_at": r["updated_at"],
            })
        return items


# ── Events Persistence ─────────────────────────────────────────────────────────

def save_event(event: dict[str, Any]) -> None:
    """Persist an individual event record."""
    ev_id = str(event.get("event_id") or uuid.uuid4())
    ev_type = str(event.get("event_type") or "GenericEvent")
    src = str(event.get("source_agent") or "system")
    wf_id = event.get("workflow_id")
    payload_str = json.dumps(event.get("payload") or {}, default=str)
    ts = str(event.get("timestamp") or datetime.now(timezone.utc).isoformat())
    ev_status = str(event.get("status") or "completed")

    with _get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO events (
                event_id, event_type, source_agent, workflow_id,
                payload_json, timestamp, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (ev_id, ev_type, src, wf_id, payload_str, ts, ev_status),
        )


def list_events(limit: int = 100, event_type: str | None = None) -> list[dict[str, Any]]:
    """Retrieve recent event history from persistent storage."""
    with _get_connection() as conn:
        if event_type:
            rows = conn.execute(
                """
                SELECT event_id, event_type, source_agent, workflow_id, payload_json, timestamp, status
                FROM events
                WHERE event_type = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (event_type, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT event_id, event_type, source_agent, workflow_id, payload_json, timestamp, status
                FROM events
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        items = []
        for r in rows:
            payload = {}
            if r["payload_json"]:
                try:
                    payload = json.loads(r["payload_json"])
                except Exception:
                    pass
            items.append({
                "event_id": r["event_id"],
                "event_type": r["event_type"],
                "source_agent": r["source_agent"],
                "workflow_id": r["workflow_id"],
                "payload": payload,
                "timestamp": r["timestamp"],
                "status": r["status"],
            })
        return items


# ── Orders Persistence ─────────────────────────────────────────────────────────

def save_order(order: dict[str, Any]) -> None:
    """Save an order record to the persistent database."""
    now_iso = datetime.now(timezone.utc).isoformat()
    ord_id = str(order.get("order_id") or uuid.uuid4())
    cust_id = str(order.get("customer_id") or uuid.uuid4())
    cust_name = str(order.get("customer_name") or "Enterprise Client")
    status_val = str(order.get("status") or "pending")
    priority_val = str(order.get("priority") or "standard")
    total_val = str(order.get("total_amount") or "0.00")
    curr_val = str(order.get("currency") or "USD")
    wf_id = order.get("workflow_id")
    created_at_val = str(order.get("created_at") or now_iso)

    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO orders (
                order_id, customer_id, customer_name, status, priority,
                total_amount, currency, workflow_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(order_id) DO UPDATE SET
                status = excluded.status,
                priority = excluded.priority,
                total_amount = excluded.total_amount
            """,
            (ord_id, cust_id, cust_name, status_val, priority_val, total_val, curr_val, wf_id, created_at_val),
        )


def get_order(order_id: str) -> dict[str, Any] | None:
    """Retrieve full order detail including line items from persistent storage."""
    with _get_connection() as conn:
        row = conn.execute(
            """
            SELECT order_id, customer_id, customer_name, status, priority, total_amount, currency, workflow_id, created_at
            FROM orders
            WHERE order_id = ?
            """,
            (order_id,),
        ).fetchone()
        if not row:
            return None

        # If order was created by a workflow, recover line items from workflow state
        items: list[dict[str, Any]] = []
        if row["workflow_id"]:
            wf_row = conn.execute(
                "SELECT state_json FROM workflows WHERE workflow_id = ?",
                (row["workflow_id"],),
            ).fetchone()
            if wf_row and wf_row["state_json"]:
                try:
                    wf_st = json.loads(wf_row["state_json"])
                    raw_items = (wf_st.get("order") or {}).get("items") or []
                    for idx, it in enumerate(raw_items):
                        u_price = float(it.get("unit_price") or 150.0)
                        qty = int(it.get("quantity") or 1)
                        l_total = float(it.get("line_total") or (u_price * qty))
                        items.append({
                            "order_item_id": it.get("order_item_id") or f"item-{row['order_id'][:8]}-{idx+1}",
                            "product_id": it.get("product_id") or "30000000-0000-0000-0000-000000000001",
                            "product_name": it.get("product_name") or "Industrial Sensor Module",
                            "sku": it.get("sku") or "ELEC-001",
                            "quantity": qty,
                            "unit_price": f"{u_price:.2f}",
                            "line_total": f"{l_total:.2f}",
                        })
                except Exception:
                    pass

        # Fallback line items if no workflow state was found
        if not items:
            tot = float(row["total_amount"] or 0)
            items = [
                {
                    "order_item_id": f"item-{row['order_id'][:8]}-1",
                    "product_id": "30000000-0000-0000-0000-000000000001",
                    "product_name": "Industrial Component System",
                    "sku": "SKU-001",
                    "quantity": 1,
                    "unit_price": f"{tot:.2f}",
                    "line_total": f"{tot:.2f}",
                }
            ]

        return {
            "order_id": row["order_id"],
            "customer_id": row["customer_id"],
            "customer": {
                "name": row["customer_name"],
                "tier": row["priority"],
                "email": f"contact@{row['customer_name'].lower().replace(' ', '')}.com",
            },
            "status": row["status"],
            "priority": row["priority"],
            "total_amount": row["total_amount"],
            "currency": row["currency"],
            "workflow_id": row["workflow_id"],
            "created_at": row["created_at"],
            "items": items,
        }


def list_orders(
    skip: int = 0,
    limit: int = 50,
    status_filter: str | None = None,
    priority_filter: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """List orders with pagination and filtering from persistent storage."""
    with _get_connection() as conn:
        conditions = []
        params: list[Any] = []
        if status_filter:
            conditions.append("status = ?")
            params.append(status_filter)
        if priority_filter:
            conditions.append("priority = ?")
            params.append(priority_filter)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        count_sql = f"SELECT COUNT(*) as total FROM orders {where_clause}"
        total = conn.execute(count_sql, params).fetchone()["total"]

        sql = f"""
            SELECT order_id, customer_id, customer_name, status, priority, total_amount, currency, workflow_id, created_at
            FROM orders
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        rows = conn.execute(sql, [*params, limit, skip]).fetchall()

        items = [
            {
                "order_id": r["order_id"],
                "customer_id": r["customer_id"],
                "customer_name": r["customer_name"],
                "status": r["status"],
                "priority": r["priority"],
                "total_amount": r["total_amount"],
                "currency": r["currency"],
                "workflow_id": r["workflow_id"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
        return items, total


def get_dashboard_metrics() -> dict[str, Any]:
    """Aggregate KPIs and recent orders from persistent storage."""
    with _get_connection() as conn:
        orders_rows = conn.execute("SELECT status, total_amount, priority, order_id, created_at FROM orders").fetchall()

        total_orders = len(orders_rows)
        total_revenue = sum(float(r["total_amount"] or 0) for r in orders_rows)
        status_counts: dict[str, int] = {}
        priority_counts: dict[str, int] = {}
        for r in orders_rows:
            st = r["status"]
            status_counts[st] = status_counts.get(st, 0) + 1
            pr = r["priority"] or "standard"
            priority_counts[pr] = priority_counts.get(pr, 0) + 1

        delivered = status_counts.get("delivered", 0)
        fill_rate = round(100.0 * delivered / max(total_orders, 1), 1)

        recent_orders_rows = conn.execute(
            """
            SELECT order_id, status, priority, total_amount, created_at
            FROM orders
            ORDER BY created_at DESC
            LIMIT 10
            """
        ).fetchall()

        recent_orders = [
            {
                "order_id": r["order_id"],
                "status": r["status"],
                "priority": r["priority"],
                "total_amount": r["total_amount"],
                "created_at": r["created_at"],
            }
            for r in recent_orders_rows
        ]

        from app.api.v1.inventory import compute_inventory_summary, _FALLBACK_INVENTORY
        inv_summary = compute_inventory_summary(_FALLBACK_INVENTORY)

        return {
            "kpis": {
                "total_orders": total_orders,
                "total_revenue": f"{total_revenue:.2f}",
                "delivered_orders": delivered,
                "fill_rate_pct": fill_rate,
                "active_suppliers": 4,
                "avg_supplier_reliability": 89.5,
                "low_stock_alerts": inv_summary["low_stock_locations"],
                "out_of_stock_alerts": inv_summary["out_of_stock_locations"],
                "total_inventory_locations": inv_summary["total_sku_locations"],
                "sku_availability_pct": inv_summary["fill_rate_pct"],
                "total_agents": 18,
            },
            "orders_by_status": status_counts,
            "orders_by_priority": priority_counts,
            "recent_orders": recent_orders,
        }
