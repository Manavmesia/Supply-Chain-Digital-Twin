-- =============================================================================
-- AI Supply Chain Digital Twin
-- File: sql/04_seed_supplementary.sql
-- Description: Seed data for supplementary tables (US-61)
--              Carriers · Transportation Routes · Contracts · Promotions
-- Run AFTER: 01_schema.sql, 02_indexes.sql, 03_seed.sql
-- IMPORTANT: Fully idempotent — safe to run multiple times.
-- =============================================================================

BEGIN;

-- =============================================================================
-- SEED: CARRIERS (5 global logistics carriers)
-- Referenced by: AIS-06 Transportation Agent, CarrierRepository
-- =============================================================================

INSERT INTO carriers (
    carrier_id, name, code, freight_modes, tracking_url, reliability_score, avg_delay_days, status
) VALUES
    (
        'cc000000-0000-0000-0000-000000000001',
        'FedEx International',
        'FEDEX',
        ARRAY['air', 'road']::freight_mode_type[],
        'https://www.fedex.com/fedextrack/?trknbr={tracking_id}',
        94.50, 0.30, 'active'
    ),
    (
        'cc000000-0000-0000-0000-000000000002',
        'DHL Express',
        'DHL',
        ARRAY['air', 'road', 'multimodal']::freight_mode_type[],
        'https://www.dhl.com/en/express/tracking.html?AWB={tracking_id}',
        92.00, 0.50, 'active'
    ),
    (
        'cc000000-0000-0000-0000-000000000003',
        'Maersk Line',
        'MAERSK',
        ARRAY['sea', 'multimodal']::freight_mode_type[],
        'https://www.maersk.com/tracking/{tracking_id}',
        88.00, 1.20, 'active'
    ),
    (
        'cc000000-0000-0000-0000-000000000004',
        'DB Schenker',
        'DSCHENKER',
        ARRAY['road', 'rail', 'sea', 'multimodal']::freight_mode_type[],
        'https://www.dbschenker.com/track/{tracking_id}',
        85.00, 0.80, 'active'
    ),
    (
        'cc000000-0000-0000-0000-000000000005',
        'UPS Supply Chain',
        'UPS',
        ARRAY['air', 'road', 'multimodal']::freight_mode_type[],
        'https://www.ups.com/track?tracknum={tracking_id}',
        91.00, 0.40, 'active'
    )
ON CONFLICT (carrier_id) DO NOTHING;


-- =============================================================================
-- SEED: TRANSPORTATION ROUTES (10 routes covering major corridors)
-- origin_location / destination match warehouse city/country labels
-- Referenced by: TransportationRouteRepository.find_routes()
-- =============================================================================

INSERT INTO transportation_routes (
    route_id, carrier_id,
    origin_warehouse_id, origin_location, destination,
    freight_mode, transit_days, base_cost, cost_per_kg, cost_per_m3, co2_per_tonne_km, is_active
) VALUES
    -- ── Newark → Los Angeles ──────────────────────────────────────────────────
    (
        'rr000000-0000-0000-0000-000000000001',
        'cc000000-0000-0000-0000-000000000001',  -- FedEx
        '33333333-0000-0000-0000-000000000001',  -- WH-EAST-01 (Newark)
        'Newark, US', 'Los Angeles, US',
        'air', 2, 3500.00, 8.50, 180.00, 0.6200, TRUE
    ),
    (
        'rr000000-0000-0000-0000-000000000002',
        'cc000000-0000-0000-0000-000000000004',  -- DB Schenker
        '33333333-0000-0000-0000-000000000001',  -- WH-EAST-01 (Newark)
        'Newark, US', 'Los Angeles, US',
        'road', 5, 850.00, 1.20, 22.00, 0.0950, TRUE
    ),
    -- ── Los Angeles → Newark ──────────────────────────────────────────────────
    (
        'rr000000-0000-0000-0000-000000000003',
        'cc000000-0000-0000-0000-000000000005',  -- UPS
        '33333333-0000-0000-0000-000000000002',  -- WH-WEST-01 (LA)
        'Los Angeles, US', 'Newark, US',
        'air', 2, 3200.00, 8.00, 175.00, 0.6100, TRUE
    ),
    (
        'rr000000-0000-0000-0000-000000000004',
        'cc000000-0000-0000-0000-000000000004',  -- DB Schenker
        '33333333-0000-0000-0000-000000000002',  -- WH-WEST-01 (LA)
        'Los Angeles, US', 'Newark, US',
        'road', 5, 780.00, 1.15, 21.00, 0.0930, TRUE
    ),
    -- ── Newark → Rotterdam ────────────────────────────────────────────────────
    (
        'rr000000-0000-0000-0000-000000000005',
        'cc000000-0000-0000-0000-000000000002',  -- DHL
        '33333333-0000-0000-0000-000000000001',  -- WH-EAST-01 (Newark)
        'Newark, US', 'Rotterdam, NL',
        'air', 1, 6500.00, 12.00, 250.00, 0.5900, TRUE
    ),
    (
        'rr000000-0000-0000-0000-000000000006',
        'cc000000-0000-0000-0000-000000000003',  -- Maersk
        '33333333-0000-0000-0000-000000000001',  -- WH-EAST-01 (Newark)
        'Newark, US', 'Rotterdam, NL',
        'sea', 12, 1800.00, 0.80, 15.00, 0.0210, TRUE
    ),
    -- ── Rotterdam → Newark ────────────────────────────────────────────────────
    (
        'rr000000-0000-0000-0000-000000000007',
        'cc000000-0000-0000-0000-000000000002',  -- DHL
        '33333333-0000-0000-0000-000000000003',  -- WH-EU-01 (Rotterdam)
        'Rotterdam, NL', 'Newark, US',
        'air', 1, 6200.00, 11.50, 240.00, 0.5850, TRUE
    ),
    (
        'rr000000-0000-0000-0000-000000000008',
        'cc000000-0000-0000-0000-000000000003',  -- Maersk
        '33333333-0000-0000-0000-000000000003',  -- WH-EU-01 (Rotterdam)
        'Rotterdam, NL', 'Newark, US',
        'sea', 12, 1650.00, 0.75, 14.50, 0.0205, TRUE
    ),
    -- ── Los Angeles → Rotterdam ───────────────────────────────────────────────
    (
        'rr000000-0000-0000-0000-000000000009',
        'cc000000-0000-0000-0000-000000000001',  -- FedEx
        '33333333-0000-0000-0000-000000000002',  -- WH-WEST-01 (LA)
        'Los Angeles, US', 'Rotterdam, NL',
        'air', 2, 7200.00, 13.00, 265.00, 0.6300, TRUE
    ),
    -- ── Rotterdam → Los Angeles ───────────────────────────────────────────────
    (
        'rr000000-0000-0000-0000-000000000010',
        'cc000000-0000-0000-0000-000000000003',  -- Maersk
        '33333333-0000-0000-0000-000000000003',  -- WH-EU-01 (Rotterdam)
        'Rotterdam, NL', 'Los Angeles, US',
        'sea', 18, 2100.00, 0.90, 16.00, 0.0220, TRUE
    )
ON CONFLICT (route_id) DO NOTHING;


-- =============================================================================
-- SEED: CONTRACTS (3 supplier contracts — 1 near-expiry for ContractExpiring event)
-- Referenced by: ContractRepository, AIS-12 Procurement Strategy Agent
-- =============================================================================

INSERT INTO contracts (
    contract_id, supplier_id, contract_reference, title, status,
    contract_type, total_value, currency,
    start_date, end_date, auto_renew, notice_period_days, payment_terms_days
) VALUES
    (
        -- Long-term active contract with TechCore (primary electronics supplier)
        'ct000000-0000-0000-0000-000000000001',
        '44444444-0000-0000-0000-000000000001',  -- TechCore Manufacturing
        'CTR-2025-TC-001',
        'TechCore Long-Term Supply Agreement 2025–2027',
        'active',
        'long_term',
        12000000.00, 'USD',
        '2025-01-01', '2027-12-31',
        TRUE, 90, 30
    ),
    (
        -- Active framework contract with Global Components
        'ct000000-0000-0000-0000-000000000002',
        '44444444-0000-0000-0000-000000000002',  -- Global Components Ltd
        'CTR-2025-GC-001',
        'Global Components Framework Agreement',
        'active',
        'framework',
        5000000.00, 'USD',
        '2025-03-01', '2026-08-31',
        FALSE, 60, 45
    ),
    (
        -- Near-expiry contract with EU Electronic Parts — triggers ContractExpiring
        -- Expires in ~25 days from the seed date (2026-08-24)
        'ct000000-0000-0000-0000-000000000003',
        '44444444-0000-0000-0000-000000000003',  -- EU Electronic Parts
        'CTR-2025-EU-001',
        'EU Electronic Parts Spot Contract',
        'expiring_soon',
        'spot',
        800000.00, 'EUR',
        '2025-09-01', (CURRENT_DATE + INTERVAL '25 days')::DATE,
        FALSE, 30, 30
    )
ON CONFLICT (contract_id) DO NOTHING;


-- Contract products — link products to each contract
INSERT INTO contract_products (contract_id, product_id, contracted_price, min_volume, max_volume)
VALUES
    -- TechCore contract covers laptops, monitors, phones
    ('ct000000-0000-0000-0000-000000000001', '22222222-0000-0000-0000-000000000001', 70000.00, 10,  500),
    ('ct000000-0000-0000-0000-000000000001', '22222222-0000-0000-0000-000000000002', 37000.00, 20,  1000),
    ('ct000000-0000-0000-0000-000000000001', '22222222-0000-0000-0000-000000000003', 54000.00, 50,  2000),
    -- Global Components covers CPUs, memory, SSDs
    ('ct000000-0000-0000-0000-000000000002', '22222222-0000-0000-0000-000000000004', 93000.00, 5,   200),
    ('ct000000-0000-0000-0000-000000000002', '22222222-0000-0000-0000-000000000005', 13500.00, 100, 5000),
    ('ct000000-0000-0000-0000-000000000002', '22222222-0000-0000-0000-000000000006', 16500.00, 50,  3000),
    -- EU contract covers networking equipment
    ('ct000000-0000-0000-0000-000000000003', '22222222-0000-0000-0000-000000000007', 78000.00, 5,   100),
    ('ct000000-0000-0000-0000-000000000003', '22222222-0000-0000-0000-000000000008',120000.00, 2,   50)
ON CONFLICT (contract_id, product_id) DO NOTHING;


-- =============================================================================
-- SEED: PROMOTIONS (2 promotions — 1 active, 1 scheduled for +7 days)
-- Referenced by: PromotionRepository, AIS-02 Demand Forecast Agent
-- =============================================================================

INSERT INTO promotions (
    promotion_id, name, description, status,
    discount_percent, discount_amount,
    starts_at, ends_at, target_segment
) VALUES
    (
        -- Active promotion: Electronics Summer Sale (running now)
        'pp000000-0000-0000-0000-000000000001',
        'Electronics Summer Sale 2026',
        'Seasonal discount on laptops and monitors for enterprise customers.',
        'active',
        15.00, NULL,
        NOW() - INTERVAL '2 days',
        NOW() + INTERVAL '12 days',
        'enterprise'
    ),
    (
        -- Scheduled promotion: Networking Equipment Bundle (starts in 7 days)
        'pp000000-0000-0000-0000-000000000002',
        'Q3 Networking Bundle Promotion',
        'Bundled discount on switches and routers for premium and enterprise customers.',
        'scheduled',
        10.00, NULL,
        NOW() + INTERVAL '7 days',
        NOW() + INTERVAL '21 days',
        'premium'
    )
ON CONFLICT (promotion_id) DO NOTHING;


-- Promotion products — which products each promotion covers
INSERT INTO promotion_products (promotion_id, product_id)
VALUES
    -- Electronics Summer Sale covers laptops + monitors
    ('pp000000-0000-0000-0000-000000000001', '22222222-0000-0000-0000-000000000001'),  -- Laptop
    ('pp000000-0000-0000-0000-000000000001', '22222222-0000-0000-0000-000000000002'),  -- Monitor
    -- Networking Bundle covers switches + routers
    ('pp000000-0000-0000-0000-000000000002', '22222222-0000-0000-0000-000000000007'),  -- Switch
    ('pp000000-0000-0000-0000-000000000002', '22222222-0000-0000-0000-000000000008')   -- Router
ON CONFLICT (promotion_id, product_id) DO NOTHING;


-- Also add the carrier_id FK to the shipments table now that carriers exist
-- This ALTER is idempotent — skipped if column already exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'shipments' AND column_name = 'carrier_id'
    ) THEN
        ALTER TABLE shipments
            ADD COLUMN carrier_id UUID REFERENCES carriers(carrier_id)
                ON UPDATE CASCADE ON DELETE SET NULL;
    END IF;
END;
$$;


COMMIT;

-- =============================================================================
-- VERIFICATION QUERIES
-- =============================================================================
-- SELECT COUNT(*) FROM carriers;               -- Expected: 5
-- SELECT COUNT(*) FROM transportation_routes;  -- Expected: 10
-- SELECT COUNT(*) FROM contracts;              -- Expected: 3
-- SELECT COUNT(*) FROM contract_products;      -- Expected: 8
-- SELECT COUNT(*) FROM promotions;             -- Expected: 2
-- SELECT COUNT(*) FROM promotion_products;     -- Expected: 4
-- SELECT * FROM contracts WHERE status = 'expiring_soon'; -- Expected: 1 (EU contract)
-- SELECT * FROM promotions WHERE status = 'active';       -- Expected: 1 (Summer Sale)
-- =============================================================================
-- END OF 04_seed_supplementary.sql
-- =============================================================================
