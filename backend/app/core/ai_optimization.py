"""
Core AI Optimization Engine — Pure Python Statistical & Stochastic Intelligence.

Provides zero-cost, in-process AI capabilities:
1. Dynamic Safety Stock Calculation (Bayesian demand + lead-time volatility modeling).
2. Economic Order Quantity (EOQ) optimization.
3. Double Exponential Smoothing (Holt's Linear Trend demand forecasting).
4. Monte Carlo Supply Chain Resilience and Value-at-Risk (VaR) Engine.
"""

from __future__ import annotations

import math
import random
import statistics
from typing import Any


def calculate_dynamic_safety_stock(
    mean_daily_demand: float,
    std_daily_demand: float,
    mean_lead_time_days: float,
    std_lead_time_days: float,
    service_level: float = 0.98,
) -> int:
    """
    Calculate mathematically optimal safety stock considering both demand uncertainty
    and lead-time uncertainty using the standard inventory volatility formula:
    
        SS = Z * sqrt( L_avg * sigma_D^2 + D_avg^2 * sigma_L^2 )
        
    Args:
        mean_daily_demand: Average units sold/consumed per day (D_avg)
        std_daily_demand: Standard deviation of daily demand (sigma_D)
        mean_lead_time_days: Average replenishment lead time in days (L_avg)
        std_lead_time_days: Standard deviation of replenishment lead time in days (sigma_L)
        service_level: Target OTIF fulfillment probability (default: 0.98 for 98%)
        
    Returns:
        Integer safety stock buffer.
    """
    if mean_daily_demand <= 0:
        return 10
    
    # Bound service level between 0.80 and 0.999
    sla = max(0.80, min(0.999, service_level))
    z = statistics.NormalDist().inv_cdf(sla)
    
    l_avg = max(1.0, mean_lead_time_days)
    sigma_d = max(0.5, std_daily_demand)
    d_avg = max(1.0, mean_daily_demand)
    sigma_l = max(0.2, std_lead_time_days)
    
    # Combined variance
    variance = (l_avg * (sigma_d ** 2)) + ((d_avg ** 2) * (sigma_l ** 2))
    ss = z * math.sqrt(variance)
    return max(10, int(math.ceil(ss)))


def calculate_optimal_reorder_quantity(
    annual_demand: float,
    order_setup_cost: float = 85.0,
    holding_cost_per_unit_per_year: float = 18.0,
    min_batch: int = 50,
) -> int:
    """
    Calculate Economic Order Quantity (EOQ) using Wilson's formula:
    
        EOQ = sqrt( (2 * D * S) / H )
        
    Args:
        annual_demand: Estimated annual demand units (D)
        order_setup_cost: Fixed administrative/logistics cost per order (S)
        holding_cost_per_unit_per_year: Annual inventory holding/carrying cost per unit (H)
        min_batch: Minimum allowed batch size
        
    Returns:
        Integer optimal batch order quantity.
    """
    d = max(10.0, float(annual_demand))
    s = max(10.0, float(order_setup_cost))
    h = max(1.0, float(holding_cost_per_unit_per_year))
    
    raw_eoq = math.sqrt((2.0 * d * s) / h)
    return max(min_batch, int(math.ceil(raw_eoq)))


def calculate_holt_trend_forecast(
    historical_series: list[float],
    alpha: float = 0.35,
    beta: float = 0.15,
    horizon_periods: int = 1,
    promo_multiplier: float = 1.0,
) -> dict[str, Any]:
    """
    Double Exponential Smoothing (Holt's Linear Model) for trended demand forecasting:
    
        Level:  L_t = alpha * Y_t + (1 - alpha) * (L_{t-1} + T_{t-1})
        Trend:  T_t = beta * (L_t - L_{t-1}) + (1 - beta) * T_{t-1}
        Forecast: F_{t+h} = (L_t + h * T_t) * promo_multiplier
        
    Args:
        historical_series: Chronological sequence of historical demand quantities
        alpha: Level smoothing factor (0 < alpha < 1)
        beta: Trend smoothing factor (0 < beta < 1)
        horizon_periods: How many steps ahead to forecast (default: 1 month / 30 days)
        promo_multiplier: Multiplier for active marketing promotions
        
    Returns:
        Dictionary with forecasted quantity, detected trend, level, and confidence metrics.
    """
    if not historical_series:
        return {
            "forecast_quantity": 50,
            "level": 50.0,
            "trend": 0.0,
            "confidence": 0.70,
            "method": "default_baseline",
        }
    
    series = [float(x) for x in historical_series if x is not None]
    if len(series) < 2:
        val = series[0] if series else 50.0
        adjusted = max(1, int(round(val * promo_multiplier)))
        return {
            "forecast_quantity": adjusted,
            "level": val,
            "trend": 0.0,
            "confidence": 0.72,
            "method": "single_point_baseline",
        }
    
    # Initialization
    level = series[0]
    trend = series[1] - series[0]
    
    # Recursive smoothing
    for t in range(1, len(series)):
        prev_level = level
        val = series[t]
        level = alpha * val + (1.0 - alpha) * (level + trend)
        trend = beta * (level - prev_level) + (1.0 - beta) * trend
    
    h = max(1, horizon_periods)
    raw_forecast = (level + h * trend) * max(0.5, promo_multiplier)
    forecast_quantity = max(1, int(round(raw_forecast)))
    
    # Calculate Mean Absolute Error (MAE) for empirical confidence estimation
    residuals = []
    curr_l = series[0]
    curr_t = series[1] - series[0]
    for t in range(1, len(series)):
        pred = curr_l + curr_t
        residuals.append(abs(series[t] - pred))
        prev_l = curr_l
        curr_l = alpha * series[t] + (1.0 - alpha) * (curr_l + curr_t)
        curr_t = beta * (curr_l - prev_l) + (1.0 - beta) * curr_t
        
    mae = statistics.mean(residuals) if residuals else 5.0
    mean_val = statistics.mean(series) if series else 1.0
    rel_error = mae / max(mean_val, 1.0)
    confidence = max(0.60, min(0.96, round(1.0 - (rel_error * 0.5), 2)))
    
    return {
        "forecast_quantity": forecast_quantity,
        "level": round(level, 2),
        "trend": round(trend, 2),
        "confidence": confidence,
        "mae": round(mae, 2),
        "method": "holt_double_exponential_smoothing",
    }


def run_monte_carlo_resilience_assessment(
    num_trials: int = 500,
    base_order_value: float = 12500.0,
    base_lead_time_days: float = 3.5,
    supplier_disruption_prob: float = 0.08,
    carrier_delay_prob: float = 0.12,
    severe_weather_prob: float = 0.05,
    margin_pct: float = 22.0,
) -> dict[str, Any]:
    """
    Stochastic Monte Carlo Supply Chain Resilience Simulation.
    Simulates concurrent random shocks across supply, logistics, weather, and demand.
    
    Outputs:
    - Value-at-Risk (VaR at 95% confidence): Worst expected financial loss in 95% of cases.
    - Expected Shortfall (CVaR): Average loss in the worst 5% tail.
    - Network Resilience Index: Proportion of trials meeting contractual SLA.
    """
    trials = max(100, min(2000, num_trials))
    financial_losses: list[float] = []
    delivery_delays_days: list[float] = []
    successful_fulfillments = 0
    
    # Seeded random for reproducible analytical evaluations
    rnd = random.Random(42)
    
    for _ in range(trials):
        # 1. Base shipment transit time (Gaussian variation)
        simulated_lead_time = max(1.0, rnd.gauss(base_lead_time_days, 0.8))
        loss = 0.0
        
        # 2. Supplier disruption shock
        has_supplier_disruption = rnd.random() < supplier_disruption_prob
        if has_supplier_disruption:
            extra_days = rnd.uniform(2.0, 7.0)
            simulated_lead_time += extra_days
            # Expedited procurement surcharge + penalty
            loss += base_order_value * rnd.uniform(0.08, 0.22)
            
        # 3. Carrier transit shock
        has_carrier_delay = rnd.random() < carrier_delay_prob
        if has_carrier_delay:
            delay = rnd.uniform(1.0, 4.0)
            simulated_lead_time += delay
            # SLA demurrage / penalty fees
            loss += base_order_value * rnd.uniform(0.02, 0.09)
            
        # 4. Severe weather corridor event
        has_weather_event = rnd.random() < severe_weather_prob
        if has_weather_event:
            simulated_lead_time += rnd.uniform(1.5, 5.0)
            loss += base_order_value * rnd.uniform(0.05, 0.15)
            
        # Check SLA contract compliance (threshold: 4.5 days)
        sla_threshold_days = base_lead_time_days + 1.5
        is_success = simulated_lead_time <= sla_threshold_days and loss < (base_order_value * (margin_pct / 100.0))
        if is_success:
            successful_fulfillments += 1
            
        financial_losses.append(round(loss, 2))
        delivery_delays_days.append(round(simulated_lead_time, 2))
        
    # Statistical analysis of Monte Carlo outcomes
    financial_losses.sort()
    delivery_delays_days.sort()
    
    # 95th percentile index
    idx_95 = int(math.floor(0.95 * trials))
    var_95 = financial_losses[idx_95]
    
    # Expected Shortfall (CVaR): average of tail beyond 95%
    tail_losses = financial_losses[idx_95:]
    cvar_95 = statistics.mean(tail_losses) if tail_losses else var_95
    
    resilience_index = round((successful_fulfillments / trials) * 100.0, 1)
    mean_delay = round(statistics.mean(delivery_delays_days), 2)
    p95_delay = delivery_delays_days[idx_95]
    
    return {
        "trials_count": trials,
        "resilience_index": resilience_index,
        "value_at_risk_95": round(var_95, 2),
        "expected_shortfall_cvar": round(cvar_95, 2),
        "mean_transit_days": mean_delay,
        "p95_transit_days": p95_delay,
        "sla_breach_probability_pct": round((1.0 - (successful_fulfillments / trials)) * 100.0, 1),
        "risk_posture": "Robust" if resilience_index >= 85.0 else ("Moderate" if resilience_index >= 65.0 else "Vulnerable"),
    }
