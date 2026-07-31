# AI Supply Chain Digital Twin
# Canonical Event Glossary

> **Document:** EVT-GLOSSARY-001  
> **Version:** 1.0  
> **Date:** 2026-07-28  
> **Status:** Authoritative — All agents MUST use these exact event names.  
> **Resolves:** AUD-47, AUD-53, AUD-54, AUD-55 (event name mismatches discovered in AIS cross-reference)

---

## Purpose

This document is the **single source of truth** for all event names used in the AI Supply Chain Digital Twin.

Every event must:
1. Use the exact `event_type` string defined in this glossary
2. Include the required `version`, `correlation_id`, and `source_agent` fields
3. Follow the schema defined in the `events` table
4. Be idempotent — republishing the same `event_id` must produce no side effects

**Any AIS file that uses a different event name must be updated to match this glossary.**

---

## Standard Event Envelope

All events share this envelope structure:

```json
{
  "event_id":       "uuid",
  "correlation_id": "uuid",
  "workflow_id":    "uuid | null",
  "event_type":     "<canonical_event_type_from_this_glossary>",
  "source_agent":   "ADS-XX",
  "target_agent":   "ADS-XX | null",
  "priority":       "low | medium | high | critical",
  "version":        "1.0",
  "simulation_id":  "uuid | null",
  "payload":        { ... },
  "metadata":       { "retry_count": 0, "published_at": "ISO8601" },
  "created_at":     "ISO8601"
}
```

---

## Event Catalogue

### Domain: ORDER MANAGEMENT

| Canonical Event Name | Version | Publisher | Subscribers | Description |
|---|---|---|---|---|
| `CustomerOrderReceived` | 1.0 | External / API Gateway | ADS-01 | Raw customer order received via API |
| `OrderCreated` | 1.0 | ADS-01 | ADS-02, ADS-03, ADS-08, ADS-09, ADS-15 | Order validated and persisted in DB |
| `OrderValidated` | 1.0 | ADS-01 | ADS-15 | Order passed all business rule validations |
| `OrderRejected` | 1.0 | ADS-01 | ADS-08 | Order failed validation (duplicate, invalid customer, etc.) |
| `OrderCancelled` | 1.0 | ADS-01 | ADS-03, ADS-08, ADS-09 | Customer or system cancelled the order |
| `OrderUpdated` | 1.0 | ADS-01 | ADS-03, ADS-15 | Order amended (quantity, priority, etc.) |
| `OrderFulfilled` | 1.0 | ADS-01 | ADS-08, ADS-09, ADS-18 | All items shipped and delivered successfully |

---

### Domain: INVENTORY

| Canonical Event Name | Version | Publisher | Subscribers | Description |
|---|---|---|---|---|
| `InventoryAllocationRequested` | 1.0 | ADS-01 | ADS-03 | Order Management requests stock reservation |
| `InventoryAllocated` | 1.0 | ADS-03 | ADS-04, ADS-06, ADS-15 | Stock successfully reserved for order |
| `InventoryReleased` | 1.0 | ADS-03 | ADS-15 | Reservation released (order cancel / failure) |
| `InventoryLow` | 1.0 | ADS-03 | ADS-05, ADS-10, ADS-12, ADS-15 | Stock fell below reorder point |
| `InventoryOutOfStock` | 1.0 | ADS-03 | ADS-01, ADS-08, ADS-10, ADS-15 | Zero available stock for a product |
| `ReorderRequested` | 1.0 | ADS-03 | ADS-05 | Explicit trigger to Supplier Agent to procure |
| `InventoryUpdated` | 1.0 | ADS-03 | ADS-02, ADS-11 | Inventory quantity changed (in/out/adjustment) |
| `InventoryAdjusted` | 1.0 | ADS-04 | ADS-03 | Warehouse physical count differs from system — correction applied |

---

### Domain: DEMAND FORECASTING

| Canonical Event Name | Version | Publisher | Subscribers | Description |
|---|---|---|---|---|
| `DemandForecastGenerated` | 1.0 | ADS-02 | ADS-03, ADS-07, ADS-11, ADS-12, ADS-15 | ⚠️ **Canonical name.** Replaces: `DemandForecastUpdated` (AIS-11), `ForecastUpdated` (AIS-07), `ForecastCompleted` (AIS-15) |
| `DemandSpikeDetected` | 1.0 | ADS-02 | ADS-03, ADS-09, ADS-10, ADS-15 | Demand significantly higher than forecast |
| `DemandDropDetected` | 1.0 | ADS-02 | ADS-09, ADS-11, ADS-15 | Demand significantly lower than forecast |

> [!WARNING]
> **AUD-54 / AUD-55 FIX:** `DemandForecastGenerated` is the ONLY correct event name.
> - AIS-07 used `ForecastUpdated` — **must change to `DemandForecastGenerated`**
> - AIS-11 used `DemandForecastUpdated` — **must change to `DemandForecastGenerated`**
> - AIS-15 used `ForecastCompleted` — **must change to `DemandForecastGenerated`**

---

### Domain: WAREHOUSE

| Canonical Event Name | Version | Publisher | Subscribers | Description |
|---|---|---|---|---|
| `InventoryReceived` | 1.0 | ADS-04 | ADS-03 | Goods received at warehouse from supplier |
| `PickingCompleted` | 1.0 | ADS-04 | ADS-06 | Warehouse picked all items for order |
| `PackingCompleted` | 1.0 | ADS-04 | ADS-06 | Warehouse packed and ready to dispatch |
| `ShipmentReady` | 1.0 | ADS-04 | ADS-06 | Shipment fully prepared for carrier pickup |
| `StockTransferred` | 1.0 | ADS-04 | ADS-03, ADS-15 | Stock moved between warehouse locations |
| `WarehouseCapacityUpdated` | 1.0 | ADS-04 | ADS-15 | Warehouse load changed significantly |
| `WarehouseExceptionRaised` | 1.0 | ADS-04 | ADS-15, ADS-17 | Critical warehouse event requiring escalation |
| `ShipmentScheduled` | 1.0 | ADS-06 | ADS-04 | Transportation Agent scheduled a pickup from warehouse |

---

### Domain: SUPPLIER & PROCUREMENT

| Canonical Event Name | Version | Publisher | Subscribers | Description |
|---|---|---|---|---|
| `SupplierSelected` | 1.0 | ADS-05 | ADS-09, ADS-15 | Supplier chosen for a procurement request |
| `PurchaseOrderCreated` | 1.0 | ADS-05 | ADS-07, ADS-09, ADS-10 | ⚠️ **Canonical name.** Replaces: `PurchaseOrderRequested` (AIS-05 output). PO has been formally raised. |
| `ProcurementCompleted` | 1.0 | ADS-05 | ADS-03, ADS-09, ADS-15 | Supplier confirmed and PO acknowledged |
| `SupplierUnavailable` | 1.0 | ADS-05 | ADS-15, ADS-17 | No qualified supplier found for request |
| `SupplierPerformanceUpdated` | 1.0 | ADS-05, ADS-14 | ADS-10, ADS-12 | ⚠️ **AUD-56 FIX:** Published by Supplier Agent after delivery confirmation OR by QA Agent after inspection. Resolves dead subscription. |
| `SupplierUpdated` | 1.0 | ADS-05 | ADS-13, ADS-14 | ⚠️ **AUD-48 FIX:** Published by Supplier Agent when supplier master data changes (blacklisting, rating update, contract change). |
| `ProductionPlanned` | 1.0 | ADS-15 | ADS-05 | Planner signals Supplier Agent that raw materials needed |
| `ContractExpiring` | 1.0 | Celery Scheduler | ADS-12 | ⚠️ **AUD-51 FIX:** Published by a Celery scheduled job that checks `contracts.end_date` daily. |

---

### Domain: TRANSPORTATION

| Canonical Event Name | Version | Publisher | Subscribers | Description |
|---|---|---|---|---|
| `ShipmentCreated` | 1.0 | ADS-06 | ADS-08, ADS-15 | Carrier booking created and tracking ID assigned |
| `ShipmentDispatched` | 1.0 | ADS-06 | ADS-08, ADS-09, ADS-13 | Carrier collected shipment |
| `ETAUpdated` | 1.0 | ADS-06 | ADS-08, ADS-15 | ETA recalculated (traffic, customs, delay) |
| `ShipmentDelayed` | 1.0 | ADS-06 | ADS-08, ADS-10, ADS-15 | Active delay detected in transit |
| `ShipmentDelivered` | 1.0 | ADS-06 | ADS-03, ADS-08, ADS-09, ADS-13, ADS-18 | ⚠️ **Note:** AIS-03 subscribed to `ShipmentReceived` — use `ShipmentDelivered` instead. |
| `DeliveryDelayed` | 1.0 | ADS-06 | ADS-08 | Final delivery missed confirmed ETA |
| `ShipmentReturned` | 1.0 | ADS-06 | ADS-03, ADS-08, ADS-14 | Shipment returned by customer or carrier |

> [!WARNING]
> **AUD-47 FIX — `OrderApproved` is replaced by `CEOApprovalGranted`.**
> AIS-06 subscribed to `OrderApproved` which never existed.
> Transportation Agent must subscribe to `CEOApprovalGranted` (published by ADS-17).

---

### Domain: MANUFACTURING

| Canonical Event Name | Version | Publisher | Subscribers | Description |
|---|---|---|---|---|
| `ProductionRequested` | 1.0 | ADS-15 | ADS-07 | Planner assigns a production task to Manufacturing Agent |
| `ManufacturingStarted` | 1.0 | ADS-07 | ADS-15 | Production of a batch has begun |
| `ManufacturingPaused` | 1.0 | ADS-07 | ADS-15, ADS-10 | Production paused (material shortage, capacity) |
| `ManufacturingCompleted` | 1.0 | ADS-07 | ADS-03, ADS-04, ADS-09, ADS-13, ADS-14 | Batch complete. Triggers QA inspection automatically. |
| `ManufacturingDelayed` | 1.0 | ADS-07 | ADS-10, ADS-15 | Production schedule missed |
| `CapacityExceeded` | 1.0 | ADS-07 | ADS-10, ADS-15, ADS-17 | Factory capacity limit hit |
| `InspectionRequested` | 1.0 | ADS-07 | ADS-14 | ⚠️ **AUD-49 FIX:** Manufacturing Agent publishes this after completing a batch, directly triggering QA Agent. |
| `ProductReturned` | 1.0 | ADS-08 | ADS-14 | ⚠️ **AUD-50 FIX:** Customer Service Agent publishes this when a return is processed, triggering QA root cause analysis. |

> [!WARNING]
> **AUD-47 FIX — `PlannerApproved` is replaced by `ProductionRequested`.**
> AIS-07 subscribed to `PlannerApproved` which was never defined.
> Manufacturing Agent must subscribe to `ProductionRequested` (published by ADS-15).

---

### Domain: FINANCE

| Canonical Event Name | Version | Publisher | Subscribers | Description |
|---|---|---|---|---|
| `FinancialApprovalGranted` | 1.0 | ADS-09 | ADS-05, ADS-06, ADS-15, ADS-17 | Finance Agent approved the cost for a workflow |
| `BudgetExceeded` | 1.0 | ADS-09 | ADS-10, ADS-15, ADS-17 | ⚠️ **AUD-53 FIX:** Canonical name. AIS-10 subscribed to `FinancialThresholdExceeded` — must change to `BudgetExceeded`. |
| `CostOptimizationSuggested` | 1.0 | ADS-09 | ADS-12, ADS-15 | Finance recommends cheaper alternatives |
| `FinancialRecommendationReady` | 1.0 | ADS-09 | ADS-16 | Finance has completed its analysis for Negotiation Agent |

> [!WARNING]
> **AUD-53 FIX:** `FinancialThresholdExceeded` (used in AIS-10) does not exist.
> Risk Agent (AIS-10) must subscribe to `BudgetExceeded` instead.

---

### Domain: RISK

| Canonical Event Name | Version | Publisher | Subscribers | Description |
|---|---|---|---|---|
| `RiskDetected` | 1.0 | ADS-10 | ADS-05, ADS-06, ADS-12, ADS-15, ADS-16, ADS-17, ADS-18 | Risk score crossed a threshold (Medium, High, or Critical) |
| `HighRiskAlert` | 1.0 | ADS-10 | ADS-15, ADS-17 | Risk score >= 70 (High/Critical threshold) |
| `MitigationRecommended` | 1.0 | ADS-10 | ADS-15, ADS-16 | Risk Agent has produced a mitigation plan |
| `ExecutiveEscalation` | 1.0 | ADS-10 | ADS-17 | Critical risk (>= 90) requiring CEO review |
| `RiskAssessmentCompleted` | 1.0 | ADS-10 | ADS-11, ADS-12 | Risk Agent finished evaluating an entity |

---

### Domain: PRICING

| Canonical Event Name | Version | Publisher | Subscribers | Description |
|---|---|---|---|---|
| `PricingRecommendationGenerated` | 1.0 | ADS-11 | ADS-15, ADS-17 | Dynamic pricing recommendation ready for review |
| `PriceChangeRequiresApproval` | 1.0 | ADS-11 | ADS-17 | Price change exceeds autonomous threshold — CEO approval needed |
| `PricingSimulationCompleted` | 1.0 | ADS-11 | ADS-18 | What-if pricing simulation finished |

---

### Domain: PROCUREMENT STRATEGY

| Canonical Event Name | Version | Publisher | Subscribers | Description |
|---|---|---|---|---|
| `ProcurementStrategyGenerated` | 1.0 | ADS-12 | ADS-15, ADS-16, ADS-17 | Long-term sourcing strategy recommendation ready |
| `SupplierDiversificationRecommended` | 1.0 | ADS-12 | ADS-15, ADS-17 | Risk of single-source dependency detected |
| `StrategicSupplierSelected` | 1.0 | ADS-12 | ADS-15 | Long-term strategic supplier chosen |

---

### Domain: SUSTAINABILITY

| Canonical Event Name | Version | Publisher | Subscribers | Description |
|---|---|---|---|---|
| `SustainabilityCalculated` | 1.0 | ADS-13 | ADS-15, ADS-18 | Carbon footprint and ESG score calculated for a shipment |
| `CarbonThresholdExceeded` | 1.0 | ADS-13 | ADS-15, ADS-17 | Shipment carbon exceeds policy limit |
| `SustainableSupplierRecommended` | 1.0 | ADS-13 | ADS-12, ADS-15 | ESG-preferred alternative supplier identified |
| `ESGAlertRaised` | 1.0 | ADS-13 | ADS-17, ADS-18 | ESG compliance violation detected |

---

### Domain: QUALITY ASSURANCE

| Canonical Event Name | Version | Publisher | Subscribers | Description |
|---|---|---|---|---|
| `QualityInspectionCompleted` | 1.0 | ADS-14 | ADS-03, ADS-04, ADS-15 | Inspection finished — result may be pass or fail |
| `QualityIssueDetected` | 1.0 | ADS-14 | ADS-05, ADS-10, ADS-15, ADS-17 | Defect rate exceeded threshold |
| `CorrectiveActionRequested` | 1.0 | ADS-14 | ADS-05, ADS-07, ADS-15 | CAPA initiated for a quality failure |
| `SupplierQualityUpdated` | 1.0 | ADS-14 | ADS-05, ADS-10 | Supplier quality score recalculated |

---

### Domain: PLANNING & COORDINATION

| Canonical Event Name | Version | Publisher | Subscribers | Description |
|---|---|---|---|---|
| `PlanGenerated` | 1.0 | ADS-15 | ADS-16, ADS-17 | Planner produced an execution plan |
| `TaskAssigned` | 1.0 | ADS-15 | ADS-01 to ADS-14 | Planner dispatched a task to a specific agent |
| `WorkflowCompleted` | 1.0 | ADS-17 | ADS-18 | CEO Agent approved and closed the workflow |
| `WorkflowPaused` | 1.0 | ADS-17 | ADS-15 | Workflow paused for human approval |
| `EscalationRequested` | 1.0 | ADS-15 | ADS-17 | Planner escalated a conflict to CEO |
| `NegotiationCompleted` | 1.0 | ADS-16 | ADS-17 | Negotiation Agent reached a consensus |
| `NegotiationEscalated` | 1.0 | ADS-16 | ADS-17 | Negotiation could not reach consensus — CEO required |
| `StrategySelected` | 1.0 | ADS-16 | ADS-15, ADS-17 | Best strategy selected after multi-agent trade-off |
| `CEOApprovalGranted` | 1.0 | ADS-17 | ADS-06, ADS-15, ADS-18 | ⚠️ **AUD-47 FIX:** Replaces `OrderApproved`. Transportation Agent must subscribe here. |
| `CEOApprovalRejected` | 1.0 | ADS-17 | ADS-15, ADS-18 | CEO rejected the proposed workflow decision |
| `HumanApprovalRequested` | 1.0 | ADS-17 | External / Dashboard | Workflow interrupt — human must approve via API |

---

### Domain: PROMOTIONS (Celery-Generated)

| Canonical Event Name | Version | Publisher | Subscribers | Description |
|---|---|---|---|---|
| `PromotionScheduled` | 1.0 | Celery Scheduler | ADS-02 | ⚠️ **AUD-52 FIX:** Published by Celery Beat job when a promotion enters 'active' status. Triggers Demand Forecast Agent to re-forecast. |
| `PromotionStarted` | 1.0 | Celery Scheduler | ADS-02, ADS-11 | Promotion officially began |
| `PromotionEnded` | 1.0 | Celery Scheduler | ADS-02, ADS-11 | Promotion concluded |

---

### Domain: REPORTING

| Canonical Event Name | Version | Publisher | Subscribers | Description |
|---|---|---|---|---|
| `ReportGenerated` | 1.0 | ADS-18 | Dashboard / External | Executive or operational report is ready |
| `DashboardUpdated` | 1.0 | ADS-18 | Dashboard / External | Live dashboard data refreshed |
| `KPIPublished` | 1.0 | ADS-18 | Dashboard / External | KPI snapshot published |
| `AuditCompleted` | 1.0 | ADS-18 | ADS-17 | Audit trail report generated and archived |

---

## AIS File Correction Map

All AIS files with event name mismatches must be updated. Here is the exact correction needed per file:

| AIS File | Incorrect Event | Correct Event | Audit ID |
|---|---|---|---|
| [AIS-06](Agent%20Specification%20Document/Agent%20Implementation%20Specification/AIS-06_Transportation_Agent.md) | `OrderApproved` (subscribed) | `CEOApprovalGranted` | AUD-47 |
| [AIS-07](Agent%20Specification%20Document/Agent%20Implementation%20Specification/AIS-07_Manufacturing_Agent.md) | `PlannerApproved` (subscribed) | `ProductionRequested` | AUD-47 |
| [AIS-07](Agent%20Specification%20Document/Agent%20Implementation%20Specification/AIS-07_Manufacturing_Agent.md) | `ForecastUpdated` (subscribed) | `DemandForecastGenerated` | AUD-54 |
| [AIS-10](Agent%20Specification%20Document/Agent%20Implementation%20Specification/AIS-10_Risk_Management_Agent.md) | `FinancialThresholdExceeded` (subscribed) | `BudgetExceeded` | AUD-53 |
| [AIS-11](Agent%20Specification%20Document/Agent%20Implementation%20Specification/AIS-11_Pricing_Agent.md) | `DemandForecastUpdated` (subscribed) | `DemandForecastGenerated` | AUD-55 |
| [AIS-11](Agent%20Specification%20Document/Agent%20Implementation%20Specification/AIS-11_Pricing_Agent.md) | `FinanceRecommendationPublished` (subscribed) | `FinancialRecommendationReady` | — |
| [AIS-15](Agent%20Specification%20Document/Agent%20Implementation%20Specification/AIS-15_Planner_Agent.md) | `ForecastCompleted` (subscribed) | `DemandForecastGenerated` | AUD-54 |
| [AIS-13](Agent%20Specification%20Document/Agent%20Implementation%20Specification/AIS-13_Sustainability_Agent.md) | `SupplierUpdated` (subscribed — no publisher) | Now published by ADS-05 | AUD-48 |
| [AIS-14](Agent%20Specification%20Document/Agent%20Implementation%20Specification/AIS-14_Quality_Assurance_Agent.md) | `SupplierUpdated` (subscribed — no publisher) | Now published by ADS-05 | AUD-48 |
| [AIS-14](Agent%20Specification%20Document/Agent%20Implementation%20Specification/AIS-14_Quality_Assurance_Agent.md) | `InspectionRequested` (subscribed — no publisher) | Now published by ADS-07 | AUD-49 |
| [AIS-08](Agent%20Specification%20Document/Agent%20Implementation%20Specification/AIS-08_Customer_Service_Agent.md) | `ReturnRequested` (no canonical definition) | `ShipmentReturned` | — |
| [AIS-03](Agent%20Specification%20Document/Agent%20Implementation%20Specification/AIS-03_Inventory_Management_Agent.md) | `ShipmentReceived` (subscribed) | `ShipmentDelivered` | — |

---

## Event Priority Rules

| Priority | When to Use |
|---|---|
| `critical` | Safety stock breach, carrier blacklist, CEO escalation, system failure |
| `high` | Risk score ≥ 70, budget exceeded, QA failure, shipment delayed |
| `medium` | Standard order flow events, forecast updates, supplier selection |
| `low` | Background reporting, analytics, KPI snapshots |

---

## Versioning Policy

- Event version starts at `1.0`
- Breaking payload changes → increment major version: `2.0`
- Additive payload changes → increment minor version: `1.1`
- Consumers must handle older versions gracefully (forward-compatible)
- All versions are stored permanently in the `events` table

---

*This document supersedes any event names found in individual AIS files where a conflict exists.*
