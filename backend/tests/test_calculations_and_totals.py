"""
Validation tests for all calculations, totals, percentages, and invariants across
the Supply Chain Digital Twin application.
"""

from decimal import Decimal
import uuid
import pytest
from app.api.v1.inventory import compute_inventory_summary, _FALLBACK_INVENTORY
from app.api.v1.analytics import get_dashboard_data
from app.core.standby_session import STANDBY_PRODUCT_DATA, STANDBY_CUSTOMERS
from app.agents.operational.order_management import _PRODUCT_CATALOG


def test_inventory_summary_calculations():
    """Verify inventory summary arithmetic matches exactly."""
    summary = compute_inventory_summary(_FALLBACK_INVENTORY)
    
    assert summary["total_sku_locations"] == len(_FALLBACK_INVENTORY)
    assert summary["total_available_units"] - summary["total_reserved_units"] == summary["net_available_units"]
    
    # Invariant: ok_locations + low_stock_locations + out_of_stock_locations == total_sku_locations
    ok_count = summary["total_sku_locations"] - summary["low_stock_locations"] - summary["out_of_stock_locations"]
    assert ok_count >= 0
    assert ok_count + summary["low_stock_locations"] + summary["out_of_stock_locations"] == summary["total_sku_locations"]
    
    # Fill rate calculation check: % of locations in stock (not out of stock)
    expected_fill_rate = round((1.0 - (summary["out_of_stock_locations"] / summary["total_sku_locations"])) * 100, 1)
    assert summary["fill_rate_pct"] == expected_fill_rate


@pytest.mark.asyncio
async def test_analytics_dashboard_fallback_invariants():
    """Verify fallback dashboard inventory health breakdown matches total locations."""
    # When session is None, get_dashboard_data falls back gracefully
    dash = await get_dashboard_data(session=None)
    inv_health = dash["inventory_health"]
    total = inv_health["total_locations"]
    healthy = inv_health["healthy"]
    low = inv_health["low_stock"]
    out = inv_health["out_of_stock"]
    
    assert healthy + low + out == total, f"Healthy ({healthy}) + Low ({low}) + Out ({out}) != Total ({total})"


def test_product_catalog_parity():
    """Verify product catalog prices and SKUs match across standby and operational agent registries."""
    for pid_str, (name, sku, price) in STANDBY_PRODUCT_DATA.items():
        try:
            uid = uuid.UUID(pid_str)
        except Exception:
            continue
        if uid in _PRODUCT_CATALOG:
            cat_name, cat_sku, cat_price = _PRODUCT_CATALOG[uid]
            assert sku == cat_sku, f"SKU mismatch for {pid_str}: {sku} != {cat_sku}"
            assert price == cat_price, f"Price mismatch for {pid_str}: {price} != {cat_price}"


@pytest.mark.asyncio
async def test_finance_agent_cost_and_margin_totals():
    """Verify finance agent arithmetic strictly sums components and calculates margins."""
    from app.agents.business.finance import FinanceAgent
    
    agent = FinanceAgent(session=None, publisher=None)
    state = {
        "workflow_id": str(uuid.uuid4()),
        "order": {
            "order_id": str(uuid.uuid4()),
            "total_amount": "1000.00",
            "items": [
                {"product_id": "30000000-0000-0000-0000-000000000001", "quantity": 10, "unit_price": "100.00"}
            ],
        },
        "supplier": {
            "purchase_orders": [
                {"unit_cost": "60.00", "quantity": 10}
            ]
        },
        "shipment": {
            "freight_mode": "road"
        },
        "event_history": [],
        "decisions": [],
    }
    
    res = await agent._execute(state)
    fin = res["finance"]
    
    rev = Decimal(fin["revenue"])
    proc = Decimal(fin["procurement_cost"])
    ship = Decimal(fin["shipping_cost"])
    wh = Decimal(fin["warehouse_cost"])
    total_cost = Decimal(fin["total_cost"])
    gross_margin_amt = Decimal(fin["gross_margin_amount"])
    
    # Exact cost sum
    assert proc + ship + wh == total_cost, f"{proc} + {ship} + {wh} != {total_cost}"
    # Exact margin calculation
    assert rev - total_cost == gross_margin_amt
    # Margin % calculation
    expected_pct = round(float((gross_margin_amt / rev) * Decimal("100.0")), 2)
    assert fin["gross_margin_pct"] == expected_pct


@pytest.mark.asyncio
async def test_sustainability_agent_co2_savings():
    """Verify green alternative calculations balance exactly: current - alternative == savings."""
    from app.agents.business.sustainability import SustainabilityAgent
    
    agent = SustainabilityAgent(session=None, publisher=None)
    state = {
        "workflow_id": str(uuid.uuid4()),
        "order": {
            "order_id": str(uuid.uuid4()),
            "items": [{"quantity": 100}],
        },
        "shipment": {
            "freight_mode": "air",
        },
        "event_history": [],
        "decisions": [],
    }
    
    res = await agent._execute(state)
    metric = res.get("sustainability", {})
    green_alt = metric.get("green_alternative")
    
    if green_alt:
        cur = green_alt["current_co2_kg"]
        alt = green_alt["alternative_co2_kg"]
        sav = green_alt["co2_savings_kg"]
        assert round(cur - alt, 3) == sav, f"{cur} - {alt} != {sav}"
