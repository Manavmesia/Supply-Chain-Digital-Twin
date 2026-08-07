"""
Rich Development Seed Script
=============================
Creates realistic test data for the AI Supply Chain Digital Twin:
  - 3 warehouses (US, UK, Germany)
  - 5 carriers (road, air, sea, multimodal)
  - 10 products across 3 categories
  - 4 suppliers (high/medium/low reliability)
  - 3 customers (enterprise, premium, standard tiers)
  - Inventory records across all warehouse×product combos
  - Transportation routes (origin → customer regions)

Run from the backend/ directory:
    python -m scripts.seed_rich

or from project root:
    python backend/scripts/seed_rich.py
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from decimal import Decimal

# Ensure app modules are importable
sys.path.insert(0, "")
sys.path.insert(0, "backend")

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.carrier import Carrier
from app.models.customer import Customer
from app.models.inventory import Inventory
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.transportation_route import TransportationRoute
from app.models.warehouse import Warehouse

logger = structlog.get_logger()


# ── Seed Data Definitions ─────────────────────────────────────────────────────

WAREHOUSES = [
    {
        "warehouse_id": uuid.UUID("10000000-0000-0000-0000-000000000001"),
        "name": "Newark Distribution Center",
        "location": "Newark, US",
        "city": "Newark",
        "country": "US",
        "latitude": Decimal("40.7357"),
        "longitude": Decimal("-74.1724"),
        "capacity_units": 50000,
        "current_load": 18000,
        "status": "active",
    },
    {
        "warehouse_id": uuid.UUID("10000000-0000-0000-0000-000000000002"),
        "name": "Birmingham Fulfilment Hub",
        "location": "Birmingham, UK",
        "city": "Birmingham",
        "country": "UK",
        "latitude": Decimal("52.4862"),
        "longitude": Decimal("-1.8904"),
        "capacity_units": 35000,
        "current_load": 12000,
        "status": "active",
    },
    {
        "warehouse_id": uuid.UUID("10000000-0000-0000-0000-000000000003"),
        "name": "Frankfurt Logistics Centre",
        "location": "Frankfurt, DE",
        "city": "Frankfurt",
        "country": "DE",
        "latitude": Decimal("50.1109"),
        "longitude": Decimal("8.6821"),
        "capacity_units": 40000,
        "current_load": 15000,
        "status": "active",
    },
]

CARRIERS = [
    {
        "carrier_id": uuid.UUID("20000000-0000-0000-0000-000000000001"),
        "name": "FastFreight Express",
        "code": "FFE",
        "freight_modes": ["road", "air"],
        "tracking_url": "https://ffe.example.com/track",
        "reliability_score": Decimal("94.5"),
        "avg_delay_days": Decimal("0.3"),
        "status": "active",
    },
    {
        "carrier_id": uuid.UUID("20000000-0000-0000-0000-000000000002"),
        "name": "GlobalAir Cargo",
        "code": "GAC",
        "freight_modes": ["air"],
        "tracking_url": "https://gac.example.com/track",
        "reliability_score": Decimal("97.2"),
        "avg_delay_days": Decimal("0.1"),
        "status": "active",
    },
    {
        "carrier_id": uuid.UUID("20000000-0000-0000-0000-000000000003"),
        "name": "OceanLink Shipping",
        "code": "OLS",
        "freight_modes": ["sea", "multimodal"],
        "tracking_url": "https://ols.example.com/track",
        "reliability_score": Decimal("88.0"),
        "avg_delay_days": Decimal("1.2"),
        "status": "active",
    },
    {
        "carrier_id": uuid.UUID("20000000-0000-0000-0000-000000000004"),
        "name": "RailConnect Europe",
        "code": "RCE",
        "freight_modes": ["rail", "multimodal"],
        "tracking_url": "https://rce.example.com/track",
        "reliability_score": Decimal("91.8"),
        "avg_delay_days": Decimal("0.5"),
        "status": "active",
    },
    {
        "carrier_id": uuid.UUID("20000000-0000-0000-0000-000000000005"),
        "name": "BudgetRoad Logistics",
        "code": "BRL",
        "freight_modes": ["road"],
        "tracking_url": "https://brl.example.com/track",
        "reliability_score": Decimal("78.5"),
        "avg_delay_days": Decimal("1.8"),
        "status": "active",
    },
]

PRODUCTS = [
    # Electronics
    {"product_id": uuid.UUID("30000000-0000-0000-0000-000000000001"),
     "sku": "ELEC-001", "name": "Industrial Sensor Module", "category": "Electronics",
     "subcategory": "Sensors", "unit_price": Decimal("249.99"), "weight_kg": Decimal("0.450"), "active": True},
    {"product_id": uuid.UUID("30000000-0000-0000-0000-000000000002"),
     "sku": "ELEC-002", "name": "High-Torque Servo Motor", "category": "Electronics",
     "subcategory": "Motors", "unit_price": Decimal("899.00"), "weight_kg": Decimal("2.100"), "active": True},
    {"product_id": uuid.UUID("30000000-0000-0000-0000-000000000003"),
     "sku": "ELEC-003", "name": "IoT Gateway Device", "category": "Electronics",
     "subcategory": "Connectivity", "unit_price": Decimal("1249.99"), "weight_kg": Decimal("0.750"), "active": True},
    # Mechanical
    {"product_id": uuid.UUID("30000000-0000-0000-0000-000000000004"),
     "sku": "MECH-001", "name": "Precision Ball Bearing Set", "category": "Mechanical",
     "subcategory": "Bearings", "unit_price": Decimal("89.50"), "weight_kg": Decimal("1.200"), "active": True},
    {"product_id": uuid.UUID("30000000-0000-0000-0000-000000000005"),
     "sku": "MECH-002", "name": "Hydraulic Actuator Cylinder", "category": "Mechanical",
     "subcategory": "Actuators", "unit_price": Decimal("3450.00"), "weight_kg": Decimal("12.500"), "active": True},
    {"product_id": uuid.UUID("30000000-0000-0000-0000-000000000006"),
     "sku": "MECH-003", "name": "Stainless Steel Valve Assembly", "category": "Mechanical",
     "subcategory": "Valves", "unit_price": Decimal("575.00"), "weight_kg": Decimal("3.800"), "active": True},
    # Chemicals / Materials
    {"product_id": uuid.UUID("30000000-0000-0000-0000-000000000007"),
     "sku": "CHEM-001", "name": "Industrial Lubricant (20L)", "category": "Chemicals",
     "subcategory": "Lubricants", "unit_price": Decimal("185.00"), "weight_kg": Decimal("18.000"), "active": True},
    {"product_id": uuid.UUID("30000000-0000-0000-0000-000000000008"),
     "sku": "CHEM-002", "name": "Epoxy Adhesive Kit", "category": "Chemicals",
     "subcategory": "Adhesives", "unit_price": Decimal("95.00"), "weight_kg": Decimal("2.000"), "active": True},
    # Safety / Consumables
    {"product_id": uuid.UUID("30000000-0000-0000-0000-000000000009"),
     "sku": "SAFE-001", "name": "Safety Relay Module", "category": "Safety",
     "subcategory": "Relays", "unit_price": Decimal("320.00"), "weight_kg": Decimal("0.600"), "active": True},
    {"product_id": uuid.UUID("30000000-0000-0000-0000-000000000010"),
     "sku": "SAFE-002", "name": "Emergency Stop Assembly", "category": "Safety",
     "subcategory": "Emergency", "unit_price": Decimal("145.00"), "weight_kg": Decimal("0.300"), "active": True},
]

SUPPLIERS = [
    {
        "supplier_id": uuid.UUID("40000000-0000-0000-0000-000000000001"),
        "name": "TechComponents Global",
        "country": "DE",
        "contact_email": "orders@tcg.example.com",
        "reliability_score": Decimal("96.50"),
        "lead_time_days": 5,
        "payment_terms_days": 30,
        "status": "active",
        "rating": Decimal("4.8"),
    },
    {
        "supplier_id": uuid.UUID("40000000-0000-0000-0000-000000000002"),
        "name": "MechParts International",
        "country": "US",
        "contact_email": "supply@mpi.example.com",
        "reliability_score": Decimal("88.00"),
        "lead_time_days": 8,
        "payment_terms_days": 45,
        "status": "active",
        "rating": Decimal("4.1"),
    },
    {
        "supplier_id": uuid.UUID("40000000-0000-0000-0000-000000000003"),
        "name": "ChemSource Asia",
        "country": "SG",
        "contact_email": "b2b@chemsource.example.com",
        "reliability_score": Decimal("79.50"),
        "lead_time_days": 14,
        "payment_terms_days": 60,
        "status": "active",
        "rating": Decimal("3.6"),
    },
    {
        "supplier_id": uuid.UUID("40000000-0000-0000-0000-000000000004"),
        "name": "SafetyFirst Components",
        "country": "UK",
        "contact_email": "procurement@sfc.example.com",
        "reliability_score": Decimal("92.00"),
        "lead_time_days": 7,
        "payment_terms_days": 30,
        "status": "active",
        "rating": Decimal("4.5"),
    },
]

CUSTOMERS = [
    {
        "customer_id": uuid.UUID("50000000-0000-0000-0000-000000000001"),
        "name": "Siemens Manufacturing GmbH",
        "email": "procurement@siemens-mfg.example.com",
        "phone": "+49-89-636-00",
        "address": "Werner-von-Siemens-Str. 1",
        "city": "Munich",
        "country": "DE",
        "customer_tier": "enterprise",
        "is_active": True,
    },
    {
        "customer_id": uuid.UUID("50000000-0000-0000-0000-000000000002"),
        "name": "AutoTech Solutions Ltd",
        "email": "orders@autotech.example.com",
        "phone": "+44-121-555-0100",
        "address": "Innovation Park, Unit 14",
        "city": "Coventry",
        "country": "UK",
        "customer_tier": "premium",
        "is_active": True,
    },
    {
        "customer_id": uuid.UUID("50000000-0000-0000-0000-000000000003"),
        "name": "Meridian Industrial Corp",
        "email": "supply@meridian.example.com",
        "phone": "+1-201-555-0199",
        "address": "45 Commerce Blvd",
        "city": "Newark",
        "country": "US",
        "customer_tier": "standard",
        "is_active": True,
    },
]

# Inventory: (product_idx, warehouse_idx, available, reserved, safety_stock, reorder_point, reorder_qty)
INVENTORY_CONFIG = [
    # product 0 (ELEC-001) — high demand
    (0, 0, 500, 50, 100, 150, 200),
    (0, 1, 300, 30, 80,  120, 150),
    (0, 2, 250, 20, 80,  120, 150),
    # product 1 (ELEC-002)
    (1, 0, 200, 10, 50,  80,  100),
    (1, 1, 150, 0,  40,  60,  80),
    # product 2 (ELEC-003)
    (2, 0, 80,  5,  20,  30,  50),
    (2, 2, 60,  0,  20,  30,  50),
    # product 3 (MECH-001) — high volume
    (3, 0, 2000, 200, 500, 700, 1000),
    (3, 1, 1500, 100, 400, 600, 800),
    # product 4 (MECH-002) — low stock to trigger supplier
    (4, 0, 15, 5, 20, 30, 50),     # net=10, below safety!
    (4, 2, 10, 0, 20, 30, 50),
    # product 5 (MECH-003)
    (5, 0, 300, 20, 60, 90, 120),
    (5, 1, 200, 10, 50, 70, 100),
    # product 6 (CHEM-001)
    (6, 0, 100, 5, 30, 40, 60),
    (6, 2, 80,  0, 25, 35, 50),
    # product 7 (CHEM-002)
    (7, 0, 500, 50, 100, 150, 200),
    (7, 1, 400, 20, 80,  120, 160),
    # product 8 (SAFE-001)
    (8, 0, 200, 10, 50, 70, 100),
    (8, 1, 150, 0, 40, 60, 80),
    # product 9 (SAFE-002)
    (9, 0, 800, 100, 200, 300, 400),
    (9, 2, 600, 50,  150, 220, 300),
]

# Routes: (carrier_idx, origin_warehouse_idx, origin_location, destination, freight_mode, transit_days, base_cost, co2)
ROUTES = [
    # FFE — road routes from Newark
    (0, 0, "Newark, US",     "Boston, US",    "road", 2,  Decimal("180.00"), Decimal("0.1200")),
    (0, 0, "Newark, US",     "Chicago, US",   "road", 3,  Decimal("250.00"), Decimal("0.1500")),
    (0, 0, "Newark, US",     "Dallas, US",    "road", 5,  Decimal("380.00"), Decimal("0.1800")),
    # FFE — air from Newark
    (0, 0, "Newark, US",     "Los Angeles, US","air", 2,  Decimal("650.00"), Decimal("0.8500")),
    # GAC — air premium
    (1, 0, "Newark, US",     "London, UK",    "air",  1,  Decimal("1200.00"),Decimal("1.2000")),
    (1, 0, "Newark, US",     "Frankfurt, DE", "air",  1,  Decimal("1350.00"),Decimal("1.2500")),
    (1, 0, "Newark, US",     "Singapore, SG", "air",  2,  Decimal("2100.00"),Decimal("1.8000")),
    # OLS — sea from Newark
    (2, 0, "Newark, US",     "Southampton, UK","sea", 10, Decimal("450.00"), Decimal("0.0120")),
    (2, 0, "Newark, US",     "Hamburg, DE",   "sea",  14, Decimal("520.00"), Decimal("0.0120")),
    # RCE — rail from Birmingham
    (3, 1, "Birmingham, UK", "Paris, FR",     "rail", 3,  Decimal("320.00"), Decimal("0.0450")),
    (3, 1, "Birmingham, UK", "Amsterdam, NL", "rail", 2,  Decimal("280.00"), Decimal("0.0400")),
    (3, 2, "Frankfurt, DE",  "Warsaw, PL",    "rail", 2,  Decimal("260.00"), Decimal("0.0400")),
    (3, 2, "Frankfurt, DE",  "Vienna, AT",    "rail", 1,  Decimal("190.00"), Decimal("0.0350")),
    # BRL — cheap road from Birmingham
    (4, 1, "Birmingham, UK", "Manchester, UK","road", 1,  Decimal("120.00"), Decimal("0.1000")),
    (4, 1, "Birmingham, UK", "London, UK",    "road", 2,  Decimal("150.00"), Decimal("0.1100")),
    (4, 2, "Frankfurt, DE",  "Munich, DE",    "road", 1,  Decimal("130.00"), Decimal("0.1000")),
    (4, 2, "Frankfurt, DE",  "Berlin, DE",    "road", 2,  Decimal("160.00"), Decimal("0.1200")),
]


# ── Main seed function ────────────────────────────────────────────────────────

async def seed_all(session: AsyncSession) -> None:
    """Insert all seed data within a single transaction."""

    # 1. Warehouses
    wh_objs = []
    for wh_data in WAREHOUSES:
        wh = Warehouse(**wh_data)
        session.add(wh)
        wh_objs.append(wh)
    await session.flush()
    logger.info("Warehouses seeded", count=len(wh_objs))

    # 2. Carriers
    carrier_objs = []
    for c_data in CARRIERS:
        c = Carrier(**c_data)
        session.add(c)
        carrier_objs.append(c)
    await session.flush()
    logger.info("Carriers seeded", count=len(carrier_objs))

    # 3. Products
    product_objs = []
    for p_data in PRODUCTS:
        p = Product(**p_data)
        session.add(p)
        product_objs.append(p)
    await session.flush()
    logger.info("Products seeded", count=len(product_objs))

    # 4. Suppliers
    for s_data in SUPPLIERS:
        s = Supplier(**s_data)
        session.add(s)
    await session.flush()
    logger.info("Suppliers seeded", count=len(SUPPLIERS))

    # 5. Customers
    for cu_data in CUSTOMERS:
        cu = Customer(**cu_data)
        session.add(cu)
    await session.flush()
    logger.info("Customers seeded", count=len(CUSTOMERS))

    # 6. Inventory
    inv_count = 0
    for (p_idx, wh_idx, avail, reserved, safety, reorder_pt, reorder_qty) in INVENTORY_CONFIG:
        inv = Inventory(
            inventory_id=uuid.uuid4(),
            product_id=product_objs[p_idx].product_id,
            warehouse_id=wh_objs[wh_idx].warehouse_id,
            available_qty=avail,
            reserved_qty=reserved,
            safety_stock=safety,
            reorder_point=reorder_pt,
            reorder_qty=reorder_qty,
        )
        session.add(inv)
        inv_count += 1
    await session.flush()
    logger.info("Inventory records seeded", count=inv_count)

    # 7. Transportation Routes
    route_count = 0
    for (c_idx, wh_idx, origin, dest, mode, transit, cost, co2) in ROUTES:
        route = TransportationRoute(
            route_id=uuid.uuid4(),
            carrier_id=carrier_objs[c_idx].carrier_id,
            origin_warehouse_id=wh_objs[wh_idx].warehouse_id,
            origin_location=origin,
            destination=dest,
            freight_mode=mode,
            transit_days=transit,
            base_cost=cost,
            co2_per_tonne_km=co2,
            is_active=True,
        )
        session.add(route)
        route_count += 1
    await session.flush()
    logger.info("Transportation routes seeded", count=route_count)


async def main() -> None:
    logger.info("Starting rich database seed")
    logger.info("Database URL", url=settings.DATABASE_URL.split("@")[-1])  # hide password

    async with AsyncSessionLocal() as session:
        try:
            await seed_all(session)
            await session.commit()
            logger.info(
                "Rich seed completed successfully",
                warehouses=len(WAREHOUSES),
                carriers=len(CARRIERS),
                products=len(PRODUCTS),
                suppliers=len(SUPPLIERS),
                customers=len(CUSTOMERS),
            )
        except Exception as exc:
            await session.rollback()
            logger.error("Seed failed — rolled back", error=str(exc))
            raise


if __name__ == "__main__":
    asyncio.run(main())
