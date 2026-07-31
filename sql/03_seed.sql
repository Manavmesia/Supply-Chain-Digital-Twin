-- =============================================================================
-- AI Supply Chain Digital Twin
-- File: sql/03_seed.sql
-- Description: Development seed data — products, customers, warehouses, suppliers
-- Run AFTER: 01_schema.sql, 02_indexes.sql
-- IMPORTANT: This is idempotent. Safe to run multiple times.
-- =============================================================================

BEGIN;

-- =============================================================================
-- SEED: CUSTOMERS (5 customers across tiers)
-- =============================================================================

INSERT INTO customers (customer_id, name, email, phone, address, city, country, customer_tier)
VALUES
    ('11111111-0000-0000-0000-000000000001', 'Acme Corporation',       'orders@acme.com',       '+1-555-0101', '100 Industrial Blvd',  'Chicago',    'US', 'enterprise'),
    ('11111111-0000-0000-0000-000000000002', 'TechWave Solutions',     'supply@techwave.io',    '+1-555-0102', '200 Silicon Ave',       'San Jose',   'US', 'premium'),
    ('11111111-0000-0000-0000-000000000003', 'GlobalMart Retail',      'procure@globalmart.com','+44-20-5551', '10 High Street',        'London',     'GB', 'enterprise'),
    ('11111111-0000-0000-0000-000000000004', 'Sunrise Electronics',    'ops@sunrise-elec.jp',   '+81-3-5551',  '5 Akihabara Square',    'Tokyo',      'JP', 'premium'),
    ('11111111-0000-0000-0000-000000000005', 'MedSupply Direct',       'orders@medsupply.de',   '+49-30-5551', '22 Logistics Park',     'Berlin',     'DE', 'standard')
ON CONFLICT (customer_id) DO NOTHING;


-- =============================================================================
-- SEED: PRODUCTS (10 products across categories)
-- =============================================================================

INSERT INTO products (product_id, sku, name, category, subcategory, unit_price, unit_of_measure, weight_kg, volume_m3)
VALUES
    ('22222222-0000-0000-0000-000000000001', 'ELEC-LAP-001', 'Business Laptop 15"',      'Electronics', 'Computers',    85000.00, 'unit',  2.1,   0.008),
    ('22222222-0000-0000-0000-000000000002', 'ELEC-MON-001', '4K Monitor 27"',           'Electronics', 'Displays',     45000.00, 'unit',  6.5,   0.025),
    ('22222222-0000-0000-0000-000000000003', 'ELEC-PHN-001', 'Enterprise Smartphone',    'Electronics', 'Mobile',       65000.00, 'unit',  0.19,  0.001),
    ('22222222-0000-0000-0000-000000000004', 'COMP-CPU-001', 'Server CPU 32-core',       'Components',  'Processors',  120000.00, 'unit',  0.35,  0.002),
    ('22222222-0000-0000-0000-000000000005', 'COMP-MEM-001', 'DDR5 RAM 64GB Module',     'Components',  'Memory',       18000.00, 'unit',  0.08,  0.0005),
    ('22222222-0000-0000-0000-000000000006', 'COMP-SSD-001', 'NVMe SSD 2TB',             'Components',  'Storage',      22000.00, 'unit',  0.06,  0.0004),
    ('22222222-0000-0000-0000-000000000007', 'NETW-SWT-001', 'Enterprise Switch 48-port','Networking',  'Switches',     95000.00, 'unit',  4.5,   0.018),
    ('22222222-0000-0000-0000-000000000008', 'NETW-RTR-001', 'Core Router',              'Networking',  'Routers',     150000.00, 'unit',  6.0,   0.022),
    ('22222222-0000-0000-0000-000000000009', 'PERI-KBD-001', 'Mechanical Keyboard',      'Peripherals', 'Input',         5500.00, 'unit',  0.95,  0.003),
    ('22222222-0000-0000-0000-000000000010', 'PERI-MSE-001', 'Ergonomic Mouse',          'Peripherals', 'Input',         3200.00, 'unit',  0.15,  0.0008)
ON CONFLICT (product_id) DO NOTHING;


-- =============================================================================
-- SEED: WAREHOUSES (3 strategic locations)
-- =============================================================================

INSERT INTO warehouses (warehouse_id, name, location, city, country, latitude, longitude, capacity_units, current_load, status)
VALUES
    ('33333333-0000-0000-0000-000000000001', 'WH-EAST-01',   'East Coast DC',     'Newark',    'US',  40.7357, -74.1724, 50000, 32000, 'active'),
    ('33333333-0000-0000-0000-000000000002', 'WH-WEST-01',   'West Coast DC',     'Los Angeles','US', 33.9425,-118.4081, 40000, 15000, 'active'),
    ('33333333-0000-0000-0000-000000000003', 'WH-EU-01',     'EU Distribution',   'Rotterdam', 'NL',  51.9244,   4.4777, 35000, 20000, 'active')
ON CONFLICT (warehouse_id) DO NOTHING;


-- =============================================================================
-- SEED: SUPPLIERS (5 suppliers with varying ratings)
-- =============================================================================

INSERT INTO suppliers (supplier_id, name, contact_email, country, rating, reliability_score, lead_time_days, payment_terms_days, status)
VALUES
    ('44444444-0000-0000-0000-000000000001', 'TechCore Manufacturing',   'supply@techcore.com',   'TW', 4.8, 96.0,  7, 30, 'active'),
    ('44444444-0000-0000-0000-000000000002', 'Global Components Ltd',    'orders@globalcomp.com', 'CN', 4.2, 85.0, 14, 45, 'active'),
    ('44444444-0000-0000-0000-000000000003', 'EU Electronic Parts',      'supply@euparts.de',     'DE', 4.5, 92.0,  5, 30, 'active'),
    ('44444444-0000-0000-0000-000000000004', 'FastShip Electronics',     'ops@fastship-e.com',    'SG', 3.8, 78.0,  3, 60, 'active'),
    ('44444444-0000-0000-0000-000000000005', 'Budget Parts Co',          'sales@budgetparts.com', 'IN', 2.9, 55.0, 21, 90, 'under_review')
ON CONFLICT (supplier_id) DO NOTHING;


-- =============================================================================
-- SEED: SUPPLIER–PRODUCT RELATIONSHIPS
-- =============================================================================

INSERT INTO supplier_products (supplier_id, product_id, contract_price, minimum_order_qty, is_preferred)
VALUES
    -- TechCore: Laptops, Monitors, Phones (preferred for electronics)
    ('44444444-0000-0000-0000-000000000001', '22222222-0000-0000-0000-000000000001', 72000.00, 10,  TRUE),
    ('44444444-0000-0000-0000-000000000001', '22222222-0000-0000-0000-000000000002', 38000.00, 20,  TRUE),
    ('44444444-0000-0000-0000-000000000001', '22222222-0000-0000-0000-000000000003', 55000.00, 50,  TRUE),
    -- Global Components: CPUs, Memory, SSDs
    ('44444444-0000-0000-0000-000000000002', '22222222-0000-0000-0000-000000000004', 95000.00,  5,  TRUE),
    ('44444444-0000-0000-0000-000000000002', '22222222-0000-0000-0000-000000000005', 14000.00, 100, TRUE),
    ('44444444-0000-0000-0000-000000000002', '22222222-0000-0000-0000-000000000006', 17000.00, 50,  TRUE),
    -- EU Parts: Networking equipment
    ('44444444-0000-0000-0000-000000000003', '22222222-0000-0000-0000-000000000007', 80000.00,  5,  TRUE),
    ('44444444-0000-0000-0000-000000000003', '22222222-0000-0000-0000-000000000008',125000.00,  2,  TRUE),
    -- FastShip: Peripherals (lower quality, faster delivery)
    ('44444444-0000-0000-0000-000000000004', '22222222-0000-0000-0000-000000000009',  4200.00, 200, FALSE),
    ('44444444-0000-0000-0000-000000000004', '22222222-0000-0000-0000-000000000010',  2400.00, 500, FALSE),
    -- Budget Parts: Peripherals (alternative, low rating)
    ('44444444-0000-0000-0000-000000000005', '22222222-0000-0000-0000-000000000009',  3800.00, 100, FALSE),
    ('44444444-0000-0000-0000-000000000005', '22222222-0000-0000-0000-000000000010',  2000.00, 200, FALSE),
    -- Cross-supplier: Laptops also available from Global Components (backup)
    ('44444444-0000-0000-0000-000000000002', '22222222-0000-0000-0000-000000000001', 75000.00, 20,  FALSE)
ON CONFLICT (supplier_id, product_id) DO NOTHING;


-- =============================================================================
-- SEED: INVENTORY (initial stock levels per product per warehouse)
-- =============================================================================

INSERT INTO inventory (product_id, warehouse_id, available_qty, reserved_qty, safety_stock, reorder_point, reorder_qty)
VALUES
    -- WH-EAST-01 (Newark — US East)
    ('22222222-0000-0000-0000-000000000001', '33333333-0000-0000-0000-000000000001', 500,  50, 100, 150, 200),  -- Laptops
    ('22222222-0000-0000-0000-000000000002', '33333333-0000-0000-0000-000000000001', 800,  80, 150, 200, 300),  -- Monitors
    ('22222222-0000-0000-0000-000000000003', '33333333-0000-0000-0000-000000000001', 1200, 120, 200, 300, 500), -- Phones
    ('22222222-0000-0000-0000-000000000004', '33333333-0000-0000-0000-000000000001', 200,  20,  50,  80, 100),  -- Server CPUs
    ('22222222-0000-0000-0000-000000000005', '33333333-0000-0000-0000-000000000001', 3000, 200, 500, 700, 1000),-- RAM
    ('22222222-0000-0000-0000-000000000006', '33333333-0000-0000-0000-000000000001', 2500, 150, 400, 600,  800), -- SSDs
    ('22222222-0000-0000-0000-000000000009', '33333333-0000-0000-0000-000000000001', 5000, 400, 800,1000, 2000), -- Keyboards
    ('22222222-0000-0000-0000-000000000010', '33333333-0000-0000-0000-000000000001', 6000, 500, 900,1200, 2500), -- Mice

    -- WH-WEST-01 (Los Angeles — US West)
    ('22222222-0000-0000-0000-000000000001', '33333333-0000-0000-0000-000000000002', 300,  30,  80, 120, 200),  -- Laptops
    ('22222222-0000-0000-0000-000000000002', '33333333-0000-0000-0000-000000000002', 400,  40, 100, 150, 200),  -- Monitors
    ('22222222-0000-0000-0000-000000000003', '33333333-0000-0000-0000-000000000002', 800,  80, 150, 250, 400),  -- Phones
    ('22222222-0000-0000-0000-000000000005', '33333333-0000-0000-0000-000000000002', 1500, 100, 300, 400, 600), -- RAM
    ('22222222-0000-0000-0000-000000000006', '33333333-0000-0000-0000-000000000002', 1200,  80, 200, 300, 500), -- SSDs
    ('22222222-0000-0000-0000-000000000009', '33333333-0000-0000-0000-000000000002', 2000, 200, 400, 500,1000), -- Keyboards
    ('22222222-0000-0000-0000-000000000010', '33333333-0000-0000-0000-000000000002', 2500, 200, 400, 600,1000), -- Mice

    -- WH-EU-01 (Rotterdam — Europe)
    ('22222222-0000-0000-0000-000000000001', '33333333-0000-0000-0000-000000000003', 400,  40, 100, 150, 200),  -- Laptops
    ('22222222-0000-0000-0000-000000000002', '33333333-0000-0000-0000-000000000003', 600,  60, 120, 180, 250),  -- Monitors
    ('22222222-0000-0000-0000-000000000003', '33333333-0000-0000-0000-000000000003', 1000, 100, 200, 300, 400), -- Phones
    ('22222222-0000-0000-0000-000000000007', '33333333-0000-0000-0000-000000000003', 150,  15,  40,  60, 100),  -- Switches
    ('22222222-0000-0000-0000-000000000008', '33333333-0000-0000-0000-000000000003', 80,    8,  20,  30,  50),  -- Routers
    ('22222222-0000-0000-0000-000000000009', '33333333-0000-0000-0000-000000000003', 3000, 300, 600, 800,1500), -- Keyboards
    ('22222222-0000-0000-0000-000000000010', '33333333-0000-0000-0000-000000000003', 4000, 400, 700,1000,1800)  -- Mice
ON CONFLICT (product_id, warehouse_id) DO NOTHING;


-- =============================================================================
-- SEED: AGENT RUNTIME REGISTRY (all 18 agents)
-- =============================================================================

INSERT INTO agent_runtime (agent_id, agent_name, agent_code, status, version)
VALUES
    -- Operational Agents
    ('55555555-0000-0000-0000-000000000001', 'Order Management Agent',    'ADS-01', 'idle', '1.0.0'),
    ('55555555-0000-0000-0000-000000000002', 'Demand Forecast Agent',     'ADS-02', 'idle', '1.0.0'),
    ('55555555-0000-0000-0000-000000000003', 'Inventory Agent',           'ADS-03', 'idle', '1.0.0'),
    ('55555555-0000-0000-0000-000000000004', 'Warehouse Agent',           'ADS-04', 'idle', '1.0.0'),
    ('55555555-0000-0000-0000-000000000005', 'Supplier Agent',            'ADS-05', 'idle', '1.0.0'),
    ('55555555-0000-0000-0000-000000000006', 'Transportation Agent',      'ADS-06', 'idle', '1.0.0'),
    ('55555555-0000-0000-0000-000000000007', 'Manufacturing Agent',       'ADS-07', 'idle', '1.0.0'),
    ('55555555-0000-0000-0000-000000000008', 'Customer Service Agent',    'ADS-08', 'idle', '1.0.0'),
    -- Business Intelligence Agents
    ('55555555-0000-0000-0000-000000000009', 'Finance Agent',             'ADS-09', 'idle', '1.0.0'),
    ('55555555-0000-0000-0000-000000000010', 'Risk Management Agent',     'ADS-10', 'idle', '1.0.0'),
    ('55555555-0000-0000-0000-000000000011', 'Pricing Agent',             'ADS-11', 'idle', '1.0.0'),
    ('55555555-0000-0000-0000-000000000012', 'Procurement Strategy Agent','ADS-12', 'idle', '1.0.0'),
    ('55555555-0000-0000-0000-000000000013', 'Sustainability Agent',      'ADS-13', 'idle', '1.0.0'),
    ('55555555-0000-0000-0000-000000000014', 'Quality Assurance Agent',   'ADS-14', 'idle', '1.0.0'),
    -- Coordination Agents
    ('55555555-0000-0000-0000-000000000015', 'Planner Agent',             'ADS-15', 'idle', '1.0.0'),
    ('55555555-0000-0000-0000-000000000016', 'Negotiation Agent',         'ADS-16', 'idle', '1.0.0'),
    ('55555555-0000-0000-0000-000000000017', 'CEO Agent',                 'ADS-17', 'idle', '1.0.0'),
    ('55555555-0000-0000-0000-000000000018', 'Reporting Agent',           'ADS-18', 'idle', '1.0.0')
ON CONFLICT (agent_id) DO NOTHING;


-- =============================================================================
-- SEED: SEMANTIC DOCUMENTS (SOPs and policies for vector memory)
-- Note: embeddings are NOT seeded here — they are generated at runtime
--       by calling the embedding model on first load.
-- =============================================================================

INSERT INTO semantic_documents (doc_id, doc_type, title, content, source, metadata)
VALUES
    (
        '66666666-0000-0000-0000-000000000001',
        'policy',
        'Safety Stock Policy',
        'Safety stock must be maintained at all times for all active products. ' ||
        'Safety stock levels are calculated as: average daily demand × lead time days × safety factor (1.5). ' ||
        'Violation of safety stock requires written CEO approval and must be logged as a critical audit event. ' ||
        'The Inventory Agent must never allow available_qty to fall below safety_stock without executive approval.',
        'System Rules v1.0 §6',
        '{"version": "1.0", "applies_to": "ADS-03", "priority": "critical"}'
    ),
    (
        '66666666-0000-0000-0000-000000000002',
        'policy',
        'Supplier Blacklist Policy',
        'Suppliers with status = blacklisted must never receive purchase orders. ' ||
        'A supplier may be blacklisted due to: repeated delivery failures (3+ in 90 days), ' ||
        'quality defect rate exceeding 5%, payment disputes, regulatory violations, or executive directive. ' ||
        'Blacklist changes require CEO approval and are logged immutably in the audit trail. ' ||
        'The Supplier Agent must check blacklist status before any supplier selection.',
        'System Rules v1.0 §6',
        '{"version": "1.0", "applies_to": "ADS-05", "priority": "critical"}'
    ),
    (
        '66666666-0000-0000-0000-000000000003',
        'sop',
        'Emergency Procurement SOP',
        'Standard Operating Procedure for Emergency Procurement: ' ||
        '1. Inventory Agent detects stock below safety stock level. ' ||
        '2. Supplier Agent evaluates all active suppliers for fastest available lead time. ' ||
        '3. Finance Agent approves emergency budget (override requires CEO approval if > $50,000). ' ||
        '4. Risk Agent evaluates supplier reliability for the emergency order. ' ||
        '5. CEO Agent issues final approval for any emergency procurement exceeding $50,000. ' ||
        '6. Purchase Order is created and PurchaseOrderCreated event is published. ' ||
        '7. Transportation Agent selects fastest carrier regardless of cost for critical orders. ' ||
        '8. Customer Service Agent notifies affected customers of potential delays.',
        'Operations Manual §4.2',
        '{"version": "1.0", "applies_to": ["ADS-03", "ADS-05", "ADS-09", "ADS-17"], "priority": "high"}'
    ),
    (
        '66666666-0000-0000-0000-000000000004',
        'policy',
        'Finance Approval Thresholds',
        'Financial approval authority matrix: ' ||
        'Up to $10,000: Automatic system approval. ' ||
        '$10,001 to $50,000: Finance Agent approval required. ' ||
        '$50,001 to $500,000: Finance Agent + CEO Agent approval required. ' ||
        'Over $500,000: Finance Agent + CEO Agent + Human approval required (interrupt workflow). ' ||
        'Emergency orders may bypass Finance Agent approval if CEO Agent grants emergency authority. ' ||
        'All approvals are logged in finance_transactions and audit_logs.',
        'Finance Policy v2.1',
        '{"version": "2.1", "applies_to": ["ADS-09", "ADS-17"], "priority": "high"}'
    ),
    (
        '66666666-0000-0000-0000-000000000005',
        'policy',
        'Transportation Priority Policy',
        'Transportation selection policy: ' ||
        'For standard orders: select the carrier that minimizes total_cost = freight_cost + handling_cost. ' ||
        'For high-priority orders: select the carrier that minimizes transit_time_days. ' ||
        'For critical orders: always select air freight regardless of cost; CEO notification required. ' ||
        'Sustainability scoring: prefer carriers with lower CO2 per tonne-km when cost difference < 10%. ' ||
        'Carrier blacklisting: same policy as supplier blacklisting applies to carriers.',
        'Logistics Policy v1.3',
        '{"version": "1.3", "applies_to": "ADS-06", "priority": "medium"}'
    )
ON CONFLICT (doc_id) DO NOTHING;


-- =============================================================================
-- VERIFICATION QUERIES (run these to validate seed data)
-- =============================================================================
-- SELECT COUNT(*) FROM customers;           -- Expected: 5
-- SELECT COUNT(*) FROM products;            -- Expected: 10
-- SELECT COUNT(*) FROM warehouses;          -- Expected: 3
-- SELECT COUNT(*) FROM suppliers;           -- Expected: 5
-- SELECT COUNT(*) FROM supplier_products;   -- Expected: 13
-- SELECT COUNT(*) FROM inventory;           -- Expected: 22
-- SELECT COUNT(*) FROM agent_runtime;       -- Expected: 18
-- SELECT COUNT(*) FROM semantic_documents;  -- Expected: 5


COMMIT;

-- =============================================================================
-- END OF 03_seed.sql
-- =============================================================================
