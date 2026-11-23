"""
Verification Test Suite for Free In-Process AI Capabilities:
1. Double Exponential Smoothing (Holt's Linear Trend) Demand Forecasting.
2. Dynamic Lead-Time and Demand Volatility Safety Stock (Bayesian modeling).
3. Wilson Economic Order Quantity (EOQ) replenishment batching.
4. Stochastic Monte Carlo Supply Chain Resilience and Value-at-Risk (VaR 95%).
5. Zero-Cost Semantic Document RAG Retrieval over supplier contracts and SOPs.
6. API endpoint verification for /api/v1/simulate/monte-carlo.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.ai_optimization import (
    calculate_dynamic_safety_stock,
    calculate_optimal_reorder_quantity,
    calculate_holt_trend_forecast,
    run_monte_carlo_resilience_assessment,
)
from app.core.semantic_search import query_contract_clauses, SemanticKnowledgeRetriever


def test_holt_trend_forecasting_accuracy():
    """Verify Holt's linear trend forecasting captures growth trajectories and confidence."""
    # Upward trending historical series: 10, 20, 30, 40, 50
    series = [10.0, 20.0, 30.0, 40.0, 50.0]
    res = calculate_holt_trend_forecast(series, alpha=0.4, beta=0.2, horizon_periods=1)
    
    assert res["forecast_quantity"] > 50, "Forecast must project upward trend"
    assert res["trend"] > 0.0, "Trend slope must be positive"
    assert 0.60 <= res["confidence"] <= 1.0, "Confidence must be within valid probability range"
    assert res["method"] == "holt_double_exponential_smoothing"

    # Promo multiplier boost verification
    boosted = calculate_holt_trend_forecast(series, promo_multiplier=1.20)
    assert boosted["forecast_quantity"] > res["forecast_quantity"]


def test_dynamic_safety_stock_volatility_formula():
    """Verify dynamic safety stock responds mathematically to demand and lead-time volatility."""
    # Stable demand & lead time
    ss_stable = calculate_dynamic_safety_stock(
        mean_daily_demand=20.0,
        std_daily_demand=2.0,
        mean_lead_time_days=4.0,
        std_lead_time_days=0.5,
        service_level=0.98,
    )
    
    # Highly volatile demand & lead time
    ss_volatile = calculate_dynamic_safety_stock(
        mean_daily_demand=20.0,
        std_daily_demand=12.0,
        mean_lead_time_days=4.0,
        std_lead_time_days=3.0,
        service_level=0.98,
    )
    
    assert ss_volatile > ss_stable, "Volatile environment must demand significantly higher safety stock buffer"
    assert ss_stable >= 10, "Minimum buffer invariant preserved"


def test_eoq_reorder_optimization():
    """Verify Economic Order Quantity (EOQ) balances holding and setup costs."""
    # Annual demand = 1200 units, Setup cost = $85, Holding cost = $18/unit/yr
    # EOQ = sqrt((2 * 1200 * 85) / 18) = sqrt(204,000 / 18) = sqrt(11333.3) ≈ 107 units
    eoq = calculate_optimal_reorder_quantity(
        annual_demand=1200.0,
        order_setup_cost=85.0,
        holding_cost_per_unit_per_year=18.0,
        min_batch=50,
    )
    assert 100 <= eoq <= 115, f"Expected EOQ around 107 units, got {eoq}"


def test_monte_carlo_resilience_assessment():
    """Verify 500-trial Monte Carlo stochastic simulation produces bounded VaR and resilience index."""
    sim = run_monte_carlo_resilience_assessment(
        num_trials=500,
        base_order_value=25000.0,
        base_lead_time_days=3.0,
        supplier_disruption_prob=0.10,
        carrier_delay_prob=0.15,
        margin_pct=25.0,
    )
    
    assert sim["trials_count"] == 500
    assert 0.0 <= sim["resilience_index"] <= 100.0
    assert sim["value_at_risk_95"] >= 0.0
    assert sim["expected_shortfall_cvar"] >= sim["value_at_risk_95"], "CVaR must be >= VaR"
    assert sim["risk_posture"] in ("Robust", "Moderate", "Vulnerable")


def test_semantic_contract_rag_retrieval():
    """Verify local zero-cost semantic search retrieves exact legal contract clauses."""
    # Test 1: Query for Siemens delay penalty
    results_siemens = query_contract_clauses("Siemens delivery delay penalty damages", top_k=1)
    assert len(results_siemens) == 1
    top_doc = results_siemens[0]
    assert "Siemens" in top_doc["title"]
    assert "liquidated damages penalty of 2.0%" in top_doc["content"]
    assert top_doc["relevance_score"] > 0.10

    # Test 2: Query for Tesla bulk discount
    results_tesla = query_contract_clauses("Tesla volume discount bulk tier", top_k=1)
    assert len(results_tesla) == 1
    assert "Tesla" in results_tesla[0]["title"]
    assert "volume discount" in results_tesla[0]["content"].lower()


@pytest.mark.asyncio
async def test_monte_carlo_api_endpoint():
    """Verify POST /api/v1/simulate/monte-carlo returns structured stochastic resilience metrics."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/simulate/monte-carlo",
            json={
                "num_trials": 300,
                "base_order_value": 18000.0,
                "supplier_disruption_prob": 0.08,
                "carrier_delay_prob": 0.12,
                "margin_pct": 20.0,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "completed"
        assert data["simulation_type"] == "monte_carlo_stochastic"
        metrics = data["metrics"]
        assert metrics["trials_count"] == 300
        assert "value_at_risk_95" in metrics
        assert "resilience_index" in metrics
