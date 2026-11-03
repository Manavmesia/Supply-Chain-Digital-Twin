"""Single Source of Truth Catalog for the Supply Chain Digital Twin.

Contains centralized baseline definitions for customers, products, warehouses,
inventory, suppliers, carriers, routes, and baseline orders.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

# ── Baseline Customers ────────────────────────────────────────────────────────

BASELINE_CUSTOMERS = [
    ("50000000-0000-0000-0000-000000000001", "Siemens Global Automations", "enterprise", "procure@siemens.com"),
    ("50000000-0000-0000-0000-000000000002", "Tesla Energy & Storage", "premium", "orders@tesla.com"),
    ("50000000-0000-0000-0000-000000000003", "Schneider Electric Grid", "enterprise", "supply@schneider.com"),
    ("50000000-0000-0000-0000-000000000004", "Honeywell Aerospace", "standard", "procure@honeywell.com"),
    ("00000000-0000-0000-0000-000000000001", "Siemens Global Automations", "enterprise", "procure@siemens.com"),
    ("cust0000-0000-0000-0000-000000000001", "Tesla Energy Solutions", "enterprise", "procure@tesla.com"),
    ("cust0000-0000-0000-0000-000000000002", "Siemens Robotics Global", "premium", "orders@siemens.com"),
    ("cust0000-0000-0000-0000-000000000003", "Schneider Power Grid", "enterprise", "supply@schneider.com"),
    ("cust0000-0000-0000-0000-000000000004", "Honeywell Industrial Automations", "standard", "procure@honeywell.com"),
]

CUSTOMER_MAP: dict[str, tuple[str, str]] = {
    c[0]: (c[1], c[2]) for c in BASELINE_CUSTOMERS
}

# ── Baseline Products ─────────────────────────────────────────────────────────

BASELINE_PRODUCTS = [
    ("30000000-0000-0000-0000-000000000001", "ELEC-001", "Industrial Sensor Module", "Electronics", "Sensors", 150.00, 0.45, 0.001),
    ("30000000-0000-0000-0000-000000000002", "ELEC-002", "High-Torque Servo Motor", "Electronics", "Motors", 280.00, 2.80, 0.005),
    ("30000000-0000-0000-0000-000000000003", "ELEC-003", "IoT Gateway Device", "Electronics", "Networking", 1249.99, 1.20, 0.003),
    ("30000000-0000-0000-0000-000000000004", "MECH-001", "Precision Ball Bearing Set", "Mechanical", "Bearings", 95.00, 0.85, 0.002),
    ("30000000-0000-0000-0000-000000000005", "MECH-002", "Hydraulic Actuator Cylinder", "Mechanical", "Actuators", 3450.00, 18.50, 0.045),
    ("30000000-0000-0000-0000-000000000006", "MECH-003", "Stainless Steel Valve Assembly", "Mechanical", "Valves", 575.00, 4.30, 0.008),
    ("30000000-0000-0000-0000-000000000007", "CHEM-001", "Industrial Lubricant (20L)", "Chemicals", "Lubricants", 185.00, 19.00, 0.025),
    ("30000000-0000-0000-0000-000000000008", "CHEM-002", "Epoxy Adhesive Kit", "Chemicals", "Adhesives", 95.00, 2.10, 0.004),
    ("30000000-0000-0000-0000-000000000009", "SAFE-001", "Safety Relay Module", "Safety", "Relays", 120.00, 0.60, 0.001),
    ("30000000-0000-0000-0000-000000000010", "SAFE-002", "Emergency Stop Assembly", "Safety", "Switches", 145.00, 0.90, 0.002),
    ("00000000-0000-0000-0000-000000000002", "ELEC-001", "Industrial IoT Sensor Hub v2", "Electronics", "Sensors", 150.00, 0.45, 0.001),
]

PRODUCT_MAP: dict[str, tuple[str, str, Decimal]] = {
    p[0]: (p[2], p[1], Decimal(str(p[5]))) for p in BASELINE_PRODUCTS
}

PRODUCT_UUID_MAP: dict[uuid.UUID, tuple[str, str, Decimal]] = {
    uuid.UUID(p[0]): (p[2], p[1], Decimal(str(p[5]))) for p in BASELINE_PRODUCTS
}

# ── Baseline Warehouses ───────────────────────────────────────────────────────

BASELINE_WAREHOUSES = [
    ("10000000-0000-0000-0000-000000000001", "Newark Distribution Center", "Newark", "US", 50000, 12500, "active"),
    ("10000000-0000-0000-0000-000000000002", "Birmingham Fulfilment Hub", "Birmingham", "GB", 35000, 8200, "active"),
    ("10000000-0000-0000-0000-000000000003", "Frankfurt Logistics Centre", "Frankfurt", "DE", 40000, 9100, "active"),
    ("22222222-0000-0000-0000-000000000001", "Pacific Northwest MegaHub", "Seattle", "US", 50000, 12500, "active"),
]

# ── Baseline Inventory (21 locations across products and warehouses) ──────────

BASELINE_INVENTORY = [
    ("11111111-2222-3333-4444-555555555501", "30000000-0000-0000-0000-000000000001", "10000000-0000-0000-0000-000000000001", 500, 50, 100, 150, "ok"),
    ("11111111-2222-3333-4444-555555555502", "30000000-0000-0000-0000-000000000001", "10000000-0000-0000-0000-000000000002", 300, 30, 80, 120, "ok"),
    ("11111111-2222-3333-4444-555555555503", "30000000-0000-0000-0000-000000000001", "10000000-0000-0000-0000-000000000003", 250, 20, 80, 120, "ok"),
    ("11111111-2222-3333-4444-555555555504", "30000000-0000-0000-0000-000000000002", "10000000-0000-0000-0000-000000000001", 200, 10, 50, 80, "ok"),
    ("11111111-2222-3333-4444-555555555505", "30000000-0000-0000-0000-000000000002", "10000000-0000-0000-0000-000000000002", 150, 0, 40, 60, "ok"),
    ("11111111-2222-3333-4444-555555555506", "30000000-0000-0000-0000-000000000003", "10000000-0000-0000-0000-000000000001", 80, 5, 20, 30, "ok"),
    ("11111111-2222-3333-4444-555555555507", "30000000-0000-0000-0000-000000000003", "10000000-0000-0000-0000-000000000003", 60, 0, 20, 30, "ok"),
    ("11111111-2222-3333-4444-555555555508", "30000000-0000-0000-0000-000000000004", "10000000-0000-0000-0000-000000000001", 2000, 200, 500, 700, "ok"),
    ("11111111-2222-3333-4444-555555555509", "30000000-0000-0000-0000-000000000004", "10000000-0000-0000-0000-000000000002", 1500, 100, 400, 600, "ok"),
    ("11111111-2222-3333-4444-555555555510", "30000000-0000-0000-0000-000000000005", "10000000-0000-0000-0000-000000000001", 15, 5, 20, 30, "low"),
    ("11111111-2222-3333-4444-555555555511", "30000000-0000-0000-0000-000000000005", "10000000-0000-0000-0000-000000000003", 10, 10, 20, 30, "critical"),
    ("11111111-2222-3333-4444-555555555512", "30000000-0000-0000-0000-000000000006", "10000000-0000-0000-0000-000000000001", 300, 20, 60, 90, "ok"),
    ("11111111-2222-3333-4444-555555555513", "30000000-0000-0000-0000-000000000006", "10000000-0000-0000-0000-000000000002", 200, 10, 50, 70, "ok"),
    ("11111111-2222-3333-4444-555555555514", "30000000-0000-0000-0000-000000000007", "10000000-0000-0000-0000-000000000001", 100, 5, 30, 40, "ok"),
    ("11111111-2222-3333-4444-555555555515", "30000000-0000-0000-0000-000000000007", "10000000-0000-0000-0000-000000000003", 80, 0, 25, 35, "ok"),
    ("11111111-2222-3333-4444-555555555516", "30000000-0000-0000-0000-000000000008", "10000000-0000-0000-0000-000000000001", 500, 50, 100, 150, "ok"),
    ("11111111-2222-3333-4444-555555555517", "30000000-0000-0000-0000-000000000008", "10000000-0000-0000-0000-000000000002", 400, 20, 80, 120, "ok"),
    ("11111111-2222-3333-4444-555555555518", "30000000-0000-0000-0000-000000000009", "10000000-0000-0000-0000-000000000001", 200, 10, 50, 70, "ok"),
    ("11111111-2222-3333-4444-555555555519", "30000000-0000-0000-0000-000000000009", "10000000-0000-0000-0000-000000000002", 150, 0, 40, 60, "ok"),
    ("11111111-2222-3333-4444-555555555520", "30000000-0000-0000-0000-000000000010", "10000000-0000-0000-0000-000000000001", 800, 100, 200, 300, "ok"),
    ("11111111-2222-3333-4444-555555555521", "30000000-0000-0000-0000-000000000010", "10000000-0000-0000-0000-000000000003", 600, 50, 150, 220, "ok"),
]

# ── Baseline Suppliers ────────────────────────────────────────────────────────

BASELINE_SUPPLIERS = [
    ("sup00000-0000-0000-0000-000000000001", "Apex Microelectronics Inc.", "Japan", 4, 96.5, 4.9, "active"),
    ("sup00000-0000-0000-0000-000000000002", "Global Precision Systems GmbH", "Germany", 7, 91.2, 4.7, "active"),
    ("sup00000-0000-0000-0000-000000000003", "Nexus Advanced Circuits", "USA", 3, 88.0, 4.5, "active"),
    ("sup00000-0000-0000-0000-000000000004", "Pacific Freight Logistics Ltd.", "Taiwan", 12, 82.3, 4.2, "active"),
    ("33333333-0000-0000-0000-000000000001", "Apex Microelectronics Inc.", "US", 4, 96.5, 4.9, "active"),
    ("33333333-0000-0000-0000-000000000002", "Precision Dynamics Corp.", "DE", 6, 92.0, 4.7, "active"),
    ("33333333-0000-0000-0000-000000000003", "EuroMech Components Ltd.", "GB", 5, 88.0, 4.5, "active"),
    ("33333333-0000-0000-0000-000000000004", "Pacific Tech Supplies", "JP", 10, 81.5, 4.2, "active"),
]

# ── Baseline Carriers & Routes ────────────────────────────────────────────────

BASELINE_CARRIERS = [
    ("44444444-0000-0000-0000-000000000001", "Global Intermodal Logistics", "GIL-01", '["road", "air", "ocean"]', 95.0, "active"),
]

BASELINE_ROUTES = [
    ("route000-0000-0000-0000-000000000001", "44444444-0000-0000-0000-000000000001", "Seattle, US", "Dallas, US", "road", 3, 350.00, 1),
]

# ── Baseline Orders ───────────────────────────────────────────────────────────

BASELINE_ORDERS = [
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

# ── Baseline Reports ──────────────────────────────────────────────────────────

BASELINE_REPORTS: list[dict[str, Any]] = [
    {
        "report_id": "e4f878a2-1111-4235-9c88-123456789abc",
        "report_type": "executive_summary",
        "title": "Autonomous Supply Chain Operational Synthesis",
        "status": "ready",
        "workflow_id": "7f92a34c-6d8b-4a5f-9271-9df61c778fa1",
        "generated_by_agent": "ADS-18",
        "created_at": "2026-11-02T10:30:00Z",
        "payload_summary": {
            "order_count": 124,
            "fulfillment_rate": "98.4%",
            "sustainability_score": 94.2,
            "margin_pct": 28.5,
            "disruption_handled": True,
        },
    },
    {
        "report_id": "b7c29410-2222-4235-9c88-123456789def",
        "report_type": "sustainability",
        "title": "Carbon Footprint & ESG Verification Report",
        "status": "ready",
        "workflow_id": "8a14b52d-7e9c-4b6a-8382-0ea72d889fb2",
        "generated_by_agent": "ADS-13",
        "created_at": "2026-11-02T09:15:00Z",
        "payload_summary": {
            "total_co2_kg": 182.4,
            "transportation_mode": "EV_FLEET",
            "esg_compliance": "A+",
        },
    },
    {
        "report_id": "c9d38521-3333-4235-9c88-123456789123",
        "report_type": "risk",
        "title": "Tier-1 Supplier Resilience & Risk Audit",
        "status": "ready",
        "workflow_id": "9b25c63e-8fa0-4c7b-9493-1fb83e990ac3",
        "generated_by_agent": "ADS-10",
        "created_at": "2026-11-02T08:00:00Z",
        "payload_summary": {
            "overall_risk_score": 24.0,
            "geopolitical_risk": "low",
            "bottleneck_identified": False,
        },
    },
]

# ── Baseline Purchase Orders (Autonomous Inbound Replenishment) ───────────────

BASELINE_PURCHASE_ORDERS = [
    (
        "po000000-0000-0000-0000-000000000001",
        "33333333-0000-0000-0000-000000000001",
        "Apex Microelectronics Inc.",
        "30000000-0000-0000-0000-000000000001",
        "Industrial Sensor Module",
        "ELEC-001",
        "22222222-0000-0000-0000-000000000001",
        "Pacific Northwest MegaHub",
        500,
        110.00,
        55000.00,
        4,
        "in_transit",
        "7f92a34c-6d8b-4a5f-9271-9df61c778fa1",
        "2026-11-02T11:00:00Z",
    ),
    (
        "po000000-0000-0000-0000-000000000002",
        "33333333-0000-0000-0000-000000000002",
        "Stuttgart Industrial Sensors GmbH",
        "30000000-0000-0000-0000-000000000004",
        "Precision Ball Bearing Set",
        "MECH-001",
        "22222222-0000-0000-0000-000000000002",
        "Midwest Fulfillment Center",
        250,
        70.00,
        17500.00,
        6,
        "draft",
        None,
        "2026-11-02T14:30:00Z",
    ),
]
