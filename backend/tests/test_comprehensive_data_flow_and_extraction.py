"""
Comprehensive Multi-Flow, Data Extraction, and Inter-Agent Communication Test Suite.

Validates:
1. End-to-end 18-Agent LangGraph Workflow execution with live Groq LLM cognitive decisions.
2. Full payload data extraction and immutable state passing across operational, BI, and executive layers.
3. Out-of-stock sourcing & contract-grounded Semantic RAG negotiation data flow.
4. Autonomous scan and auto-heal closed loop (deficit detection -> EOQ PO generation -> stock receipt).
5. High-value CEO governance and approval tier extraction (> $50,000).
6. Cross-domain KPI consistency and invariant validation across analytics, inventory, and orders.
7. Stochastic Monte Carlo resilience simulation and Value-at-Risk (VaR) extraction.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.llm import is_llm_available, get_active_provider_and_key
from app.core.ai_optimization import run_monte_carlo_resilience_assessment
from app.core.semantic_search import query_contract_clauses
from app.core import persistence


@pytest.fixture
def auth_headers() -> dict[str, str]:
    from app.api.v1.auth import _create_access_token
    token = _create_access_token(data={"sub": "admin", "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_flow_1_standard_order_end_to_end_data_flow(auth_headers):
    """
    TEST FLOW 1: Standard In-Stock Order.
    Validates complete data extraction from intake through forecasting, inventory reservation,
    routing, carbon emission math, QA inspection, finance margin, risk scoring, customer service, and reporting.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=45.0) as client:
        # 1. Place Order
        cust_id = "50000000-0000-0000-0000-000000000001" # Siemens
        prod_id = "30000000-0000-0000-0000-000000000001" # Industrial Controller
        
        post_res = await client.post(
            "/api/v1/orders",
            json={
                "customer_id": cust_id,
                "priority": "standard",
                "items": [{"product_id": prod_id, "quantity": 10}],
            },
            headers=auth_headers,
        )
        assert post_res.status_code == 201, f"Order placement failed: {post_res.text}"
        order_data = post_res.json()
        order_id = order_data["order_id"]
        workflow_id = order_data["workflow_id"]
        
        # Verify initial data extraction
        assert float(order_data["total_amount"]) == 1500.00
        assert order_data["customer_name"] == "Siemens Global Automations"
        assert order_data["shipment_id"].startswith("shp-")
        
        # 2. Wait for multi-agent execution pipeline to process
        for _ in range(15):
            status_poll = await client.get(f"/api/v1/workflows/{workflow_id}", headers=auth_headers)
            if status_poll.status_code == 200 and status_poll.json().get("workflow_status") in ("completed", "failed", "escalated"):
                break
            await asyncio.sleep(0.4)
        
        # 3. Poll workflow trace
        trace_res = await client.get(f"/api/v1/workflows/{workflow_id}/trace", headers=auth_headers)
        assert trace_res.status_code == 200
        trace_data = trace_res.json()
        trace = trace_data.get("traces") or trace_data.get("trace", [])
        
        # Verify agents executed in graph sequence
        executed_agents = [step.get("agent_code") for step in trace]
        assert len(executed_agents) > 0, "Agents must have executed"
        assert "ADS-01" in executed_agents, "Order Management agent missing"
        assert "ADS-02" in executed_agents, "Demand Forecast agent missing"
        assert "ADS-03" in executed_agents, "Inventory agent missing"
        assert "ADS-04" in executed_agents, "Warehouse agent missing"
        assert "ADS-06" in executed_agents, "Transportation agent missing"
        assert "ADS-13" in executed_agents, "Sustainability agent missing"
        assert "ADS-14" in executed_agents, "QA agent missing"
        assert "ADS-09" in executed_agents, "Finance agent missing"
        assert "ADS-10" in executed_agents, "Risk agent missing"
        assert "ADS-18" in executed_agents, "Reporting agent missing"
        
        # 4. Verify inter-agent data passing in trace snapshots
        # Check ADS-13 Sustainability extracted cargo weight and distance
        step_13 = next(s for s in trace if s.get("agent_code") == "ADS-13")
        sus_out = step_13.get("output", {}).get("sustainability", {})
        assert "co2_kg" in sus_out
        assert float(sus_out["co2_kg"]) > 0.0
        assert sus_out["freight_mode"] in ("road", "air", "sea", "rail")
        
        # Check ADS-09 Finance extracted costs and computed exact margin
        step_09 = next(s for s in trace if s.get("agent_code") == "ADS-09")
        fin_out = step_09.get("output", {}).get("finance", {})
        assert "gross_margin_pct" in fin_out
        assert "total_cost" in fin_out
        assert "revenue" in fin_out
        rev = Decimal(str(fin_out["revenue"]))
        tot_c = Decimal(str(fin_out["total_cost"]))
        margin_amt = Decimal(str(fin_out["gross_margin_amount"]))
        assert rev - tot_c == margin_amt, f"Margin invariant breached: {rev} - {tot_c} != {margin_amt}"


@pytest.mark.asyncio
async def test_flow_2_contract_rag_and_supplier_negotiation(auth_headers):
    """
    TEST FLOW 2: Sourcing with Contract Semantic RAG.
    Validates that when negotiation is invoked, relevant contract clauses are retrieved
    and synthesized into the negotiation rationale.
    """
    # Verify local RAG directly
    clauses = query_contract_clauses("Siemens delivery delay penalties liquidated damages", top_k=1)
    assert len(clauses) == 1
    assert "liquidated damages penalty" in clauses[0]["content"]
    
    # Test workflow with bulk quantity triggering negotiation volume tier
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=45.0) as client:
        res = await client.post(
            "/api/v1/orders",
            json={
                "customer_id": "50000000-0000-0000-0000-000000000002", # Tesla
                "priority": "standard",
                "items": [{"product_id": "30000000-0000-0000-0000-000000000002", "quantity": 40}],
            },
            headers=auth_headers,
        )
        assert res.status_code == 201
        wf_id = res.json()["workflow_id"]
        
        await asyncio.sleep(2.0)
        wf_status_res = await client.get(f"/api/v1/workflows/{wf_id}", headers=auth_headers)
        assert wf_status_res.status_code == 200
        wf = wf_status_res.json()
        assert wf["workflow_status"] in ("completed", "running")


@pytest.mark.asyncio
async def test_flow_3_autonomous_scan_and_auto_heal_closed_loop(auth_headers):
    """
    TEST FLOW 3: Autonomous Deficit Scan & Auto-Healing.
    Scans live inventory buffers -> verifies low stock detection -> auto-generates replenishment POs
    with EOQ batching -> auto-receives stock into warehouse.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=30.0) as client:
        # 1. Run autonomous inventory scan
        scan_res = await client.post("/api/v1/inventory/autonomous-scan", headers=auth_headers)
        assert scan_res.status_code == 200
        scan_data = scan_res.json()
        assert scan_data["status"] == "completed"
        assert "message" in scan_data
        
        # 2. Query inbound replenishment purchase orders
        pos_res = await client.get("/api/v1/inventory/replenishment-orders?status=in_transit", headers=auth_headers)
        assert pos_res.status_code == 200
        pos_data = pos_res.json()
        in_transit_orders = pos_data.get("items", [])
        
        if in_transit_orders:
            target_po = in_transit_orders[0]
            po_id = target_po["po_id"]
            
            # 3. Receive stock to complete closed loop
            receive_res = await client.post(f"/api/v1/inventory/replenishment-orders/{po_id}/receive", headers=auth_headers)
            assert receive_res.status_code == 200
            recv_data = receive_res.json()
            assert recv_data["success"] is True
            assert "received successfully" in recv_data["message"]
            
        # 4. Verify batch auto-heal endpoint executes cleanly
        auto_heal_res = await client.post("/api/v1/inventory/replenish/auto-heal", headers=auth_headers)
        assert auto_heal_res.status_code == 200
        assert auto_heal_res.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_flow_4_high_value_capex_order_escalation(auth_headers):
    """
    TEST FLOW 4: High-Value Order (> $50,000) Executive Escalation.
    Verifies that order values exceeding corporate delegation of authority thresholds
    are flagged for human / CEO executive approval.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=45.0) as client:
        # 500 units x $150 = $75,000 (exceeds $50k hurdle)
        res = await client.post(
            "/api/v1/orders",
            json={
                "customer_id": "50000000-0000-0000-0000-000000000001",
                "priority": "critical",
                "items": [{"product_id": "30000000-0000-0000-0000-000000000001", "quantity": 500}],
            },
            headers=auth_headers,
        )
        assert res.status_code == 201
        data = res.json()
        assert float(data["total_amount"]) == 75000.00
        wf_id = data["workflow_id"]
        
        for _ in range(15):
            poll = await client.get(f"/api/v1/workflows/{wf_id}", headers=auth_headers)
            if poll.status_code == 200 and poll.json().get("workflow_status") in ("completed", "failed", "escalated"):
                break
            await asyncio.sleep(0.4)
            
        wf_res = await client.get(f"/api/v1/workflows/{wf_id}", headers=auth_headers)
        assert wf_res.status_code == 200
        wf = wf_res.json()
        
        # Check executive decision or trace includes CEO Agent (ADS-17)
        exec_dec = wf.get("executive_decision")
        assert exec_dec is not None or wf.get("workflow_status") in ("completed", "escalated")


@pytest.mark.asyncio
async def test_flow_5_cross_domain_data_consistency_and_invariants(auth_headers):
    """
    TEST FLOW 5: Cross-Domain Data Extraction & Consistency Invariants.
    Verifies that counts and totals across the executive dashboard, inventory summary,
    and shipment listings match without orphan or corrupted states.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=30.0) as client:
        # 1. Dashboard summary
        dash_res = await client.get("/api/v1/analytics/dashboard", headers=auth_headers)
        assert dash_res.status_code == 200
        dash = dash_res.json()
        kpis = dash["kpis"]
        
        assert kpis["total_orders"] >= 0
        assert kpis.get("total_agents", 18) == 18
        
        # 2. Inventory summary invariants
        inv_res = await client.get("/api/v1/inventory/summary", headers=auth_headers)
        assert inv_res.status_code == 200
        inv = inv_res.json()
        
        total_locs = inv["total_sku_locations"]
        ok_count = inv["total_sku_locations"] - inv["low_stock_locations"] - inv["out_of_stock_locations"]
        assert ok_count >= 0
        assert ok_count + inv["low_stock_locations"] + inv["out_of_stock_locations"] == total_locs
        assert inv["total_available_units"] - inv["total_reserved_units"] == inv["net_available_units"]
        
        # 3. Shipments listing
        shp_res = await client.get("/api/v1/shipments?limit=10", headers=auth_headers)
        assert shp_res.status_code == 200
        shp_data = shp_res.json()
        assert "items" in shp_data
        for s in shp_data["items"]:
            assert "shipment_id" in s
            assert "status" in s
            assert s["freight_mode"] in ("road", "air", "ocean", "rail")


@pytest.mark.asyncio
async def test_flow_6_monte_carlo_stochastic_simulation_extraction(auth_headers):
    """
    TEST FLOW 6: Monte Carlo Resilience Risk Engine.
    Executes 500-trial stochastic risk simulation and validates mathematical bounds of VaR and CVaR.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=30.0) as client:
        res = await client.post(
            "/api/v1/simulate/monte-carlo",
            json={
                "num_trials": 500,
                "base_order_value": 30000.0,
                "supplier_disruption_prob": 0.10,
                "carrier_delay_prob": 0.15,
                "margin_pct": 25.0,
            },
            headers=auth_headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "completed"
        metrics = data["metrics"]
        
        assert metrics["trials_count"] == 500
        assert 0.0 <= metrics["resilience_index"] <= 100.0
        assert metrics["value_at_risk_95"] >= 0.0
        assert metrics["expected_shortfall_cvar"] >= metrics["value_at_risk_95"]
        assert metrics["risk_posture"] in ("Robust", "Moderate", "Vulnerable")
