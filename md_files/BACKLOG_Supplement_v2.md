# AI Supply Chain Digital Twin
# Backlog Supplement — Version 2

> **Document:** BACKLOG_Supplement_v2.md
> **Version:** 1.0
> **Date:** 2026-07-28
> **Extends:** enterprise_audit_and_epics.md (US-01 to US-58, EP-01 to EP-13)
> **Scope:** Part A — Schema Gap Stories (US-59 to US-66) | Part B — EP-14 Event Compliance | Part C — Granular Per-Agent Stories (US-67 to US-156, EP-15 to EP-32)
> **Resolves:** AUD-39 to AUD-56 (all 18 AIS cross-reference gaps)

---

## Running Total

| Metric | Previous | This Supplement | Grand Total |
|---|---|---|---|
| Epics | 13 | 20 | **33** |
| User Stories | 58 | 98 | **156** |
| Story Points | ~210 | ~385 | **~595** |
| Agents Fully Specified | 6 (MVP) | +12 (all remaining) | **18** |
| Audit Issues Resolved | 30 | +18 | **48** |

---

# PART A — Schema Gap Stories (EP-02 Extension)

> These stories extend EP-02 (Shared Data Infrastructure) to include the 9 supplementary tables discovered during the AIS cross-reference audit (AUD-39 to AUD-46). They must be completed **before** the agents that use them are implemented.

---

## US-59 · Alembic Migrations for Supplementary Tables

- **Epic:** EP-02 (Extension)
- **Sprint Target:** Sprint 3 (alongside US-06 to US-11)
- **Resolves:** AUD-39, AUD-40, AUD-41, AUD-42, AUD-43, AUD-45, AUD-46
- **Description:** As a database engineer, I want Alembic migration scripts for all 9 supplementary tables — `purchase_orders`, `support_tickets`, `pricing_history`, `contracts`, `contract_products`, `carriers`, `transportation_routes`, `promotions`, `promotion_products`, and `reports` — so that the schema is complete before any dependent agent is implemented.
- **Technical Notes:**
  - Create a single Alembic revision: `add_supplementary_tables`
  - Apply all ENUMs first: `purchase_order_status`, `ticket_status`, `ticket_category`, `pricing_trigger`, `contract_status`, `carrier_status`, `freight_mode_type`, `promotion_status`, `report_type`, `report_status`
  - Create tables in dependency order: `carriers` → `transportation_routes` → `purchase_orders` → `support_tickets` → `pricing_history` → `contracts` → `contract_products` → `promotions` → `promotion_products` → `reports`
  - Apply `ALTER TABLE shipments ADD COLUMN carrier_id UUID REFERENCES carriers`
  - All FK constraints and CHECK constraints from `01_schema.sql v1.1` must be included
- **Acceptance Criteria:**
  - `alembic upgrade head` creates all 10 supplementary tables without errors
  - `alembic downgrade -1` reverses cleanly
  - All FKs reference existing tables
  - `shipments.carrier_id` column exists and is nullable
- **Definition of Done:** Migration reviewed · Runs in CI · Schema diff verified against `01_schema.sql v1.1`
- **Story Points:** 5 | **Priority:** P0

---

## US-60 · SQLAlchemy ORM Models for Supplementary Tables

- **Epic:** EP-02 (Extension)
- **Sprint Target:** Sprint 3
- **Resolves:** AUD-39 to AUD-46
- **Description:** As a backend engineer, I want SQLAlchemy ORM model classes and repository classes for all 9 supplementary tables so that agents can access these tables through the standard data access layer.
- **Technical Notes:**
  - One model class per table in `backend/app/models/`
  - Repository classes in `backend/app/repositories/` with: `get_by_id`, `list`, `create`, `update` (where permitted), and any domain-specific queries
  - `PurchaseOrderRepository`: `get_by_supplier()`, `get_by_status()`, `get_pending_delivery()`
  - `SupportTicketRepository`: `get_open_by_customer()`, `get_sla_breaching()`, `escalate()`
  - `PricingHistoryRepository`: `get_latest_by_product()`, `get_pending_approval()`
  - `ContractRepository`: `get_expiring_soon(days)`, `get_active_by_supplier()`
  - `CarrierRepository`: `get_available(freight_mode)`, `get_by_reliability_threshold(min_score)`
  - `TransportationRouteRepository`: `find_routes(origin, destination, mode)`, `cheapest_route()`, `fastest_route()`
  - `PromotionRepository`: `get_active_promotions()`, `get_by_product(product_id)`
  - `ReportRepository`: `get_by_type()`, `get_by_workflow()`, `archive(report_id)`
  - `purchase_history` is a view — add read-only model using `__table_args__ = {'info': {'is_view': True}}`
- **Acceptance Criteria:**
  - All models map to correct tables. All repository methods unit-tested.
  - `purchase_history` view is queryable via ORM. Coverage ≥ 80%.
- **Definition of Done:** Reviewed · Unit tests pass · Coverage verified
- **Story Points:** 8 | **Priority:** P0

---

## US-61 · Seed Data for Supplementary Tables

- **Epic:** EP-02 (Extension)
- **Sprint Target:** Sprint 3
- **Description:** As a developer, I want realistic seed data for carriers, transportation routes, promotions, and contracts so that Transportation, Demand Forecast, and Procurement Strategy agents have reference data to operate against during local development and testing.
- **Technical Notes:**
  - Carriers: 5 seed carriers (FedEx, DHL, Maersk, DB Schenker, UPS) with realistic reliability scores and supported modes
  - Transportation Routes: 10 seed routes covering air/sea/road between major warehouse cities
  - Contracts: 3 seed contracts with 1 expiring within 30 days (to test `ContractExpiring` event)
  - Promotions: 2 seed promotions — 1 active, 1 scheduled for +7 days
  - All seed data must satisfy constraints and FK relationships
  - Idempotent: use `INSERT ... ON CONFLICT DO NOTHING`
- **Acceptance Criteria:** Seed script runs without errors. Route query returns ≥ 1 result for each freight mode. Contract expiry check finds the near-expiry contract.
- **Definition of Done:** Reviewed · Idempotent · Integrated into development startup flow
- **Story Points:** 3 | **Priority:** P0

---

## US-62 · Supplementary Table Indexes Migration

- **Epic:** EP-02 (Extension)
- **Sprint Target:** Sprint 3
- **Description:** As a database engineer, I want all performance indexes for supplementary tables applied in a dedicated Alembic migration so that query performance targets are met from the first deployment.
- **Technical Notes:**
  - Apply all indexes defined at end of `01_schema.sql v1.1`: `idx_po_supplier_status`, `idx_po_product_id`, `idx_po_workflow_id`, `idx_po_created_at`, `idx_tickets_customer_status`, `idx_tickets_sla_deadline`, `idx_pricing_product_created`, `idx_pricing_pending`, `idx_contracts_supplier`, `idx_contracts_end_date`, `idx_carriers_status`, `idx_routes_carrier`, `idx_routes_origin_dest`, `idx_promotions_active`, `idx_reports_type_status`, `idx_reports_workflow_id`
  - Separate Alembic revision from US-59 for clean rollback
- **Acceptance Criteria:** All 16 indexes created. `EXPLAIN ANALYZE` on representative queries confirms index usage.
- **Definition of Done:** Reviewed · Index creation verified
- **Story Points:** 2 | **Priority:** P0

---

# PART B — EP-14: Canonical Event Glossary Compliance

**Epic ID:** EP-14
**Objective:** Enforce the canonical event name glossary across all AIS specifications, fix all broken subscription chains, and establish runtime validation so event naming drift never re-occurs.
**Sprint Target:** Sprint 5 (alongside EP-03 Event Bus setup)
**Resolves:** AUD-47, AUD-48, AUD-49, AUD-50, AUD-51, AUD-52, AUD-53, AUD-54, AUD-55, AUD-56
**Priority:** P0 — Must be complete before any agent is coded. Event names once hardcoded in agent handlers are expensive to change.

**Acceptance Criteria:**
- All 13 event name mismatches corrected in AIS documentation
- All dead subscriptions have a publisher defined
- Celery scheduled publishers operational for `ContractExpiring`, `PromotionScheduled`
- Runtime validator rejects any event not in the canonical registry at publish time

---

## US-63 · Fix Event Name Mismatches in AIS Documentation

- **Epic:** EP-14
- **Sprint Target:** Sprint 5
- **Resolves:** AUD-47, AUD-53, AUD-54, AUD-55
- **Description:** As a technical writer/architect, I want all AIS files updated to use canonical event names from `CANONICAL_Event_Glossary.md` so that no agent implementation uses a non-existent event name.
- **Technical Notes:** Apply the following corrections to each AIS file:

  | AIS File | Change |
  |---|---|
  | AIS-06 Transportation | `OrderApproved` → subscribe to `CEOApprovalGranted` |
  | AIS-07 Manufacturing | `PlannerApproved` → `ProductionRequested`; `ForecastUpdated` → `DemandForecastGenerated` |
  | AIS-10 Risk | `FinancialThresholdExceeded` → `BudgetExceeded` |
  | AIS-11 Pricing | `DemandForecastUpdated` → `DemandForecastGenerated`; `FinanceRecommendationPublished` → `FinancialRecommendationReady` |
  | AIS-15 Planner | `ForecastCompleted` → `DemandForecastGenerated`; `InventoryUpdated` subscription confirmed |
  | AIS-03 Inventory | `ShipmentReceived` → `ShipmentDelivered` |
  | AIS-05 Supplier | `PurchaseOrderRequested` (output) → `PurchaseOrderCreated` |

- **Acceptance Criteria:** All AIS files use only event names from the canonical glossary. Cross-reference table in Part 0 of enterprise_audit_and_epics.md updated to reflect corrections.
- **Definition of Done:** Reviewed · All AIS files updated · Glossary is the only source of truth
- **Story Points:** 3 | **Priority:** P0

---

## US-64 · Implement Missing Event Publishers

- **Epic:** EP-14
- **Sprint Target:** Sprint 5–8 (phased with agent implementation)
- **Resolves:** AUD-48, AUD-49, AUD-50, AUD-56
- **Description:** As a platform engineer, I want the four events with no publisher to be explicitly assigned to a publishing agent and implemented, so that all event subscriptions in the system are reachable.
- **Technical Notes:**
  - `SupplierUpdated` → Published by ADS-05 (Supplier Agent) in `update_supplier_profile()` tool when supplier rating, blacklist status, or contract terms change
  - `InspectionRequested` → Published by ADS-07 (Manufacturing Agent) at the end of `ManufacturingCompleted` processing, triggering QA Agent automatically
  - `ProductReturned` → Published by ADS-08 (Customer Service Agent) when a customer initiates a return via `POST /support/returns`
  - `SupplierPerformanceUpdated` → Published by ADS-05 after delivery confirmation AND by ADS-14 after QA inspection scoring — both agents set `source_agent` appropriately in payload
- **Acceptance Criteria:** All 4 events have a defined, implemented publisher. Integration tests verify the full chain: publisher event → subscriber agent triggered.
- **Definition of Done:** Reviewed · Integration tests pass for all 4 event chains
- **Story Points:** 5 | **Priority:** P0

---

## US-65 · Celery Scheduled Event Publishers

- **Epic:** EP-14
- **Sprint Target:** Sprint 5
- **Resolves:** AUD-51, AUD-52
- **Description:** As a platform engineer, I want Celery Beat scheduled tasks that publish `ContractExpiring` and `PromotionScheduled` events on a schedule so that Procurement Strategy and Demand Forecast agents are triggered by time-based business events.
- **Technical Notes:**
  - `ContractExpiryChecker` task: runs daily at 00:00 UTC. Queries `contracts` WHERE `status = 'active'` AND `end_date <= NOW() + INTERVAL '30 days'`. Publishes `ContractExpiring` event per contract. Updates `contracts.status = 'expiring_soon'`.
  - `PromotionActivationChecker` task: runs every hour. Queries `promotions` WHERE `status = 'scheduled'` AND `starts_at <= NOW()`. Publishes `PromotionScheduled` (1 hour before) and `PromotionStarted` (at start). Updates `promotions.status = 'active'`.
  - `PromotionEndChecker` task: runs every hour. Queries active promotions WHERE `ends_at <= NOW()`. Publishes `PromotionEnded`. Updates status to `'completed'`.
  - Configure in Celery Beat schedule (`celeryconfig.py`). Use `celery_unique_task` decorator to prevent duplicate runs.
- **Acceptance Criteria:** ContractExpiry task fires daily. Near-expiry contracts trigger event. Promotion lifecycle events fire at correct times. All tasks are idempotent.
- **Definition of Done:** Reviewed · Unit tested with mock datetime · Integration tested
- **Story Points:** 5 | **Priority:** P0

---

## US-66 · Runtime Event Contract Validator

- **Epic:** EP-14
- **Sprint Target:** Sprint 5
- **Description:** As a platform engineer, I want a runtime event contract validator that rejects any event with an unregistered `event_type` at publish time so that event naming drift is caught immediately rather than silently failing.
- **Technical Notes:**
  - Create `EventRegistry` class in `backend/app/events/registry.py`
  - Load canonical event names from a Python constant (generated from `CANONICAL_Event_Glossary.md` at build time)
  - Integrate into `EventPublisher.publish()` method: validate `event_type` against registry before sending to RabbitMQ
  - Raise `UnregisteredEventTypeError` (subclass of `ValueError`) with a message showing the unregistered name and suggesting the closest match
  - Add registry check to CI: `pytest tests/test_event_registry.py` validates that all events referenced in agent code exist in the registry
  - Include `event_version` validation: reject events whose version is not in `{known_versions}` for that event type
- **Acceptance Criteria:** Publishing an unregistered event raises `UnregisteredEventTypeError`. CI test catches new event names not in registry. Version mismatch is caught.
- **Definition of Done:** Reviewed · Unit tested · CI check confirmed
- **Story Points:** 3 | **Priority:** P0

---

# PART C — Granular Per-Agent Implementation Stories

> Each of the 18 agents receives 5 dedicated user stories covering: (1) LangGraph Node, (2) Event Handlers, (3) Business Logic & Tools, (4) Unit Tests, (5) Integration Test.
> Stories are grouped into per-agent Epics (EP-15 to EP-32).
> All agents depend on EP-05 (LangGraph Engine) and EP-14 (Event Compliance) being complete.
> For the 5-story breakdown per agent:
> - **Story A:** LangGraph Node Setup — class, state schema, checkpoint, routing edges
> - **Story B:** Event Subscription Handlers — consumer registration, idempotency, DLQ binding
> - **Story C:** Business Logic & Tool Integration — core algorithm, LLM calls, DB writes, event publishes
> - **Story D:** Unit Tests — all decision branches, edge cases, failure injection
> - **Story E:** Integration Test — full end-to-end with real infrastructure via testcontainers

---

## EP-15 · AIS-01 Order Management Agent — Full Implementation

**Sprint Target:** Sprint 8 | **Priority:** P1 | **Depends on:** EP-05, EP-14, US-59–62

---

### US-67 · AIS-01 | LangGraph Node: OrderManagementNode

- **Description:** As a platform engineer, I want the `OrderManagementNode` LangGraph node class created with correct state read/write bindings, checkpoint configuration, and routing edges so that it integrates cleanly into the supply chain graph.
- **Technical Notes:**
  - File: `backend/app/agents/order_management/node.py`
  - Class: `OrderManagementNode(BaseAgentNode)`
  - Reads from state: `workflow_id`, `correlation_id`, `customer`, `order`
  - Writes to state: `order` (validated), `errors`, `event_history`
  - Checkpoint: after successful validation (before publishing `OrderCreated`)
  - Routing: `order_valid` → next node; `order_invalid` → `ErrorNode`; `duplicate` → `END`
  - Node must implement `__call__(state: SupplyChainState) -> SupplyChainState`
- **Acceptance Criteria:** Node registers in LangGraph graph without errors. State transitions correctly for valid/invalid/duplicate orders. Checkpoint persisted after validation.
- **Story Points:** 3 | **Priority:** P1

---

### US-68 · AIS-01 | Event Handlers: CustomerOrder Events

- **Description:** As a platform engineer, I want RabbitMQ consumer handlers for `CustomerOrderReceived`, `CustomerOrderUpdated`, and `CustomerOrderCancelled` registered and wired to the LangGraph graph trigger so that external orders flow into the system.
- **Technical Notes:**
  - File: `backend/app/agents/order_management/handlers.py`
  - Consumer for `CustomerOrderReceived` → validates payload schema (Pydantic) → triggers `OrderManagementNode`
  - Consumer for `CustomerOrderUpdated` → loads existing order from DB → applies delta → re-validates
  - Consumer for `CustomerOrderCancelled` → loads order → publishes `OrderCancelled` event → releases any inventory
  - Idempotency: check `events` table for `event_id` before processing. Return 200 if duplicate.
  - DLQ: after 3 retries with exponential backoff, route to `order_management.dlq`
- **Acceptance Criteria:** All 3 event types consumed correctly. Duplicate events are no-ops. Failed events after max retries land in DLQ.
- **Story Points:** 3 | **Priority:** P1

---

### US-69 · AIS-01 | Business Logic: Validation, Prioritization & Order Persistence

- **Description:** As a supply chain system, I want the Order Management Agent to validate customer orders against all business rules, assign priority, and persist to the database before publishing `OrderCreated`.
- **Technical Notes:**
  - Validation rules (all deterministic, no LLM):
    1. Customer exists and `is_active = TRUE`
    2. All `product_id` values exist and `active = TRUE`
    3. All quantities > 0
    4. No duplicate `order_id` in last 24h for same customer + items (idempotency)
    5. `total_amount` matches sum of `quantity × unit_price`
  - Priority assignment: `customer_tier = 'enterprise'` → `critical`; `'premium'` → `high`; `'standard'` → `standard`
  - DB writes: INSERT to `orders` + `order_items`. Write `audit_logs` with full before/after payload.
  - LLM use: NONE in this agent (all logic is deterministic per AIS-01)
  - Published events: `OrderCreated` (on success), `OrderRejected` (on validation failure)
  - Each rejection reason must be included in the `payload.reason` field
- **Acceptance Criteria:** All 5 validation rules enforced. Correct priority assigned. `orders` + `order_items` rows created. `OrderCreated` event published with correct schema. Rejected orders produce `OrderRejected` with reason.
- **Story Points:** 5 | **Priority:** P1

---

### US-70 · AIS-01 | Unit Tests: Order Management Agent

- **Description:** As a QA engineer, I want comprehensive unit tests for the Order Management Agent covering all validation branches and edge cases.
- **Technical Notes:**
  - Framework: pytest + pytest-asyncio + unittest.mock
  - Test cases:
    1. Valid standard order → `OrderCreated` published
    2. Valid enterprise order → `critical` priority assigned
    3. Invalid customer (not found) → `OrderRejected` with reason `customer_not_found`
    4. Inactive product → `OrderRejected` with reason `product_unavailable`
    5. Zero quantity → `OrderRejected` with reason `invalid_quantity`
    6. Duplicate order (same event_id) → no-op, 200 returned
    7. Amount mismatch → `OrderRejected`
    8. DB write failure → error caught, `OrderRejected` published, audit log written
    9. RabbitMQ publish failure → retry logic triggered
    10. `OrderCancelled` for non-existent order → graceful error
  - Mock: DB session, RabbitMQ publisher, Redis
- **Acceptance Criteria:** All 10 test cases pass. Coverage ≥ 90% for business logic module.
- **Story Points:** 5 | **Priority:** P1

---

### US-71 · AIS-01 | Integration Test: Order Submission to OrderCreated

- **Description:** As a QA engineer, I want an integration test that submits a real order through the API and verifies the complete AIS-01 lifecycle: HTTP request → RabbitMQ event → DB record → `OrderCreated` event published.
- **Technical Notes:**
  - Infrastructure: testcontainers (PostgreSQL, Redis, RabbitMQ)
  - Steps:
    1. POST to `POST /orders` with valid payload
    2. Assert 201 response with `order_id`
    3. Assert `orders` row in DB with correct status `'pending'` → `'validated'`
    4. Assert `order_items` rows exist
    5. Assert `events` table contains `OrderCreated` event with correct `correlation_id`
    6. Assert `audit_logs` entry created with agent `ADS-01`
  - Test invalid order: Assert 400 response + `OrderRejected` event in `events` table
- **Acceptance Criteria:** Full lifecycle verified with real infrastructure. Invalid order path verified.
- **Story Points:** 5 | **Priority:** P1

---

## EP-16 · AIS-02 Demand Forecast Agent — Full Implementation

**Sprint Target:** Sprint 11 | **Priority:** P1 | **Depends on:** EP-15, US-59–62

---

### US-72 · AIS-02 | LangGraph Node: DemandForecastNode

- **Description:** As a platform engineer, I want the `DemandForecastNode` created with state bindings that read order history from the `orders` table and promotion data from `promotions`, then write the forecast result to shared state.
- **Technical Notes:**
  - Reads: `workflow_id`, `order` context, `correlation_id`
  - Writes: `forecast` (DemandForecastResult TypedDict: product_id, forecast_qty, confidence, period_start, period_end, lower_bound, upper_bound, model_used, is_anomaly)
  - Checkpoint: after forecast is written to `demand_forecasts` table
  - Routing: `forecast_complete` → next; `data_insufficient` → `FallbackForecastNode`; `anomaly_detected` → `RiskNode` (parallel trigger)
- **Acceptance Criteria:** Node integrates into graph. Forecast written to state. Anomaly triggers parallel risk evaluation.
- **Story Points:** 3 | **Priority:** P1

---

### US-73 · AIS-02 | Event Handlers: OrderCreated & PromotionScheduled

- **Description:** As a platform engineer, I want consumer handlers for `OrderCreated` and `PromotionScheduled` that trigger forecast recalculation when relevant inputs change.
- **Technical Notes:**
  - `OrderCreated` handler: accumulate orders; if rolling 7-day order count for a product changes by >15% → trigger `DemandForecastNode`
  - `PromotionScheduled` handler: immediately trigger `DemandForecastNode` for all promoted products
  - `InventoryUpdated` handler: optional re-forecast trigger if stock level falls below safety stock
  - Rate-limiting: debounce `OrderCreated` triggers — max 1 forecast recalc per product per 5 minutes using Redis TTL key
- **Acceptance Criteria:** Handlers registered. Debounce working. Promotion triggers immediate recalculation.
- **Story Points:** 3 | **Priority:** P1

---

### US-74 · AIS-02 | Business Logic: Statistical Forecast Engine

- **Description:** As a supply chain system, I want the Demand Forecast Agent to run a Holt-Winters statistical forecast model on historical order data and detect demand anomalies, publishing `DemandForecastGenerated` with full confidence intervals.
- **Technical Notes:**
  - Model: `statsmodels.tsa.holtwinters.ExponentialSmoothing` (no LLM for calculation)
  - Minimum history: 30 days of order data. Fallback: 90-day average if < 30 days.
  - Promotion adjustment: multiply forecast by `1 + (discount_percent / 100) * elasticity_factor` (elasticity_factor = 0.5 by default, configurable)
  - Anomaly detection: if `forecast_qty > 2 × 12-month_average` → set `is_anomaly = True`, publish `DemandSpikeDetected`
  - LLM use: ONLY for anomaly explanation text in `anomaly_description` field
  - DB writes: INSERT to `demand_forecasts`. One row per product per period.
  - Published events: `DemandForecastGenerated` (always), `DemandSpikeDetected` (conditional), `DemandDropDetected` (if forecast < 0.5 × average)
- **Acceptance Criteria:** Forecast generated for all active products. MAPE calculated and stored. Anomaly correctly detected from test data with >2× spike. LLM only called for anomaly explanation.
- **Story Points:** 8 | **Priority:** P1

---

### US-75 · AIS-02 | Unit Tests: Demand Forecast Agent

- **Description:** As a QA engineer, I want unit tests for the Demand Forecast Agent covering all model branches.
- **Technical Notes:** Test cases:
  1. Normal history → valid forecast with confidence interval
  2. < 30 days history → fallback average used, logged
  3. Active promotion → forecast adjusted upward
  4. Demand spike (>2× average) → `DemandSpikeDetected` published + `is_anomaly = True`
  5. Demand drop (<0.5× average) → `DemandDropDetected` published
  6. Zero order history → graceful handling, fallback
  7. DB write failure → error logged, retry
  8. LLM timeout for anomaly explanation → continue without explanation (non-blocking)
- **Acceptance Criteria:** All 8 cases pass. Coverage ≥ 85%.
- **Story Points:** 5 | **Priority:** P1

---

### US-76 · AIS-02 | Integration Test: Forecast Generation Pipeline

- **Description:** As a QA engineer, I want an integration test that seeds order history, triggers a forecast, and verifies the full event chain from `OrderCreated` → `DemandForecastGenerated` → `demand_forecasts` DB row.
- **Technical Notes:** Seed 60 days of `orders` data. Trigger `OrderCreated` event. Assert `demand_forecasts` row created. Assert `DemandForecastGenerated` event published. Assert `events` table contains event with correct payload schema. Verify promotion adjustment by seeding an active promotion and re-running.
- **Acceptance Criteria:** Full pipeline verified. Promotion adjustment confirmed by comparing forecast with/without promotion.
- **Story Points:** 5 | **Priority:** P1

---

## EP-17 · AIS-03 Inventory Management Agent — Full Implementation

**Sprint Target:** Sprint 8 | **Priority:** P1 | **Depends on:** EP-15

---

### US-77 · AIS-03 | LangGraph Node: InventoryAgentNode

- **Description:** As a platform engineer, I want the `InventoryAgentNode` created with atomic stock reservation logic integrated into LangGraph state management.
- **Technical Notes:**
  - Reads: `order`, `workflow_id`
  - Writes: `inventory` (allocation result), `events`
  - Critical: stock reservation must be atomic — use `SELECT ... FOR UPDATE` with a PostgreSQL advisory lock per `(product_id, warehouse_id)` to prevent race conditions
  - Routing: `allocated` → `WarehouseNode`; `partial_fill` → `SupplierNode` + `WarehouseNode` (parallel); `out_of_stock` → `SupplierNode`; `safety_stock_breach` → `RiskNode` + `CEONode`
  - Checkpoint: after successful allocation
- **Acceptance Criteria:** Concurrent allocations do not double-book stock. Routing edges work correctly. `inventory.reserved_qty` updated atomically.
- **Story Points:** 5 | **Priority:** P1

---

### US-78 · AIS-03 | Event Handlers: Inventory Event Bus

- **Description:** As a platform engineer, I want all 5 Inventory Agent event subscriptions handled correctly: `OrderCreated`, `OrderCancelled`, `ShipmentDelivered`, `ManufacturingCompleted`, `InventoryAdjusted`.
- **Technical Notes:**
  - `OrderCreated` → attempt allocation for all line items
  - `OrderCancelled` → release all reserved quantities (`reserved_qty -= allocated_qty`)
  - `ShipmentDelivered` → increment `available_qty` (goods received at warehouse)
  - `ManufacturingCompleted` → increment `available_qty` for manufactured product
  - `InventoryAdjusted` → apply physical count correction (can reduce or increase)
  - All handlers: idempotency check on `event_id`, write to `audit_logs`
- **Acceptance Criteria:** All 5 handlers tested with real events. Stock levels never go negative (constraint enforced).
- **Story Points:** 3 | **Priority:** P1

---

### US-79 · AIS-03 | Business Logic: Allocation, Safety Stock & Reorder Trigger

- **Description:** As a supply chain system, I want the Inventory Agent to allocate stock using warehouse proximity scoring, enforce safety stock policy, and automatically trigger reorder when stock falls below the reorder point.
- **Technical Notes:**
  - Warehouse selection: score = `(proximity_score × 0.5) + (utilization_inverse × 0.3) + (zone_match × 0.2)`. Select warehouse with highest score that has sufficient stock.
  - Allocation: `UPDATE inventory SET reserved_qty = reserved_qty + :qty WHERE product_id = :pid AND warehouse_id = :wid AND (available_qty - reserved_qty) >= :qty`
  - Safety stock check: if `available_qty - reserved_qty <= safety_stock` after allocation → publish `InventoryLow`
  - Reorder trigger: if `available_qty <= reorder_point` → publish `ReorderRequested` with `reorder_qty`
  - Out of stock: if no warehouse has sufficient stock → publish `InventoryOutOfStock`
  - LLM use: NONE (all deterministic)
  - Published: `InventoryAllocated`, `InventoryLow`, `ReorderRequested`, `InventoryOutOfStock`
- **Acceptance Criteria:** Allocation selects correct warehouse. Safety stock never violated without `InventoryLow` event. Reorder triggered at correct threshold.
- **Story Points:** 8 | **Priority:** P1

---

### US-80 · AIS-03 | Unit Tests: Inventory Management Agent

- **Description:** Unit tests for all inventory allocation scenarios.
- **Technical Notes:** Test cases:
  1. Sufficient stock in closest warehouse → `InventoryAllocated` published
  2. Stock in 2nd warehouse only → correct warehouse selected
  3. Stock exactly at safety stock after allocation → `InventoryLow` published
  4. Stock at reorder point → `ReorderRequested` published with correct qty
  5. Zero stock everywhere → `InventoryOutOfStock` published
  6. Concurrent allocation race condition → lock prevents double-booking
  7. `OrderCancelled` → `reserved_qty` correctly released
  8. `ShipmentDelivered` → `available_qty` incremented correctly
  9. DB constraint violation (qty negative) → error caught + DLQ
- **Acceptance Criteria:** All 9 cases pass. Race condition test verified with concurrent threads.
- **Story Points:** 5 | **Priority:** P1

---

### US-81 · AIS-03 | Integration Test: Inventory Allocation End-to-End

- **Description:** Full integration test from `OrderCreated` → `InventoryAllocated` → DB verification.
- **Technical Notes:** Seed inventory. Publish `OrderCreated`. Assert `inventory.reserved_qty` incremented. Assert `InventoryAllocated` event published. Test out-of-stock path. Test reorder path. Verify audit log entry.
- **Acceptance Criteria:** All allocation paths verified with real DB.
- **Story Points:** 5 | **Priority:** P1

---

## EP-18 · AIS-04 Warehouse Agent — Full Implementation

**Sprint Target:** Sprint 8 | **Priority:** P1 | **Depends on:** EP-17

---

### US-82 · AIS-04 | LangGraph Node: WarehouseAgent

- **Description:** LangGraph node for warehouse task orchestration (pick, pack, ship-ready).
- **Technical Notes:** Reads: `inventory` (allocated result), `order`. Writes: `warehouse` (pick/pack status). Routing: `shipment_ready` → `TransportationNode`; `warehouse_exception` → `CEONode` + alert. Checkpoint after `ShipmentReady` event.
- **Story Points:** 3 | **Priority:** P1

---

### US-83 · AIS-04 | Event Handlers: Warehouse Operations Events

- **Description:** Handlers for `OrderCreated`, `InventoryAllocated`, `InventoryReceived`, `ShipmentScheduled`.
- **Technical Notes:** `InventoryAllocated` → trigger pick task. `ShipmentScheduled` → trigger pack task. `InventoryReceived` → update warehouse load, publish `WarehouseCapacityUpdated`. All operations write to `audit_logs`.
- **Story Points:** 3 | **Priority:** P1

---

### US-84 · AIS-04 | Business Logic: Pick, Pack, Load Balancing

- **Description:** As a supply chain system, I want the Warehouse Agent to assign the optimal warehouse zone for picking, calculate estimated pick/pack time, and publish `ShipmentReady` when packing is complete.
- **Technical Notes:**
  - Pick assignment: select bin location with shortest walking distance (mock map grid for MVP)
  - Pack: verify item count matches order. Flag discrepancies as `WarehouseExceptionRaised`.
  - Capacity check: after receiving goods, if `current_load / capacity_units > 0.95` → publish `WarehouseExceptionRaised`
  - LLM use: NONE
  - DB writes: UPDATE `warehouses.current_load`, INSERT `shipments` (initial record), write `audit_logs`
  - Published: `PickingCompleted`, `PackingCompleted`, `ShipmentReady`, `WarehouseCapacityUpdated`, `WarehouseExceptionRaised`
- **Acceptance Criteria:** Correct events in sequence. Capacity threshold triggers exception. Pack discrepancy caught.
- **Story Points:** 5 | **Priority:** P1

---

### US-85 · AIS-04 | Unit Tests: Warehouse Agent

- **Description:** Unit tests for picking, packing, capacity, and exception scenarios.
- **Technical Notes:** Test cases: normal pick+pack flow, capacity threshold breach, item count mismatch, goods received → capacity updated, warehouse at full capacity → exception raised.
- **Story Points:** 5 | **Priority:** P1

---

### US-86 · AIS-04 | Integration Test: Warehouse Pick-Pack-Ready Pipeline

- **Description:** Integration test: `InventoryAllocated` → `PickingCompleted` → `PackingCompleted` → `ShipmentReady`, all verified in DB and event store.
- **Story Points:** 5 | **Priority:** P1

---

## EP-19 · AIS-05 Supplier Agent — Full Implementation

**Sprint Target:** Sprint 8 | **Priority:** P1 | **Depends on:** EP-17, US-59–62

---

### US-87 · AIS-05 | LangGraph Node: SupplierAgent

- **Description:** LangGraph node for supplier selection and PO creation.
- **Technical Notes:** Reads: `inventory` (shortage details), `order`. Writes: `supplier` (selected supplier, PO details). Checkpoint after `PurchaseOrderCreated`. Routing: `po_created` → `FinanceNode`; `no_supplier` → `ManufacturingNode`; `all_blacklisted` → `CEONode`.
- **Story Points:** 3 | **Priority:** P1

---

### US-88 · AIS-05 | Event Handlers: Procurement Trigger Events

- **Description:** Handlers for `InventoryLow`, `ReorderRequested`, `ProductionPlanned`.
- **Technical Notes:** All handlers extract `product_id` and `required_qty`, then trigger `SupplierAgent` node. `InventoryLow` handler checks if reorder already in progress (Redis key `reorder_in_progress:{product_id}`) to avoid duplicate POs. On completion, publish `SupplierUpdated` (AUD-48 fix) and `SupplierPerformanceUpdated` (AUD-56 fix) when delivery confirmed.
- **Story Points:** 3 | **Priority:** P1

---

### US-89 · AIS-05 | Business Logic: Supplier Scoring, PO Creation & Performance Update

- **Description:** As a supply chain system, I want the Supplier Agent to score all eligible suppliers, select the optimal one, create a purchase order, and publish `SupplierUpdated` after any supplier master data change.
- **Technical Notes:**
  - Eligibility filter: `status = 'active'`, has product in `supplier_products`, `minimum_order_qty <= required_qty`
  - Blacklist check: `status = 'blacklisted'` → NEVER selected (System Rule §6)
  - Scoring: `score = (reliability_score × 0.4) + ((1 / unit_cost) × 0.3 × weight) + ((1 / lead_time_days) × 0.2 × weight) + (quality_score × 0.1)`
  - Tie-breaking: prefer `is_preferred = TRUE` supplier
  - PO creation: INSERT to `purchase_orders` with `status = 'submitted'`
  - LLM use: recommendation explanation only (why this supplier was chosen over alternatives)
  - `SupplierUpdated` published when: blacklist status changes, rating changes by > 0.5, contract expires
  - `SupplierPerformanceUpdated` published when: delivery confirmed AND quality score recalculated
  - Published: `SupplierSelected`, `PurchaseOrderCreated`, `SupplierUnavailable` (if no eligible suppliers), `SupplierUpdated`, `SupplierPerformanceUpdated`
- **Acceptance Criteria:** Blacklisted suppliers never selected (tested with 100% blacklist). Scoring formula verified. PO row created. LLM explanation captured in audit.
- **Story Points:** 8 | **Priority:** P1

---

### US-90 · AIS-05 | Unit Tests: Supplier Agent

- **Description:** Unit tests for supplier selection scenarios.
- **Technical Notes:** Test cases:
  1. Multiple eligible suppliers → highest-score selected
  2. Blacklisted supplier → excluded from selection
  3. All blacklisted → `SupplierUnavailable` + route to manufacturing
  4. MOQ constraint → supplier with insufficient MOQ excluded
  5. Tie → preferred supplier wins
  6. Delivery confirmed → `SupplierPerformanceUpdated` published
  7. Supplier blacklisted → `SupplierUpdated` published
  8. PO DB write failure → retry x5, circuit breaker
- **Acceptance Criteria:** All 8 pass. Blacklist rule verified with multiple test cases.
- **Story Points:** 5 | **Priority:** P1

---

### US-91 · AIS-05 | Integration Test: Supplier Selection to PO Pipeline

- **Description:** Integration test: `ReorderRequested` → supplier scored → `PurchaseOrderCreated` → `purchase_orders` DB row verified.
- **Story Points:** 5 | **Priority:** P1

---

## EP-20 · AIS-06 Transportation Agent — Full Implementation

**Sprint Target:** Sprint 8 | **Priority:** P1 | **Depends on:** EP-18, US-59–62

---

### US-92 · AIS-06 | LangGraph Node: TransportationAgentNode

- **Description:** LangGraph node for carrier selection and shipment dispatch.
- **Technical Notes:** Reads: `order`, `inventory` (warehouse), `risk`. Writes: `shipment`. **Subscribe to `CEOApprovalGranted` not `OrderApproved` (AUD-47 fix)**. Checkpoint after `ShipmentDispatched`. Routing: `dispatched` → `CustomerServiceNode` + `SustainabilityNode` (parallel); `carrier_unavailable` → retry x3 then `CEONode`.
- **Story Points:** 3 | **Priority:** P1

---

### US-93 · AIS-06 | Event Handlers: Shipment Trigger Events

- **Description:** Handlers for `ShipmentReady`, `CEOApprovalGranted`, `InventoryAllocated`, `RiskDetected`.
- **Technical Notes:** `ShipmentReady` → initiate carrier selection. `CEOApprovalGranted` → resume shipment if previously paused awaiting approval. `RiskDetected` with shipment context → re-evaluate route. All handlers idempotent.
- **Story Points:** 3 | **Priority:** P1

---

### US-94 · AIS-06 | Business Logic: Carrier Selection, Route Optimization & ETA

- **Description:** As a supply chain system, I want the Transportation Agent to select the optimal carrier and route, calculate ETA, create a shipment record, and dispatch.
- **Technical Notes:**
  - Route query: SELECT from `transportation_routes` WHERE `origin_location = :origin` AND `destination = :dest` AND `is_active = TRUE`
  - Carrier filter: `carrier.status = 'active'`, mode supports required freight type, `carrier.reliability_score >= 70`
  - Scoring: time-critical orders → weight transit_days × 2; cost-critical → weight base_cost × 2
  - ETA calculation: `NOW() + INTERVAL ':transit_days days' + handling_time`
  - Shipment record: INSERT to `shipments` with `carrier_id` FK (AUD-45 fix), `carrier_tracking_id`, `eta`, `route_id`
  - LLM use: explain trade-off between fastest vs cheapest route
  - Published: `ShipmentCreated`, `ShipmentDispatched`, `ETAUpdated` (if ETA changes post-dispatch)
  - CO2 data: pass `transportation_routes.co2_per_tonne_km` to sustainability payload
- **Acceptance Criteria:** Correct route selected for time/cost priority. `shipments.carrier_id` populated. ETA calculated correctly. LLM trade-off explanation in audit.
- **Story Points:** 8 | **Priority:** P1

---

### US-95 · AIS-06 | Unit Tests: Transportation Agent

- **Description:** Unit tests for carrier selection and routing scenarios.
- **Technical Notes:** Test cases:
  1. Time-critical order → fastest route selected
  2. Cost-critical order → cheapest route selected
  3. No active carrier for mode → retry x3 → `CEONode` escalation
  4. Risk detected on route → alternative route selected
  5. Blacklisted carrier → excluded (same as supplier blacklist policy)
  6. ETA recalculation → `ETAUpdated` published
- **Story Points:** 5 | **Priority:** P1

---

### US-96 · AIS-06 | Integration Test: Shipment Dispatch End-to-End

- **Description:** Integration test: `ShipmentReady` → carrier selected → `ShipmentDispatched` → `shipments` row verified with `carrier_id`.
- **Story Points:** 5 | **Priority:** P1

---

## EP-21 · AIS-07 Manufacturing Agent — Full Implementation

**Sprint Target:** Sprint 16 | **Priority:** P2 | **Depends on:** EP-16 (Forecast)

---

### US-97 · AIS-07 | LangGraph Node: ManufacturingAgent

- **Description:** LangGraph node for production scheduling.
- **Technical Notes:** **Subscribe to `ProductionRequested` (not `PlannerApproved`) and `DemandForecastGenerated` (not `ForecastUpdated`) — AUD-47 and AUD-54 fix**. Writes: `manufacturing` state. Checkpoint after `ManufacturingStarted`. Routing: `started` → parallel `QualityNode`; `capacity_exceeded` → `PlannerNode` (replan); `paused` → `RiskNode`.
- **Story Points:** 3 | **Priority:** P2

---

### US-98 · AIS-07 | Event Handlers: Production Trigger Events

- **Description:** Handlers for `ProductionRequested`, `DemandForecastGenerated`, `InventoryAllocated`.
- **Technical Notes:** On `ManufacturingCompleted`, publish `InspectionRequested` (AUD-49 fix) to trigger QA Agent automatically. Handler validates that `manufacturing_orders.warehouse_id` is always set (AUD-20 fix).
- **Story Points:** 3 | **Priority:** P2

---

### US-99 · AIS-07 | Business Logic: Capacity Check, Schedule & Quality Trigger

- **Description:** As a supply chain system, I want the Manufacturing Agent to check factory capacity, schedule production, and automatically trigger QA inspection upon completion.
- **Technical Notes:**
  - Capacity check: query `manufacturing_orders` WHERE `status IN ('planned', 'in_progress')` for current load
  - Schedule: INSERT to `manufacturing_orders` with `warehouse_id` FK, `scheduled_start`, `scheduled_end`
  - Progress updates: UPDATE status through lifecycle: `planned` → `in_progress` → `completed`
  - On `completed`: publish `ManufacturingCompleted` AND `InspectionRequested` (AUD-49 fix)
  - LLM use: trade-off between short run (higher unit cost) vs bulk run (lower cost, longer time)
  - Published: `ManufacturingStarted`, `ManufacturingPaused`, `ManufacturingCompleted`, `ManufacturingDelayed`, `CapacityExceeded`, `InspectionRequested`
- **Acceptance Criteria:** `manufacturing_orders.warehouse_id` always populated. `InspectionRequested` published after completion. Capacity breach triggers `CapacityExceeded`.
- **Story Points:** 5 | **Priority:** P2

---

### US-100 · AIS-07 | Unit Tests: Manufacturing Agent

- **Description:** Unit tests for production scheduling, capacity, and QA trigger.
- **Technical Notes:** Test cases: capacity available, capacity at limit → `CapacityExceeded`, completion triggers `InspectionRequested`, delay detected → `ManufacturingDelayed`, `DemandForecastGenerated` triggers re-schedule assessment.
- **Story Points:** 5 | **Priority:** P2

---

### US-101 · AIS-07 | Integration Test: Production to QA Pipeline

- **Description:** Integration test: `ProductionRequested` → `ManufacturingStarted` → `ManufacturingCompleted` → `InspectionRequested` → QA Agent triggered.
- **Story Points:** 5 | **Priority:** P2

---

## EP-22 · AIS-08 Customer Service Agent — Full Implementation

**Sprint Target:** Sprint 16 | **Priority:** P2 | **Depends on:** EP-15, EP-20

---

### US-102 · AIS-08 | LangGraph Node: CustomerServiceNode

- **Description:** LangGraph node for customer notification and escalation.
- **Technical Notes:** Reads: `order`, `shipment`, `customer`. Writes: `customer_service` state. `ProductReturned` publisher implemented here (AUD-50 fix). Routing: `notified` → `END`; `escalated` → `CEONode`.
- **Story Points:** 3 | **Priority:** P2

---

### US-103 · AIS-08 | Event Handlers: Customer Lifecycle Events

- **Description:** Handlers for `OrderCreated`, `ShipmentDispatched`, `ShipmentDelivered`, `DeliveryDelayed`.
- **Technical Notes:** Each handler: load customer and order from DB → compose notification → publish `CustomerNotified`. Return request handler: validate return eligibility → INSERT `support_tickets` → publish `ProductReturned` (AUD-50 fix).
- **Story Points:** 3 | **Priority:** P2

---

### US-104 · AIS-08 | Business Logic: Notifications, Tickets & Return Processing

- **Description:** As a supply chain system, I want the Customer Service Agent to proactively notify customers at every milestone, manage support tickets, and process returns triggering QA.
- **Technical Notes:**
  - Notification triggers: `OrderCreated` (confirmation), `ShipmentDispatched` (dispatch + tracking link), `ShipmentDelivered` (delivery confirmation), `DeliveryDelayed` (delay alert + new ETA)
  - Notification content: LLM generates personalized message using customer name, order details, ETA
  - Support ticket: INSERT to `support_tickets` with SLA deadline based on category (delivery_delay = 4h, billing_issue = 24h, other = 48h)
  - Return processing: validate return window (within 30 days of delivery) → INSERT ticket with `category = 'return_request'` → publish `ProductReturned` for QA Agent
  - Escalation: ticket not resolved within SLA → publish `TicketEscalated` → route to CEO
  - Published: `CustomerNotified`, `TicketOpened`, `TicketEscalated`, `ProductReturned`
- **Acceptance Criteria:** Notification sent at each milestone. SLA deadline set correctly. Return triggers `ProductReturned`. Escalation fires on SLA breach.
- **Story Points:** 8 | **Priority:** P2

---

### US-105 · AIS-08 | Unit Tests: Customer Service Agent

- **Description:** Test cases: notification for each milestone, return within window, return outside window (rejected), SLA breach escalation, LLM failure (graceful degradation to template).
- **Story Points:** 5 | **Priority:** P2

---

### US-106 · AIS-08 | Integration Test: Customer Notification Pipeline

- **Description:** Integration test: `ShipmentDelivered` → `CustomerNotified` event → `support_tickets` DB row for return request → `ProductReturned` event published.
- **Story Points:** 5 | **Priority:** P2

---

## EP-23 · AIS-09 Finance Agent — Full Implementation

**Sprint Target:** Sprint 11 | **Priority:** P1 | **Depends on:** EP-19, EP-20

---

### US-107 · AIS-09 | LangGraph Node: FinanceAgentNode

- **Description:** LangGraph node for financial evaluation and approval.
- **Technical Notes:** Reads: `order`, `supplier`, `shipment`. Writes: `finance`. Checkpoint after decision. Routing: `approved` → next; `budget_exceeded` → `CEONode`; `high_cost_flag` → `NegotiationNode`.
- **Story Points:** 3 | **Priority:** P1

---

### US-108 · AIS-09 | Event Handlers: Financial Trigger Events

- **Description:** Handlers for `OrderCreated`, `InventoryAllocated`, `PurchaseOrderCreated`, `ManufacturingCompleted`, `ShipmentDispatched`.
- **Technical Notes:** Each handler: extract cost components → calculate total → compare to budget. On budget breach: publish `BudgetExceeded` (NOT `FinancialThresholdExceeded` — AUD-53 fix). Publish `FinancialRecommendationReady` for Negotiation Agent.
- **Story Points:** 3 | **Priority:** P1

---

### US-109 · AIS-09 | Business Logic: Cost Calculation, Budget Check & Ledger

- **Description:** As a supply chain system, I want the Finance Agent to calculate total workflow cost, compare to budget, write a ledger entry, and publish approval or escalation.
- **Technical Notes:**
  - Cost calculation: `total_cost = procurement_cost + shipping_cost + handling_cost + manufacturing_cost`
  - Budget check: query `finance_transactions` for `period_start` → `NOW()` to get period spend. Add `total_cost`. If > budget_limit → `BudgetExceeded`.
  - Approval thresholds: < $10k → auto-approve; $10k–$100k → Finance approval; > $100k → CEO approval required
  - DB writes: INSERT to `finance_transactions` with `approved_by_agent = 'ADS-09'`
  - LLM use: comparative cost analysis narrative (e.g., "This route is 12% cheaper than the 3-month average")
  - Published: `FinancialApprovalGranted`, `BudgetExceeded`, `CostOptimizationSuggested`, `FinancialRecommendationReady`
- **Acceptance Criteria:** Correct cost calculation. Threshold routing verified. `finance_transactions` row created. `BudgetExceeded` (not other name) published on breach.
- **Story Points:** 8 | **Priority:** P1

---

### US-110 · AIS-09 | Unit Tests: Finance Agent

- **Description:** Test cases: within budget approval, $10k threshold routing, $100k CEO routing, budget exceeded, period spend calculation, DB write failure retry.
- **Story Points:** 5 | **Priority:** P1

---

### US-111 · AIS-09 | Integration Test: Financial Approval Pipeline

- **Description:** Integration test: `PurchaseOrderCreated` → cost calculated → `FinancialApprovalGranted` → `finance_transactions` row verified.
- **Story Points:** 5 | **Priority:** P1

---

## EP-24 · AIS-10 Risk Management Agent — Full Implementation

**Sprint Target:** Sprint 11 | **Priority:** P1 | **Depends on:** EP-19, EP-20

---

### US-112 · AIS-10 | LangGraph Node: RiskManagementAgent

- **Description:** LangGraph node for risk evaluation. Subscribe to `BudgetExceeded` (not `FinancialThresholdExceeded` — AUD-53 fix) and `SupplierPerformanceUpdated` (AUD-56 fix).
- **Story Points:** 3 | **Priority:** P1

---

### US-113 · AIS-10 | Event Handlers: Risk Signal Events

- **Description:** Handlers for `InventoryLow`, `ShipmentDelayed`, `ManufacturingDelayed`, `SupplierPerformanceUpdated`, `BudgetExceeded`.
- **Technical Notes:** Each event contributes a risk signal with weight. `SupplierPerformanceUpdated` triggers supplier risk score recalculation. `BudgetExceeded` triggers financial risk assessment.
- **Story Points:** 3 | **Priority:** P1

---

### US-114 · AIS-10 | Business Logic: Multi-Signal Risk Scoring & Mitigation

- **Description:** As a supply chain system, I want the Risk Agent to aggregate multiple risk signals into a composite score, classify the risk, write a risk record, and recommend mitigation.
- **Technical Notes:**
  - Signals and weights: supplier_reliability (0.25), inventory_level (0.20), shipment_delay (0.20), weather_api (0.15), geopolitical_index (0.10), financial_health (0.10)
  - Score: `risk_score = Σ(signal_value × weight)` scaled 0–100
  - Classification: 0–30 Low, 31–60 Medium, 61–80 High, 81–100 Critical
  - Thresholds: score > 70 → `RiskDetected`; score > 90 → `ExecutiveEscalation`
  - External API failure: fallback to historical average for that signal (logged as degraded)
  - LLM use: mitigation recommendation narrative
  - DB writes: INSERT to `risk_assessments`
  - Published: `RiskDetected`, `HighRiskAlert`, `MitigationRecommended`, `ExecutiveEscalation`, `RiskAssessmentCompleted`
- **Acceptance Criteria:** Score correctly computed from all signals. Threshold events published. API failure gracefully degraded. `risk_assessments` row created.
- **Story Points:** 8 | **Priority:** P1

---

### US-115 · AIS-10 | Unit Tests: Risk Management Agent

- **Description:** Test cases: all-low-signals → no alert, single spike → correct score, score=71 → `RiskDetected`, score=91 → `ExecutiveEscalation`, external API timeout → fallback score used, all APIs fail → max fallback score with critical alert.
- **Story Points:** 5 | **Priority:** P1

---

### US-116 · AIS-10 | Integration Test: Risk Assessment Pipeline

- **Description:** Integration test: `ShipmentDelayed` → risk scored → `RiskDetected` published → `risk_assessments` row verified.
- **Story Points:** 5 | **Priority:** P1

---

## EP-25 · AIS-11 Pricing Agent — Full Implementation

**Sprint Target:** Sprint 16 | **Priority:** P2 | **Depends on:** EP-16, EP-23, US-59–62

---

### US-117 · AIS-11 | LangGraph Node: PricingAgentNode

- **Description:** LangGraph node for dynamic pricing recommendations. Subscribe to `DemandForecastGenerated` (not `DemandForecastUpdated` — AUD-55 fix) and `FinancialRecommendationReady` (not `FinanceRecommendationPublished` — AUD-55 fix).
- **Story Points:** 3 | **Priority:** P2

---

### US-118 · AIS-11 | Event Handlers: Pricing Trigger Events

- **Description:** Handlers for `DemandForecastGenerated`, `InventoryUpdated`, `RiskAssessmentCompleted`, `FinancialRecommendationReady`.
- **Technical Notes:** All handlers trigger `PricingAgentNode`. Rate-limit: max 1 pricing recalculation per product per 15 minutes (Redis TTL key).
- **Story Points:** 3 | **Priority:** P2

---

### US-119 · AIS-11 | Business Logic: Dynamic Pricing Engine

- **Description:** As a supply chain system, I want the Pricing Agent to compute an optimal price recommendation using demand elasticity, inventory level, and risk data, publishing the recommendation for CEO approval if the change exceeds the autonomous threshold.
- **Technical Notes:**
  - Base price: `products.unit_price`
  - Demand adjustment: if `forecast_qty > 1.2 × avg` → price_multiplier = 1.1; if `forecast_qty < 0.8 × avg` → price_multiplier = 0.9
  - Inventory adjustment: if `available_qty < safety_stock × 2` → price_multiplier += 0.05
  - Risk adjustment: if `risk_score > 60` → price_multiplier += 0.03
  - Floor/ceiling: price cannot be < `base_price × 0.7` or > `base_price × 1.5`
  - Autonomous threshold: changes ≤ 10% auto-approved. Changes > 10% → `PriceChangeRequiresApproval`
  - DB writes: INSERT to `pricing_history` with `approved_price = NULL` until approval
  - LLM use: pricing strategy narrative and simulation summary
  - Published: `PricingRecommendationGenerated`, `PriceChangeRequiresApproval`, `PricingSimulationCompleted`
- **Acceptance Criteria:** Price within floor/ceiling. Threshold routing correct. `pricing_history` row created with `approved_price = NULL`.
- **Story Points:** 8 | **Priority:** P2

---

### US-120 · AIS-11 | Unit Tests: Pricing Agent

- **Description:** Test cases: demand spike → price up, demand drop → price down, floor constraint enforced, ceiling constraint enforced, ≤10% change auto-approved, >10% change routes to CEO, inventory low → additional premium, risk adjustment applied.
- **Story Points:** 5 | **Priority:** P2

---

### US-121 · AIS-11 | Integration Test: Pricing Recommendation Pipeline

- **Description:** Integration test: `DemandForecastGenerated` → price calculated → `PricingRecommendationGenerated` → `pricing_history` DB row verified.
- **Story Points:** 5 | **Priority:** P2

---

## EP-26 · AIS-12 Procurement Strategy Agent — Full Implementation

**Sprint Target:** Sprint 16 | **Priority:** P2 | **Depends on:** EP-19, US-59–62, US-65

---

### US-122 · AIS-12 | LangGraph Node: ProcurementStrategyNode

- **Description:** LangGraph node for long-term sourcing strategy. Reads from `purchase_history` view (AUD-44 fix), `contracts` table (AUD-43 fix).
- **Story Points:** 3 | **Priority:** P2

---

### US-123 · AIS-12 | Event Handlers: Procurement Strategy Triggers

- **Description:** Handlers for `DemandForecastGenerated`, `InventoryLow`, `SupplierPerformanceUpdated`, `RiskDetected`, `ContractExpiring` (published by Celery — AUD-51 fix).
- **Technical Notes:** `ContractExpiring` → immediately evaluate replacement supplier strategy. `SupplierPerformanceUpdated` → recalculate supplier concentration index.
- **Story Points:** 3 | **Priority:** P2

---

### US-124 · AIS-12 | Business Logic: Strategy Generation, Concentration Risk & Contract Management

- **Description:** As a supply chain system, I want the Procurement Strategy Agent to analyze the supplier portfolio, detect concentration risk, and recommend diversification or contract renewal.
- **Technical Notes:**
  - Concentration index: for each product, if 1 supplier provides > 60% of volume → `SupplierDiversificationRecommended`
  - Supplier performance trend: query `purchase_history` last 12 months. If avg reliability dropping → flag
  - Contract renewal: query `contracts` WHERE `status = 'expiring_soon'` → recommend renewal or alternative
  - Strategic supplier selection: LLM evaluates trade-offs between cost, reliability, ESG score, geopolitical risk
  - DB reads: `contracts`, `contract_products`, `purchase_history` view, `suppliers`, `risk_assessments`
  - LLM use: strategy narrative and supplier comparison
  - Published: `ProcurementStrategyGenerated`, `SupplierDiversificationRecommended`, `StrategicSupplierSelected`
- **Acceptance Criteria:** Concentration risk detected at >60% threshold. Contract expiry handled. Strategy documented with rationale.
- **Story Points:** 8 | **Priority:** P2

---

### US-125 · AIS-12 | Unit Tests: Procurement Strategy Agent

- **Description:** Test cases: concentration >60% → diversification recommended, contract expiring → renewal strategy, all contracts healthy → no action, performance declining → alternative supplier flagged.
- **Story Points:** 5 | **Priority:** P2

---

### US-126 · AIS-12 | Integration Test: Procurement Strategy Pipeline

- **Description:** Integration test: `ContractExpiring` event → strategy generated → `ProcurementStrategyGenerated` event published → verified.
- **Story Points:** 5 | **Priority:** P2

---

## EP-27 · AIS-13 Sustainability Agent — Full Implementation

**Sprint Target:** Sprint 16 | **Priority:** P2 | **Depends on:** EP-20, US-59–62

---

### US-127 · AIS-13 | LangGraph Node: SustainabilityAgent

- **Description:** LangGraph node for ESG calculation. Subscribe to `SupplierUpdated` (now published by ADS-05 — AUD-48 fix).
- **Story Points:** 3 | **Priority:** P2

---

### US-128 · AIS-13 | Event Handlers: Sustainability Trigger Events

- **Description:** Handlers for `ShipmentDispatched`, `ShipmentDelivered`, `ManufacturingCompleted`, `SupplierUpdated`.
- **Technical Notes:** `SupplierUpdated` handler recalculates supplier ESG score. `ShipmentDispatched` triggers carbon calculation.
- **Story Points:** 3 | **Priority:** P2

---

### US-129 · AIS-13 | Business Logic: Carbon Calculation, ESG Scoring & Green Recommendations

- **Description:** As a supply chain system, I want the Sustainability Agent to calculate CO2 emissions per shipment, evaluate supplier ESG scores, and recommend greener alternatives when thresholds are exceeded.
- **Technical Notes:**
  - Carbon formula: `co2_kg = distance_km × weight_tonnes × co2_per_tonne_km` (from `transportation_routes.co2_per_tonne_km`)
  - Sustainability score: 0–100 based on: emission vs. industry benchmark (40%), freight mode efficiency (30%), supplier ESG score (30%)
  - Threshold: sustainability_score < 60 → generate green alternative recommendations
  - Green alternative: query routes with lower `co2_per_tonne_km` and compare cost premium
  - Supplier ESG: weighted score from: compliance_rating, certifications, renewable_energy_pct (mocked initially)
  - DB writes: INSERT to `sustainability_metrics` per shipment
  - LLM use: green alternative recommendation narrative
  - Published: `SustainabilityCalculated`, `CarbonThresholdExceeded` (if co2 > policy limit), `SustainableSupplierRecommended`, `ESGAlertRaised`
- **Acceptance Criteria:** CO2 calculated for each shipment. Score < 60 triggers recommendations. `sustainability_metrics` row created.
- **Story Points:** 8 | **Priority:** P2

---

### US-130 · AIS-13 | Unit Tests: Sustainability Agent

- **Description:** Test cases: normal shipment → score calculated, high-emission route → `CarbonThresholdExceeded`, low-ESG supplier → `SustainableSupplierRecommended`, missing route data → fallback emission factor, `SupplierUpdated` → ESG recalculated.
- **Story Points:** 5 | **Priority:** P2

---

### US-131 · AIS-13 | Integration Test: Sustainability Calculation Pipeline

- **Description:** Integration test: `ShipmentDispatched` → CO2 calculated → `SustainabilityCalculated` → `sustainability_metrics` row verified.
- **Story Points:** 5 | **Priority:** P2

---

## EP-28 · AIS-14 Quality Assurance Agent — Full Implementation

**Sprint Target:** Sprint 16 | **Priority:** P2 | **Depends on:** EP-21, US-59–62

---

### US-132 · AIS-14 | LangGraph Node: QualityAssuranceAgent

- **Description:** LangGraph node for quality inspection. Subscribe to `InspectionRequested` (now published by ADS-07 — AUD-49 fix), `SupplierUpdated` (now published by ADS-05 — AUD-48 fix), `ProductReturned` (now published by ADS-08 — AUD-50 fix).
- **Story Points:** 3 | **Priority:** P2

---

### US-133 · AIS-14 | Event Handlers: Quality Trigger Events

- **Description:** Handlers for `ManufacturingCompleted`, `InspectionRequested`, `ProductReturned`, `SupplierUpdated`.
- **Technical Notes:** `InspectionRequested` is the primary trigger. `ProductReturned` triggers root cause analysis. `SupplierUpdated` triggers supplier quality re-evaluation. All events write `audit_logs`.
- **Story Points:** 3 | **Priority:** P2

---

### US-134 · AIS-14 | Business Logic: Inspection, Root Cause & CAPA

- **Description:** As a supply chain system, I want the QA Agent to evaluate inspection metrics, perform root cause analysis on failures, recommend CAPA, and update supplier quality scores.
- **Technical Notes:**
  - Quality score: `100 - (defect_rate × 100)` capped 0–100
  - Threshold: score < 70 → `QualityIssueDetected`; score < 40 → CRITICAL, requires CEO approval
  - Root cause analysis: LLM analyzes defect pattern, material, supplier, and batch parameters
  - CAPA: LLM recommends corrective action (e.g., "Increase incoming inspection frequency for supplier X")
  - Supplier quality update: recalculate supplier quality score. If 3 consecutive low scores → flag for blacklisting
  - `ProductReturned` handling: link return to original batch, run mini root-cause analysis
  - DB writes: INSERT to `quality_inspections` with `manufacturing_order_id` FK and `supplier_id` FK (AUD-21 fix). Publish `SupplierPerformanceUpdated` (AUD-56 fix).
  - Published: `QualityInspectionCompleted`, `QualityIssueDetected`, `CorrectiveActionRequested`, `SupplierQualityUpdated`, `SupplierPerformanceUpdated`
- **Acceptance Criteria:** Score calculated correctly. AUD-21 resolved (FKs populated). CAPA generated for failures. Supplier quality updated. 3-strike blacklist flag triggered.
- **Story Points:** 8 | **Priority:** P2

---

### US-135 · AIS-14 | Unit Tests: Quality Assurance Agent

- **Description:** Test cases: passing inspection, borderline fail (score=70), critical fail (score<40)→CEO escalation, root cause for returned product, supplier 3-strike flag, `SupplierPerformanceUpdated` published after scoring.
- **Story Points:** 5 | **Priority:** P2

---

### US-136 · AIS-14 | Integration Test: QA Inspection Pipeline

- **Description:** Integration test: `InspectionRequested` → inspection evaluated → `QualityInspectionCompleted` → `quality_inspections` row with FKs verified → `SupplierPerformanceUpdated` published.
- **Story Points:** 5 | **Priority:** P2

---

## EP-29 · AIS-15 Planner Agent — Full Implementation

**Sprint Target:** Sprint 14 | **Priority:** P2 | **Depends on:** EP-23, EP-24

---

### US-137 · AIS-15 | LangGraph Node: PlannerNode

- **Description:** LangGraph node for enterprise execution planning. Subscribe to `DemandForecastGenerated` (not `ForecastCompleted` — AUD-54 fix). Writes `execution_plan`, `task_queue` to state.
- **Story Points:** 3 | **Priority:** P2

---

### US-138 · AIS-15 | Event Handlers: Planner Trigger Events

- **Description:** Handlers for `OrderCreated`, `InventoryUpdated`, `DemandForecastGenerated`, `RiskDetected`.
- **Technical Notes:** `RiskDetected` with score > 70 → trigger replan. `DemandForecastGenerated` → evaluate if current plan needs adjustment. All handlers write to `audit_logs`.
- **Story Points:** 3 | **Priority:** P2

---

### US-139 · AIS-15 | Business Logic: Plan Generation, Dependency Resolution & Task Assignment

- **Description:** As a supply chain system, I want the Planner Agent to generate a comprehensive enterprise execution plan, resolve agent dependencies, assign tasks, and publish `PlanGenerated`.
- **Technical Notes:**
  - Plan generation: LLM evaluates all inputs (order, inventory, forecast, finance, risk, supplier, capacity) and produces a JSON execution plan
  - Dependency resolution: deterministic DAG ordering (Order → Inventory → Warehouse → Supplier → Finance → Transportation)
  - Task assignment: `TaskAssigned` event per agent with: `agent_id`, `task_type`, `parameters`, `deadline`, `priority`
  - Routing decision: if inventory sufficient → skip SupplierNode; if risk high → trigger NegotiationNode first
  - Conflict detection: if Finance and Procurement recommend contradictory actions → route to NegotiationNode
  - Replanning: triggered on `RiskDetected` or `ShipmentDelayed` — re-runs plan with updated constraints
  - Published: `PlanGenerated`, `TaskAssigned` (one per agent), `EscalationRequested`, `WorkflowCompleted`
- **Acceptance Criteria:** Plan generated with correct agent assignments. Dependency order respected. Replanning triggers correctly. `PlanGenerated` event matches schema.
- **Story Points:** 8 | **Priority:** P2

---

### US-140 · AIS-15 | Unit Tests: Planner Agent

- **Description:** Test cases: normal plan generation, inventory-sufficient path (skip supplier), risk-triggered replan, conflict detected → Negotiation routing, all agents unavailable → `EscalationRequested`.
- **Story Points:** 5 | **Priority:** P2

---

### US-141 · AIS-15 | Integration Test: Plan Generation Pipeline

- **Description:** Integration test: complex order → plan generated → `TaskAssigned` events published for each required agent → all agents triggered correctly.
- **Story Points:** 8 | **Priority:** P2

---

## EP-30 · AIS-16 Negotiation Agent — Full Implementation

**Sprint Target:** Sprint 14 | **Priority:** P2 | **Depends on:** EP-29

---

### US-142 · AIS-16 | LangGraph Node: NegotiationAgent

- **Description:** LangGraph node for conflict resolution. Reads all BI agent outputs from shared state. Writes `negotiation_result`, `selected_strategy`.
- **Story Points:** 3 | **Priority:** P2

---

### US-143 · AIS-16 | Event Handlers: Conflict Detection Events

- **Description:** Handlers for `PlanGenerated`, `RiskDetected`, `FinancialRecommendationReady`, `InventoryAllocated`.
- **Technical Notes:** Trigger conflict detection when > 1 BI agent recommendation available. Use Redis sorted set to collect recommendations within a 30-second window before triggering negotiation.
- **Story Points:** 3 | **Priority:** P2

---

### US-144 · AIS-16 | Business Logic: Multi-Criteria Conflict Resolution

- **Description:** As a supply chain system, I want the Negotiation Agent to detect conflicting recommendations, apply the enterprise decision hierarchy, and reach consensus using LLM-assisted trade-off evaluation.
- **Technical Notes:**
  - Conflict detection: parse recommendations from Finance, Risk, Procurement, Inventory, Sustainability, Quality. If ≥ 2 recommend contradictory actions → conflict flag set.
  - Decision hierarchy (from ADS-00 §8): Safety > Compliance > Policy > Data Quality > Customer > Financial > Operational > Speed
  - Scoring: each alternative scored against all 7 criteria in AIS-16 §15 (Cost, Delivery Time, Risk, Sustainability, Customer Impact, Resource Utilization, Policy Compliance)
  - Consensus: if winning alternative scores > 60% on all criteria → `NegotiationCompleted`
  - No consensus: if no alternative passes → `NegotiationEscalated` to CEO
  - LLM use: trade-off evaluation across alternatives, consensus rationale generation
  - Published: `NegotiationCompleted`, `NegotiationEscalated`, `StrategySelected`
- **Acceptance Criteria:** Conflict detected when applicable. Hierarchy respected. Consensus or escalation within timeout. Decision auditable in `audit_logs`.
- **Story Points:** 8 | **Priority:** P2

---

### US-145 · AIS-16 | Unit Tests: Negotiation Agent

- **Description:** Test cases: 2 conflicting recommendations → consensus reached, 3-way conflict → hierarchy applied correctly, no consensus → `NegotiationEscalated`, policy violation → blocked regardless of other scores, LLM timeout → retry x2 then escalate.
- **Story Points:** 5 | **Priority:** P2

---

### US-146 · AIS-16 | Integration Test: Negotiation Resolution Pipeline

- **Description:** Integration test: inject conflicting recommendations into state → `NegotiationCompleted` event published → `StrategySelected` event verified → audit trail confirms decision rationale.
- **Story Points:** 8 | **Priority:** P2

---

## EP-31 · AIS-17 CEO Agent — Full Implementation

**Sprint Target:** Sprint 8 (MVP) + Sprint 14 (Full) | **Priority:** P1/P2 | **Depends on:** EP-29, EP-30

---

### US-147 · AIS-17 | LangGraph Node: CEO_Agent

- **Description:** LangGraph node for enterprise governance. Reads full shared state. Writes `executive_decision`, `approval_status`. Checkpoint before AND after approval (per AIS-17 §12).
- **Story Points:** 3 | **Priority:** P1

---

### US-148 · AIS-17 | Event Handlers: Governance Events

- **Description:** Handlers for `PlanGenerated`, `NegotiationCompleted`, `RiskDetected`, `WorkflowPaused`.
- **Technical Notes:** `HumanApprovalRequested` published when policy_exception_required flag set. Human approval via `POST /approval/{workflow_id}` API endpoint with `approved: bool` + `reason: str`. Timeout: if human doesn't respond in 4h → `WorkflowPaused` event + notification.
- **Story Points:** 3 | **Priority:** P1

---

### US-149 · AIS-17 | Business Logic: Policy Validation & Strategic Approval

- **Description:** As a supply chain system, I want the CEO Agent to validate enterprise policies, evaluate strategic criteria, and issue final approval or rejection with a full decision record.
- **Technical Notes:**
  - Policy checks (all deterministic): budget within fiscal limits, supplier not blacklisted, safety stock not violated, no compliance violations
  - Strategic criteria (LLM): strategic alignment, financial impact score, customer impact score, risk score, sustainability score, operational feasibility
  - Decision matrix: if all policy checks pass AND LLM confidence > 0.75 → `CEOApprovalGranted`; if policy fails → `CEOApprovalRejected` (no LLM needed); if policy passes but confidence 0.5–0.75 → `HumanApprovalRequested`
  - Human escalation: publish `HumanApprovalRequested`, pause workflow in Redis, await webhook from `POST /approval/{workflow_id}`
  - DB writes: UPDATE `agent_runtime.current_workflow_id`, INSERT `events` (approval), INSERT `audit_logs` with full decision payload
  - Published: `CEOApprovalGranted`, `CEOApprovalRejected`, `HumanApprovalRequested`, `WorkflowCompleted`
- **Acceptance Criteria:** Policy violations always rejected (no LLM override). Human approval triggers on correct confidence band. Dual checkpoint (before + after) verified.
- **Story Points:** 8 | **Priority:** P1

---

### US-150 · AIS-17 | Unit Tests: CEO Agent

- **Description:** Test cases: all policy pass + high confidence → `CEOApprovalGranted`, policy violation → `CEOApprovalRejected` (LLM not called), mid-confidence → `HumanApprovalRequested`, human approves → workflow resumed, human timeout → `WorkflowPaused`, LLM failure → safe rejection (fail-closed).
- **Story Points:** 5 | **Priority:** P1

---

### US-151 · AIS-17 | Integration Test: Governance & Human Approval

- **Description:** Integration test: `NegotiationCompleted` → CEO evaluates → `CEOApprovalGranted` published → `WorkflowCompleted` triggers Reporting Agent. Test human-in-the-loop: simulate human approval via API call → workflow resumes.
- **Story Points:** 8 | **Priority:** P1

---

## EP-32 · AIS-18 Reporting & Analytics Agent — Full Implementation

**Sprint Target:** Sprint 11 | **Priority:** P1 | **Depends on:** EP-17, US-59–62

---

### US-152 · AIS-18 | LangGraph Node: ReportingNode

- **Description:** LangGraph node for report generation. Reads entire `event_history` from state. Writes `report_reference`, `analytics_summary`. No workflow modifications — read-only access to operational data.
- **Story Points:** 3 | **Priority:** P1

---

### US-153 · AIS-18 | Event Handlers: Reporting Trigger Events

- **Description:** Handlers for `WorkflowCompleted`, `PlanGenerated`, `CEOApprovalGranted`, `ShipmentDelivered`, `RiskDetected`.
- **Technical Notes:** `WorkflowCompleted` → full report generation (async, non-blocking). `RiskDetected` → incident report. `CEOApprovalGranted` → decision summary. All reads from committed DB data only (no dirty reads). `reports` table uses INSERT only — no updates after `status = 'ready'`.
- **Story Points:** 3 | **Priority:** P1

---

### US-154 · AIS-18 | Business Logic: Report Generation, KPI Calculation & Dashboard Refresh

- **Description:** As a business user, I want the Reporting Agent to generate complete, immutable reports with KPI snapshots, explainability summaries, and dashboard data for every completed workflow.
- **Technical Notes:**
  - Report types: executive_summary, operational_kpi, financial, risk, sustainability, quality, audit, workflow
  - KPI calculation: deterministic from DB queries (no LLM for numbers)
    - Order fulfillment rate: `delivered_orders / total_orders × 100`
    - Inventory turnover: `COGS / avg_inventory_value`
    - On-time delivery: `on_time_shipments / total_shipments × 100`
    - Defect rate: `defective_units / total_units × 100`
    - Sustainability score: average from `sustainability_metrics`
  - Explainability (LLM): generates answers to 5 explainability questions for each workflow
  - DB writes: INSERT to `reports` with `payload_summary` JSONB snapshot. Status starts `'generating'` → `'ready'`. Immutable after `'ready'`.
  - Storage: serialize report to JSON → store to object storage → update `reports.storage_url`
  - Publish: `ReportGenerated`, `DashboardUpdated`, `KPIPublished`, `AuditCompleted`
  - RBAC: reports filtered by requesting user's role (executive vs operational)
- **Acceptance Criteria:** Full report generated for each workflow. All KPIs calculated correctly. `reports.status = 'ready'` cannot be updated. Dashboard data available via API.
- **Story Points:** 8 | **Priority:** P1

---

### US-155 · AIS-18 | Unit Tests: Reporting Agent

- **Description:** Test cases: full workflow report generation, KPI calculations verified against test data, LLM explainability for 5 questions, immutability enforced (UPDATE rejected), partial workflow → partial report with disclaimer, storage failure → retry x5, RBAC filtering.
- **Story Points:** 5 | **Priority:** P1

---

### US-156 · AIS-18 | Integration Test: End-to-End Reporting Pipeline

- **Description:** Integration test: `WorkflowCompleted` → report generated → `ReportGenerated` event → `reports` DB row with `status = 'ready'` verified → `GET /reports` API returns report → dashboard endpoint returns KPI data. Verify report immutability by attempting UPDATE.
- **Story Points:** 8 | **Priority:** P1

---

# PART D — Updated Story Dependency Matrix (US-59 to US-156)

```
Story         Depends On
──────────────────────────────────────────────────────────────────
US-59         US-06, US-09 (schema migration foundations)
US-60         US-59 (ORM for supplementary tables)
US-61         US-59, US-60 (seed data needs tables + models)
US-62         US-59 (indexes after table creation)
US-63         US-12, US-13 (event bus must exist before fixing names)
US-64         US-63, agents that own the publishers (phased)
US-65         US-12 (Celery/RabbitMQ infrastructure)
US-66         US-13 (EventPublisher class must exist)

US-67         US-21, US-25, US-63 (LangGraph + event compliance)
US-68         US-67, US-13 (node + consumer infra)
US-69         US-68, US-08 (business logic + ORM)
US-70         US-69 (unit tests after business logic)
US-71         US-67, US-68, US-69, US-70 (integration needs all above)

US-72         US-21, US-63
US-73         US-72, US-13
US-74         US-73, US-08, US-60, US-61
US-75         US-74
US-76         US-72–US-75

US-77         US-21, US-63, US-60
US-78         US-77, US-13
US-79         US-78, US-08
US-80         US-79
US-81         US-77–US-80

US-82         US-21, US-63
US-83         US-82, US-13
US-84         US-83, US-08
US-85         US-84
US-86         US-82–US-85

US-87         US-21, US-63, US-59, US-60
US-88         US-87, US-13, US-64
US-89         US-88, US-08
US-90         US-89
US-91         US-87–US-90

US-92         US-21, US-63, US-59, US-60
US-93         US-92, US-13
US-94         US-93, US-08, US-61
US-95         US-94
US-96         US-92–US-95

US-97         US-21, US-63, US-76 (needs forecast)
US-98         US-97, US-13, US-64
US-99         US-98, US-08
US-100        US-99
US-101        US-97–US-100

US-102        US-21, US-63, US-59, US-60, US-64
US-103        US-102, US-13, US-64
US-104        US-103, US-08
US-105        US-104
US-106        US-102–US-105

US-107        US-21, US-63
US-108        US-107, US-13
US-109        US-108, US-08
US-110        US-109
US-111        US-107–US-110

US-112        US-21, US-63
US-113        US-112, US-13, US-64
US-114        US-113, US-08
US-115        US-114
US-116        US-112–US-115

US-117        US-21, US-63, US-59, US-60, US-76 (forecast)
US-118        US-117, US-13
US-119        US-118, US-08, US-111 (finance)
US-120        US-119
US-121        US-117–US-120

US-122        US-21, US-63, US-59, US-60, US-65 (Celery)
US-123        US-122, US-13, US-65
US-124        US-123, US-08, US-91 (supplier)
US-125        US-124
US-126        US-122–US-125

US-127        US-21, US-63, US-59, US-60
US-128        US-127, US-13, US-64, US-96 (transportation routes)
US-129        US-128, US-08
US-130        US-129
US-131        US-127–US-130

US-132        US-21, US-63, US-59, US-60, US-64
US-133        US-132, US-13, US-64
US-134        US-133, US-08, US-101 (manufacturing)
US-135        US-134
US-136        US-132–US-135

US-137        US-21, US-63, US-111 (finance), US-116 (risk)
US-138        US-137, US-13
US-139        US-138, US-08, US-81 (inventory), US-91 (supplier)
US-140        US-139
US-141        US-137–US-140

US-142        US-21, US-63, US-141 (planner)
US-143        US-142, US-13
US-144        US-143, US-08, US-111 (finance), US-116 (risk)
US-145        US-144
US-146        US-142–US-145

US-147        US-21, US-63
US-148        US-147, US-13
US-149        US-148, US-08, US-146 (negotiation)
US-150        US-149
US-151        US-147–US-150

US-152        US-21, US-63, US-59, US-60
US-153        US-152, US-13
US-154        US-153, US-08, US-111 (finance), US-116 (risk)
US-155        US-154
US-156        US-152–US-155, US-151 (CEO approval)
```

---

# PART E — Updated Implementation Roadmap Addendum

## Sprint 3 (Addendum) — Supplementary Schema
**New Stories:** US-59, US-60, US-61, US-62
**Milestone:** All 27 tables migrated, seeded, and ORM-accessible
**Audit Resolved:** AUD-39, AUD-40, AUD-41, AUD-42, AUD-43, AUD-44, AUD-45, AUD-46

## Sprint 5 (Addendum) — Event Compliance
**New Stories:** US-63, US-64 (Phase 1 — document fixes), US-65, US-66
**Milestone:** All event names canonical. Celery scheduled publishers operational. Runtime validator active.
**Audit Resolved:** AUD-47, AUD-48, AUD-49, AUD-50, AUD-51, AUD-52, AUD-53, AUD-54, AUD-55, AUD-56

## Sprint 8 (Addendum) — Granular MVP Agents
**New Stories:** US-67–71 (AIS-01), US-77–81 (AIS-03), US-82–86 (AIS-04), US-87–91 (AIS-05), US-92–96 (AIS-06), US-147–151 (AIS-17 MVP)

## Sprint 11 (Addendum) — Granular BI Agents
**New Stories:** US-72–76 (AIS-02), US-107–111 (AIS-09), US-112–116 (AIS-10), US-152–156 (AIS-18)

## Sprint 14 (Addendum) — Granular Coordination
**New Stories:** US-137–141 (AIS-15), US-142–146 (AIS-16)

## Sprint 16 (Addendum) — Granular Advanced Agents
**New Stories:** US-97–101 (AIS-07), US-102–106 (AIS-08), US-117–121 (AIS-11), US-122–126 (AIS-12), US-127–131 (AIS-13), US-132–136 (AIS-14)

---

# Grand Total Summary

| Metric | Value |
|---|---|
| Total Epics | **33** (EP-01 to EP-32 + 1 extension) |
| Total User Stories | **156** (US-01 to US-156) |
| Total Story Points | **~595** |
| Total Agents — Fully Specified | **18** |
| Total Agents — Granular (5 stories each) | **18** |
| Audit Issues Identified | **56** (AUD-01 to AUD-56) |
| Audit Issues Resolved by Stories | **48+** |
| Estimated Sprints (2-week) | **25** |
| Estimated Timeline | **~12–14 months (1 team)** |
| New Schema Tables Added | **9** (purchase_orders, support_tickets, pricing_history, contracts, contract_products, carriers, transportation_routes, promotions, promotion_products, reports) |
| New Views Added | **1** (purchase_history) |
| Event Name Mismatches Resolved | **13** |
| Dead Event Subscriptions Fixed | **4** |
| New Event Publishers Added | **3** (Celery scheduler, ADS-05, ADS-07, ADS-08) |
