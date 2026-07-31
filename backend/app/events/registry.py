"""
Canonical Event Registry — US-66 / EP-14

Single source of truth for all 60 event types in the AI Supply Chain Digital Twin.
Every event name published to RabbitMQ must exist in this registry.

Generated from: CANONICAL_Event_Glossary.md
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Canonical event names, grouped by domain
# ---------------------------------------------------------------------------

CANONICAL_EVENTS: dict[str, dict] = {

    # ── Order Management (ADS-01) ────────────────────────────────────────────
    "CustomerOrderReceived": {
        "version": "1.0",
        "publisher": "ADS-01",
        "subscribers": ["ADS-01"],
        "description": "External order received from customer-facing channel.",
    },
    "CustomerOrderUpdated": {
        "version": "1.0",
        "publisher": "ADS-01",
        "subscribers": ["ADS-01"],
        "description": "Customer modified an existing order before processing.",
    },
    "CustomerOrderCancelled": {
        "version": "1.0",
        "publisher": "ADS-01",
        "subscribers": ["ADS-01", "ADS-03"],
        "description": "Customer cancelled an order; inventory must be released.",
    },
    "OrderCreated": {
        "version": "1.0",
        "publisher": "ADS-01",
        "subscribers": ["ADS-02", "ADS-03", "ADS-04", "ADS-08"],
        "description": "Order validated and persisted. Triggers inventory check.",
    },
    "OrderRejected": {
        "version": "1.0",
        "publisher": "ADS-01",
        "subscribers": ["ADS-08"],
        "description": "Order failed validation. Reason included in payload.",
    },
    "OrderCancelled": {
        "version": "1.0",
        "publisher": "ADS-01",
        "subscribers": ["ADS-03", "ADS-06", "ADS-08"],
        "description": "Order cancelled post-creation (e.g. payment failure).",
    },
    "OrderStatusUpdated": {
        "version": "1.0",
        "publisher": "ADS-01",
        "subscribers": ["ADS-08"],
        "description": "Order lifecycle status changed.",
    },

    # ── Demand Forecast (ADS-02) ─────────────────────────────────────────────
    "DemandForecastGenerated": {
        "version": "1.0",
        "publisher": "ADS-02",
        "subscribers": ["ADS-03", "ADS-07", "ADS-11", "ADS-15"],
        "description": "New demand forecast produced for a product/period.",
    },
    "DemandSpikeDetected": {
        "version": "1.0",
        "publisher": "ADS-02",
        "subscribers": ["ADS-03", "ADS-10", "ADS-15"],
        "description": "Forecast qty exceeds 2× 12-month average — anomaly flag.",
    },
    "DemandDropDetected": {
        "version": "1.0",
        "publisher": "ADS-02",
        "subscribers": ["ADS-10", "ADS-15"],
        "description": "Forecast qty is below 50% of 12-month average.",
    },

    # ── Inventory (ADS-03) ───────────────────────────────────────────────────
    "InventoryAllocated": {
        "version": "1.0",
        "publisher": "ADS-03",
        "subscribers": ["ADS-04", "ADS-06"],
        "description": "Stock reserved for an order in a specific warehouse.",
    },
    "InventoryLow": {
        "version": "1.0",
        "publisher": "ADS-03",
        "subscribers": ["ADS-05", "ADS-10", "ADS-17"],
        "description": "Available qty at or below safety_stock after allocation.",
    },
    "InventoryOutOfStock": {
        "version": "1.0",
        "publisher": "ADS-03",
        "subscribers": ["ADS-05", "ADS-07", "ADS-10", "ADS-17"],
        "description": "No warehouse has sufficient stock to fulfil the order.",
    },
    "ReorderRequested": {
        "version": "1.0",
        "publisher": "ADS-03",
        "subscribers": ["ADS-05"],
        "description": "Stock crossed reorder_point; Supplier Agent should create PO.",
    },
    "InventoryUpdated": {
        "version": "1.0",
        "publisher": "ADS-03",
        "subscribers": ["ADS-02", "ADS-15"],
        "description": "Inventory record changed (adjustment, receipt, or release).",
    },
    "InventoryAdjusted": {
        "version": "1.0",
        "publisher": "ADS-03",
        "subscribers": ["ADS-03"],
        "description": "Physical count correction applied to inventory.",
    },

    # ── Warehouse (ADS-04) ───────────────────────────────────────────────────
    "PickingCompleted": {
        "version": "1.0",
        "publisher": "ADS-04",
        "subscribers": ["ADS-04"],
        "description": "Pick task completed for order items.",
    },
    "PackingCompleted": {
        "version": "1.0",
        "publisher": "ADS-04",
        "subscribers": ["ADS-04"],
        "description": "Pack task completed; shipment ready for dispatch.",
    },
    "ShipmentReady": {
        "version": "1.0",
        "publisher": "ADS-04",
        "subscribers": ["ADS-06"],
        "description": "Warehouse has packed and handed over shipment for dispatch.",
    },
    "WarehouseCapacityUpdated": {
        "version": "1.0",
        "publisher": "ADS-04",
        "subscribers": ["ADS-03", "ADS-10"],
        "description": "Warehouse load changed (goods in or out).",
    },
    "WarehouseExceptionRaised": {
        "version": "1.0",
        "publisher": "ADS-04",
        "subscribers": ["ADS-17"],
        "description": "Warehouse exception detected (capacity breach, discrepancy).",
    },
    "InventoryReceived": {
        "version": "1.0",
        "publisher": "ADS-04",
        "subscribers": ["ADS-03", "ADS-04"],
        "description": "Goods received at warehouse and scanned into inventory.",
    },

    # ── Supplier (ADS-05) ────────────────────────────────────────────────────
    "SupplierSelected": {
        "version": "1.0",
        "publisher": "ADS-05",
        "subscribers": ["ADS-09"],
        "description": "Optimal supplier chosen for a reorder or emergency procurement.",
    },
    "PurchaseOrderCreated": {
        "version": "1.0",
        "publisher": "ADS-05",
        "subscribers": ["ADS-09", "ADS-12"],
        "description": "PO submitted to supplier; triggers Finance Agent approval flow.",
    },
    "SupplierUnavailable": {
        "version": "1.0",
        "publisher": "ADS-05",
        "subscribers": ["ADS-07", "ADS-17"],
        "description": "No eligible supplier found; escalate to manufacturing or CEO.",
    },
    "SupplierUpdated": {
        "version": "1.0",
        "publisher": "ADS-05",
        "subscribers": ["ADS-10", "ADS-12"],
        "description": "Supplier master data changed (blacklist, rating, terms).",
    },
    "SupplierPerformanceUpdated": {
        "version": "1.0",
        "publisher": "ADS-05",
        "subscribers": ["ADS-10", "ADS-12"],
        "description": "Supplier delivery confirmed; performance score recalculated.",
    },

    # ── Transportation (ADS-06) ──────────────────────────────────────────────
    "ShipmentCreated": {
        "version": "1.0",
        "publisher": "ADS-06",
        "subscribers": ["ADS-08", "ADS-13"],
        "description": "Shipment record created with carrier and route.",
    },
    "ShipmentDispatched": {
        "version": "1.0",
        "publisher": "ADS-06",
        "subscribers": ["ADS-08", "ADS-13"],
        "description": "Carrier has collected the shipment.",
    },
    "ShipmentDelivered": {
        "version": "1.0",
        "publisher": "ADS-06",
        "subscribers": ["ADS-03", "ADS-08"],
        "description": "Delivery confirmed; triggers inventory receipt and customer notification.",
    },
    "DeliveryDelayed": {
        "version": "1.0",
        "publisher": "ADS-06",
        "subscribers": ["ADS-08", "ADS-10", "ADS-17"],
        "description": "Carrier confirmed delay; new ETA attached to payload.",
    },
    "ETAUpdated": {
        "version": "1.0",
        "publisher": "ADS-06",
        "subscribers": ["ADS-08"],
        "description": "ETA recalculated post-dispatch.",
    },

    # ── Manufacturing (ADS-07) ───────────────────────────────────────────────
    "ProductionRequested": {
        "version": "1.0",
        "publisher": "ADS-15",
        "subscribers": ["ADS-07"],
        "description": "Planner Agent authorised a manufacturing run.",
    },
    "ManufacturingStarted": {
        "version": "1.0",
        "publisher": "ADS-07",
        "subscribers": ["ADS-10"],
        "description": "Production line started for a manufacturing order.",
    },
    "ManufacturingCompleted": {
        "version": "1.0",
        "publisher": "ADS-07",
        "subscribers": ["ADS-03", "ADS-14"],
        "description": "Production completed; triggers inventory update and QA inspection.",
    },
    "ManufacturingPaused": {
        "version": "1.0",
        "publisher": "ADS-07",
        "subscribers": ["ADS-10", "ADS-17"],
        "description": "Production paused (capacity, material, or risk reason).",
    },
    "ManufacturingDelayed": {
        "version": "1.0",
        "publisher": "ADS-07",
        "subscribers": ["ADS-10", "ADS-17"],
        "description": "Production running behind schedule.",
    },
    "CapacityExceeded": {
        "version": "1.0",
        "publisher": "ADS-07",
        "subscribers": ["ADS-15", "ADS-17"],
        "description": "Factory capacity cannot accommodate the requested run.",
    },
    "InspectionRequested": {
        "version": "1.0",
        "publisher": "ADS-07",
        "subscribers": ["ADS-14"],
        "description": "QA inspection triggered after ManufacturingCompleted.",
    },

    # ── Customer Service (ADS-08) ────────────────────────────────────────────
    "CustomerNotified": {
        "version": "1.0",
        "publisher": "ADS-08",
        "subscribers": [],
        "description": "Customer notification sent (email / push / SMS).",
    },
    "TicketOpened": {
        "version": "1.0",
        "publisher": "ADS-08",
        "subscribers": ["ADS-10"],
        "description": "New support ticket created.",
    },
    "TicketEscalated": {
        "version": "1.0",
        "publisher": "ADS-08",
        "subscribers": ["ADS-17"],
        "description": "Ticket SLA breached; escalated to CEO Agent.",
    },
    "ProductReturned": {
        "version": "1.0",
        "publisher": "ADS-08",
        "subscribers": ["ADS-14"],
        "description": "Customer initiated return; triggers QA inspection.",
    },

    # ── Finance (ADS-09) ─────────────────────────────────────────────────────
    "FinancialRecommendationReady": {
        "version": "1.0",
        "publisher": "ADS-09",
        "subscribers": ["ADS-17"],
        "description": "Finance Agent produced cost analysis for CEO review.",
    },
    "BudgetExceeded": {
        "version": "1.0",
        "publisher": "ADS-09",
        "subscribers": ["ADS-10", "ADS-17"],
        "description": "Procurement or shipping cost exceeds approved budget.",
    },
    "PaymentApproved": {
        "version": "1.0",
        "publisher": "ADS-09",
        "subscribers": ["ADS-05"],
        "description": "Finance Agent approved payment for a PO or shipment.",
    },

    # ── Risk (ADS-10) ────────────────────────────────────────────────────────
    "RiskDetected": {
        "version": "1.0",
        "publisher": "ADS-10",
        "subscribers": ["ADS-06", "ADS-15", "ADS-17"],
        "description": "Risk threshold crossed; mitigation required.",
    },
    "RiskMitigated": {
        "version": "1.0",
        "publisher": "ADS-10",
        "subscribers": ["ADS-17"],
        "description": "Previously detected risk resolved or mitigated.",
    },

    # ── CEO (ADS-17) ─────────────────────────────────────────────────────────
    "CEOApprovalGranted": {
        "version": "1.0",
        "publisher": "ADS-17",
        "subscribers": ["ADS-06"],
        "description": "CEO Agent approved a high-value or risk shipment. "
                       "Note: Transportation Agent subscribes to this, NOT OrderApproved.",
    },
    "CEOApprovalDenied": {
        "version": "1.0",
        "publisher": "ADS-17",
        "subscribers": ["ADS-01", "ADS-08"],
        "description": "CEO Agent denied approval; order or PO cancelled.",
    },

    # ── Pricing (ADS-11) ─────────────────────────────────────────────────────
    "PriceRecommendationGenerated": {
        "version": "1.0",
        "publisher": "ADS-11",
        "subscribers": ["ADS-17"],
        "description": "Pricing Agent produced a new price recommendation.",
    },
    "PriceApplied": {
        "version": "1.0",
        "publisher": "ADS-11",
        "subscribers": ["ADS-08"],
        "description": "Approved price applied to product catalogue.",
    },

    # ── Sustainability (ADS-13) ──────────────────────────────────────────────
    "SustainabilityReportGenerated": {
        "version": "1.0",
        "publisher": "ADS-13",
        "subscribers": ["ADS-18"],
        "description": "CO2 and sustainability metrics calculated for a shipment.",
    },

    # ── Quality (ADS-14) ─────────────────────────────────────────────────────
    "InspectionCompleted": {
        "version": "1.0",
        "publisher": "ADS-14",
        "subscribers": ["ADS-03", "ADS-05", "ADS-08"],
        "description": "QA inspection finished; result (pass/fail) in payload.",
    },
    "QualityAlertRaised": {
        "version": "1.0",
        "publisher": "ADS-14",
        "subscribers": ["ADS-10", "ADS-17"],
        "description": "Defect rate exceeded threshold; corrective action required.",
    },

    # ── Procurement Strategy (ADS-12) ────────────────────────────────────────
    "ContractExpiring": {
        "version": "1.0",
        "publisher": "SYSTEM_CELERY",
        "subscribers": ["ADS-12"],
        "description": "Celery task detected contract expiring within notice_period_days.",
    },
    "ContractRenewed": {
        "version": "1.0",
        "publisher": "ADS-12",
        "subscribers": ["ADS-09"],
        "description": "Contract renewed; Finance Agent notified for budget planning.",
    },

    # ── Promotions (Celery + ADS-02) ─────────────────────────────────────────
    "PromotionScheduled": {
        "version": "1.0",
        "publisher": "SYSTEM_CELERY",
        "subscribers": ["ADS-02"],
        "description": "Scheduled promotion activation imminent (1h notice).",
    },
    "PromotionStarted": {
        "version": "1.0",
        "publisher": "SYSTEM_CELERY",
        "subscribers": ["ADS-02", "ADS-11"],
        "description": "Promotion is now active.",
    },
    "PromotionEnded": {
        "version": "1.0",
        "publisher": "SYSTEM_CELERY",
        "subscribers": ["ADS-02", "ADS-11"],
        "description": "Promotion period ended; pricing/forecast agents should recalculate.",
    },
}

# Flat set for O(1) lookups used by EventRegistry
CANONICAL_EVENT_NAMES: frozenset[str] = frozenset(CANONICAL_EVENTS.keys())
