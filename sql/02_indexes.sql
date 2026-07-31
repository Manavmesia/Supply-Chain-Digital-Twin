-- =============================================================================
-- AI Supply Chain Digital Twin
-- File: sql/02_indexes.sql
-- Description: All indexes — composite, GIN (JSONB), vector (pgvector), partial
-- Database: PostgreSQL 16
-- Run AFTER: 01_schema.sql
-- =============================================================================

-- =============================================================================
-- PRIMARY KEY INDEXES (auto-created, listed here for documentation)
-- =============================================================================
-- customers.customer_id      ← B-tree (auto)
-- products.product_id        ← B-tree (auto)
-- orders.order_id            ← B-tree (auto)
-- order_items.order_item_id  ← B-tree (auto)
-- inventory.inventory_id     ← B-tree (auto)
-- warehouses.warehouse_id    ← B-tree (auto)
-- suppliers.supplier_id      ← B-tree (auto)
-- shipments.shipment_id      ← B-tree (auto)
-- manufacturing_orders.mo_id ← B-tree (auto)
-- finance_transactions.txn_id← B-tree (auto)
-- risk_assessments.risk_id   ← B-tree (auto)
-- sustainability_metrics.metric_id ← B-tree (auto)
-- quality_inspections.inspection_id← B-tree (auto)
-- demand_forecasts.forecast_id     ← B-tree (auto)
-- events.event_id            ← B-tree (auto)
-- audit_logs.log_id          ← B-tree (auto)
-- agent_runtime.agent_id     ← B-tree (auto)
-- semantic_documents.doc_id  ← B-tree (auto)


-- =============================================================================
-- UNIQUE INDEXES (in addition to UNIQUE constraints in schema)
-- =============================================================================

-- Already defined via UNIQUE constraints in 01_schema.sql:
--   customers.email
--   products.sku
--   inventory(product_id, warehouse_id)
--   agent_runtime.agent_code


-- =============================================================================
-- COMPOSITE INDEXES — from DDD §7
-- =============================================================================

-- Orders: query by status (most common filter) + created_at for range queries
CREATE INDEX idx_orders_status_created
    ON orders (status, created_at DESC);

-- Orders: workflow lookup
CREATE INDEX idx_orders_workflow_id
    ON orders (workflow_id)
    WHERE workflow_id IS NOT NULL;

-- Orders: customer's order history
CREATE INDEX idx_orders_customer_id
    ON orders (customer_id, created_at DESC);

-- Inventory: most common join key
CREATE INDEX idx_inventory_product_warehouse
    ON inventory (product_id, warehouse_id);

-- Inventory: find low-stock items (available below reorder point)
CREATE INDEX idx_inventory_available_qty
    ON inventory (available_qty)
    WHERE available_qty <= reorder_point;
-- Partial index: only indexes records that are actually low

-- Shipments: agent tracking queries
CREATE INDEX idx_shipments_status_eta
    ON shipments (status, eta);

-- Shipments: by order (most common lookup)
CREATE INDEX idx_shipments_order_id
    ON shipments (order_id);

-- Finance: per-order transaction audit
CREATE INDEX idx_finance_order_type
    ON finance_transactions (order_id, transaction_type)
    WHERE order_id IS NOT NULL;

-- Finance: per-supplier transaction history
CREATE INDEX idx_finance_supplier
    ON finance_transactions (supplier_id, created_at DESC)
    WHERE supplier_id IS NOT NULL;

-- Finance: chronological lookup for period reporting
CREATE INDEX idx_finance_created_at
    ON finance_transactions (created_at DESC);

-- Risk: entity lookup (AUD-22 fix — entity_type is now typed enum)
CREATE INDEX idx_risk_entity_type_id
    ON risk_assessments (entity_type, entity_id);

-- Risk: find unresolved high-score risks
CREATE INDEX idx_risk_score_unresolved
    ON risk_assessments (risk_score DESC)
    WHERE mitigation_status NOT IN ('resolved', 'ignored');
-- Partial index: only unresolved risks

-- Audit logs: agent-level audit trail
CREATE INDEX idx_audit_agent_created
    ON audit_logs (agent_id, created_at DESC);

-- Audit logs: workflow-level audit trail
CREATE INDEX idx_audit_workflow_id
    ON audit_logs (workflow_id, created_at DESC)
    WHERE workflow_id IS NOT NULL;

-- Audit logs: correlation trail
CREATE INDEX idx_audit_correlation_id
    ON audit_logs (correlation_id)
    WHERE correlation_id IS NOT NULL;

-- Manufacturing orders: by product and status
CREATE INDEX idx_mo_product_status
    ON manufacturing_orders (product_id, status);

-- Manufacturing orders: by warehouse
CREATE INDEX idx_mo_warehouse_id
    ON manufacturing_orders (warehouse_id);

-- Quality inspections: by product
CREATE INDEX idx_quality_product_id
    ON quality_inspections (product_id, inspected_at DESC);

-- Quality inspections: by supplier (AUD-21 fix)
CREATE INDEX idx_quality_supplier_id
    ON quality_inspections (supplier_id)
    WHERE supplier_id IS NOT NULL;

-- Quality inspections: by manufacturing order (AUD-21 fix)
CREATE INDEX idx_quality_mo_id
    ON quality_inspections (manufacturing_order_id)
    WHERE manufacturing_order_id IS NOT NULL;

-- Demand forecasts: by product + period (Demand Forecast Agent query)
CREATE INDEX idx_forecast_product_period
    ON demand_forecasts (product_id, forecast_period DESC);

-- Demand forecasts: anomaly detection queries
CREATE INDEX idx_forecast_anomalies
    ON demand_forecasts (product_id, forecast_period)
    WHERE is_anomaly = TRUE;
-- Partial index: only anomalous forecasts

-- Supplier products: find all products for a supplier
CREATE INDEX idx_supplier_products_supplier
    ON supplier_products (supplier_id);

-- Supplier products: find all suppliers for a product
CREATE INDEX idx_supplier_products_product
    ON supplier_products (product_id);

-- Agent runtime: find active agents
CREATE INDEX idx_agent_runtime_status
    ON agent_runtime (status, last_heartbeat DESC);


-- =============================================================================
-- EVENT TABLE INDEXES
-- =============================================================================

-- Events: correlation ID is the primary lookup key for tracing a workflow
CREATE UNIQUE INDEX idx_events_correlation_event
    ON events (correlation_id, event_id);
-- Unique: guarantees idempotent event delivery per correlation

-- Events: lookup by type (e.g., find all OrderCreated events)
CREATE INDEX idx_events_type_created
    ON events (event_type, created_at DESC);

-- Events: workflow-level event history
CREATE INDEX idx_events_workflow_id
    ON events (workflow_id, created_at)
    WHERE workflow_id IS NOT NULL;

-- Events: simulation isolation — production vs simulation queries
CREATE INDEX idx_events_simulation_id
    ON events (simulation_id)
    WHERE simulation_id IS NOT NULL;
-- Partial index: only simulation events

-- Events: source agent lookup
CREATE INDEX idx_events_source_agent
    ON events (source_agent, created_at DESC);


-- =============================================================================
-- JSONB GIN INDEXES — for querying inside JSONB payload columns
-- =============================================================================

-- Events payload: allows queries like payload->>'product_id' = '...'
CREATE INDEX idx_events_payload_gin
    ON events
    USING GIN (payload);

-- Events metadata: allows querying retry counts, workflow metadata
CREATE INDEX idx_events_metadata_gin
    ON events
    USING GIN (metadata);

-- Audit logs payload: query before/after state change content
CREATE INDEX idx_audit_payload_gin
    ON audit_logs
    USING GIN (payload);

-- Risk assessments: store extended risk factors in metadata
-- (query specific risk factors without schema changes)
CREATE INDEX idx_risk_mitigation_gin
    ON risk_assessments
    USING GIN (to_tsvector('english', COALESCE(mitigation_plan, '')));
-- Full-text search on mitigation plans

-- Sustainability: query green_alternatives recommendations
CREATE INDEX idx_sustainability_alternatives_gin
    ON sustainability_metrics
    USING GIN (green_alternatives)
    WHERE green_alternatives IS NOT NULL;

-- Semantic documents: full-text search on content
CREATE INDEX idx_semantic_content_fts
    ON semantic_documents
    USING GIN (to_tsvector('english', content));


-- =============================================================================
-- VECTOR INDEX (pgvector) — HNSW for semantic similarity search
-- =============================================================================

-- HNSW index on embeddings: recommended for low-latency ANN search
-- Parameters: m=16 (connections per node), ef_construction=64 (build quality)
CREATE INDEX idx_semantic_embedding_hnsw
    ON semantic_documents
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

COMMENT ON INDEX idx_semantic_embedding_hnsw IS
    'HNSW index for approximate nearest-neighbor search. Used by Negotiation Agent for SOP/contract retrieval.';


-- =============================================================================
-- TABLE PARTITIONING — events table (monthly)
-- Already declared in schema as regular table.
-- For high-volume production, convert to partitioned table:
-- =============================================================================

-- NOTE: To enable monthly partitioning for the events table in production,
-- convert it to PARTITION BY RANGE (created_at) and create monthly child tables.
-- Example (run in production migration, not here):
--
-- CREATE TABLE events_2026_01 PARTITION OF events
--     FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
--
-- CREATE TABLE events_2026_02 PARTITION OF events
--     FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
--
-- Use a maintenance script to create future partitions automatically.
-- The pg_partman extension is recommended for this.


-- =============================================================================
-- STATISTICS: Improve query planner accuracy for skewed distributions
-- =============================================================================

ALTER TABLE orders ALTER COLUMN status SET STATISTICS 200;
ALTER TABLE events ALTER COLUMN event_type SET STATISTICS 200;
ALTER TABLE inventory ALTER COLUMN available_qty SET STATISTICS 200;
ALTER TABLE risk_assessments ALTER COLUMN risk_score SET STATISTICS 200;

-- =============================================================================
-- END OF 02_indexes.sql
-- =============================================================================
