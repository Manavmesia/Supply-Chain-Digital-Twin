# AI Supply Chain Digital Twin

# Database Design Document (DDD)

> **Version:** 1.0\
> **Database:** PostgreSQL + Redis + pgvector\
> **Architecture:** Event-Driven + LangGraph Shared State

------------------------------------------------------------------------

# 1. Purpose

This document defines the logical database architecture for the AI
Supply Chain Digital Twin. It provides the schema design, relationships,
indexing strategy, constraints, and event contracts required to support
an enterprise-scale multi-agent system.

------------------------------------------------------------------------

# 2. Database Architecture

                        +----------------------+
                        |      FastAPI         |
                        +----------+-----------+
                                   |
                         LangGraph Orchestrator
                                   |
          +------------------------+------------------------+
          |                        |                        |
     PostgreSQL               Redis Cache             Object Storage
    (Relational DB)        (State/Checkpoints)      (Files/Documents)
          |
          +-----------------------------+
          |                             |
       pgvector                    Event Store
    (Embeddings)             (Append-only Events)

------------------------------------------------------------------------

# 3. Core Domains

-   Customers
-   Products
-   Orders
-   Inventory
-   Warehouses
-   Suppliers
-   Manufacturing
-   Shipments
-   Finance
-   Risk
-   Sustainability
-   Quality Assurance
-   Agent Runtime
-   Events
-   Audit Logs

------------------------------------------------------------------------

# 4. High-Level ER Diagram

``` text
Customer
   │ 1
   │
   ├──────────────< Orders >──────────────< Order Items >────────── Product
   │                    │                                         │
   │                    │                                         │
   │                    ├──────────── Shipment                     │
   │                    │                                         │
   │                    ├──────────── Finance                      │
   │                    └──────────── Risk                         │
   │
Warehouse >──────── Inventory >──────── Product
        │
        └──────── Manufacturing

Supplier >──────── Supplier_Product >──────── Product

Agent_Runtime ─────< Events
Agent_Runtime ─────< Audit_Logs
```

------------------------------------------------------------------------

# 5. Table Definitions

## customers

  Column        Type        Constraint
  ------------- ----------- ------------
  customer_id   UUID        PK
  name          TEXT        NOT NULL
  email         TEXT        UNIQUE
  phone         TEXT        
  address       TEXT        
  created_at    TIMESTAMP   NOT NULL

------------------------------------------------------------------------

## products

  Column       Type      Constraint
  ------------ --------- ------------
  product_id   UUID      PK
  sku          TEXT      UNIQUE
  name         TEXT      NOT NULL
  category     TEXT      
  unit_price   NUMERIC   
  active       BOOLEAN   

------------------------------------------------------------------------

## orders

  Column         Type
  -------------- -----------
  order_id       UUID PK
  customer_id    UUID FK
  status         TEXT
  priority       TEXT
  total_amount   NUMERIC
  created_at     TIMESTAMP

------------------------------------------------------------------------

## order_items

-   order_item_id (PK)
-   order_id (FK)
-   product_id (FK)
-   quantity
-   unit_price

------------------------------------------------------------------------

## inventory

-   inventory_id (PK)
-   product_id (FK)
-   warehouse_id (FK)
-   available_qty
-   reserved_qty
-   safety_stock

------------------------------------------------------------------------

## warehouses

-   warehouse_id (PK)
-   name
-   location
-   capacity
-   status

------------------------------------------------------------------------

## suppliers

-   supplier_id (PK)
-   name
-   rating
-   lead_time_days
-   status

------------------------------------------------------------------------

## supplier_products (Bridge Table)

-   supplier_id (FK)
-   product_id (FK)
-   contract_price
-   minimum_order_qty

Composite PK:

    supplier_id + product_id

------------------------------------------------------------------------

## manufacturing_orders

-   mo_id
-   product_id
-   planned_qty
-   completed_qty
-   status

------------------------------------------------------------------------

## shipments

-   shipment_id
-   order_id
-   carrier
-   route
-   eta
-   status

------------------------------------------------------------------------

## finance_transactions

-   txn_id
-   order_id
-   transaction_type
-   amount
-   currency
-   created_at

------------------------------------------------------------------------

## risk_assessments

-   risk_id
-   entity_type
-   entity_id
-   risk_score
-   mitigation_status

------------------------------------------------------------------------

## sustainability_metrics

-   metric_id
-   shipment_id
-   co2_emission
-   fuel_consumption
-   sustainability_score

------------------------------------------------------------------------

## quality_inspections

-   inspection_id
-   product_id
-   inspection_result
-   defect_count

------------------------------------------------------------------------

## agent_runtime

-   agent_id
-   agent_name
-   status
-   last_heartbeat
-   current_workflow

------------------------------------------------------------------------

## events

-   event_id
-   correlation_id
-   event_type
-   source_agent
-   target_agent
-   payload (JSONB)
-   metadata (JSONB)
-   timestamp

------------------------------------------------------------------------

## audit_logs

-   log_id
-   agent_id
-   action
-   entity
-   created_at

------------------------------------------------------------------------

# 6. Relationships

  Parent          Child                    Type
  --------------- ------------------------ ------
  customers       orders                   1:N
  orders          order_items              1:N
  products        order_items              1:N
  warehouses      inventory                1:N
  products        inventory                1:N
  suppliers       supplier_products        1:N
  products        supplier_products        1:N
  orders          shipments                1:1
  orders          finance_transactions     1:N
  products        manufacturing_orders     1:N
  products        quality_inspections      1:N
  shipments       sustainability_metrics   1:N
  agent_runtime   events                   1:N
  agent_runtime   audit_logs               1:N

------------------------------------------------------------------------

# 7. Index Design

## Primary Indexes

-   All Primary Keys

## Unique Indexes

-   products.sku
-   customers.email
-   events.correlation_id

## Composite Indexes

``` text
orders(status, created_at)

inventory(product_id, warehouse_id)

shipments(status, eta)

finance_transactions(order_id, transaction_type)

risk_assessments(entity_type, entity_id)

audit_logs(agent_id, created_at)
```

## JSONB GIN Indexes

``` sql
CREATE INDEX idx_events_payload
ON events
USING GIN(payload);
```

## Vector Index

``` text
HNSW / IVFFlat

embedding VECTOR(768)
```

------------------------------------------------------------------------

# 8. Constraints

## NOT NULL

-   IDs
-   Foreign Keys
-   Timestamps

## CHECK

``` sql
quantity >= 0

available_qty >= 0

reserved_qty >= 0

risk_score BETWEEN 0 AND 100

rating BETWEEN 1 AND 5
```

## Foreign Keys

-   ON UPDATE CASCADE
-   ON DELETE RESTRICT (business entities)
-   ON DELETE CASCADE (bridge tables)

------------------------------------------------------------------------

# 9. Event Schema

``` json
{
  "event_id": "uuid",
  "correlation_id": "uuid",
  "event_type": "OrderCreated",
  "source_agent": "OrderManagement",
  "target_agent": "Inventory",
  "priority": "HIGH",
  "timestamp": "2026-01-01T12:00:00Z",
  "payload": {},
  "metadata": {}
}
```

------------------------------------------------------------------------

# 10. Standard Event Types

## Operational

-   OrderCreated
-   InventoryAllocated
-   InventoryLow
-   PurchaseOrderCreated
-   ManufacturingStarted
-   ShipmentDispatched
-   ShipmentDelivered

## Business

-   FinancialApprovalGranted
-   RiskDetected
-   SustainabilityCalculated
-   QualityInspectionCompleted

## Coordination

-   PlanGenerated
-   NegotiationCompleted
-   CEOApprovalGranted
-   ReportGenerated

## System

-   AgentFailure
-   RetryRequested
-   WorkflowCompleted

------------------------------------------------------------------------

# 11. LangGraph Shared State

``` yaml
workflow_id:
current_node:
active_agents:
business_context:
shared_variables:
event_history:
checkpoint:
```

------------------------------------------------------------------------

# 12. Scalability Strategy

-   Monthly partitioning for `events`
-   Read replicas for analytics
-   Redis caching
-   pgvector for semantic memory
-   Horizontal agent scaling
-   Connection pooling
-   Background archival jobs

------------------------------------------------------------------------

# 13. Security

-   JWT authentication
-   Role-Based Access Control
-   Row-Level Security
-   Immutable audit logs
-   Encrypted secrets
-   Database backups
-   Least-privilege permissions

------------------------------------------------------------------------

# 14. Future Enhancements

-   Full SQL DDL scripts
-   Migration scripts
-   Materialized views
-   Stored procedures
-   Draw.io ER diagrams
-   Mermaid ER diagrams
-   Event versioning
-   Data retention policies
-   Disaster recovery plan
-   Performance tuning guide
