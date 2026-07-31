# AI Supply Chain Digital Twin

# LangGraph Workflow Design Document (LWD)

> **Framework:** LangGraph\
> **Architecture:** Event-Driven Multi-Agent System\
> **Purpose:** Define graph topology, state, routing, checkpoints,
> retries, and subgraphs.

------------------------------------------------------------------------

# 1. System Overview

``` text
              User/API
                 │
             FastAPI Router
                 │
          LangGraph Entry Node
                 │
      ┌──────────┴──────────┐
      │                     │
 Operational Layer    Business Layer
      │                     │
      └──────────┬──────────┘
                 │
         Coordination Layer
                 │
          Response Generator
```

------------------------------------------------------------------------

# 2. Global State Object

``` python
class SupplyChainState(TypedDict):
    workflow_id: str
    correlation_id: str
    current_node: str
    active_agents: list[str]
    event_history: list[dict]
    customer: dict
    order: dict
    inventory: dict
    shipment: dict
    supplier: dict
    finance: dict
    risk: dict
    forecast: dict
    quality: dict
    sustainability: dict
    decisions: list[dict]
    retries: dict
    errors: list[dict]
    messages: list
```

------------------------------------------------------------------------

# 3. Main Workflow

``` text
START
 │
 ▼
Receive Event
 │
Validate Request
 │
Load Shared State
 │
Planner
 │
├── Order Management
├── Demand Forecast
├── Inventory
├── Warehouse
├── Supplier
├── Manufacturing
├── Transportation
├── Customer Service
│
├── Finance
├── Risk
├── Pricing
├── Procurement
├── Sustainability
└── Quality
 │
Negotiation
 │
CEO Approval
 │
Reporting
 │
Persist State
 │
END
```

------------------------------------------------------------------------

# 4. Node Definitions

## Entry Nodes

-   Receive Event
-   Validate Request
-   Load Shared State

## Operational Nodes

-   Order Management
-   Demand Forecast
-   Inventory
-   Warehouse
-   Supplier
-   Manufacturing
-   Transportation
-   Customer Service

## Business Nodes

-   Finance
-   Risk
-   Pricing
-   Procurement Strategy
-   Sustainability
-   Quality Assurance

## Coordination Nodes

-   Planner
-   Negotiation
-   CEO
-   Reporting

## Exit Nodes

-   Persist State
-   END

------------------------------------------------------------------------

# 5. Edge Definitions

  From                To                  Condition
  ------------------- ------------------- -------------------
  START               Receive Event       Always
  Receive Event       Validate Request    Event received
  Validate Request    Load Shared State   Valid
  Load Shared State   Planner             State loaded
  Planner             Operational Nodes   Task required
  Operational Nodes   Business Nodes      Analysis needed
  Business Nodes      Negotiation         Conflicts exist
  Business Nodes      CEO                 No conflicts
  Negotiation         CEO                 Agreement reached
  CEO                 Reporting           Approved
  Reporting           Persist State       Report complete
  Persist State       END                 Success

------------------------------------------------------------------------

# 6. Routing Conditions

## Order

    if order.valid:
        OrderManagement
    else:
        RejectWorkflow

## Inventory

    if inventory.available:
        Warehouse
    else:
        Supplier

## Manufacturing

    if stock_missing:
        Manufacturing

## Transportation

    if shipment_ready:
        Transportation

## Finance

    if order_value > threshold:
        Finance

## Risk

    if risk_score > 70:
        Risk

## Negotiation

    if recommendations_conflict:
        Negotiation

## CEO

    if strategic_decision:
        CEO

------------------------------------------------------------------------

# 7. Retry Logic

  Failure                 Retries   Strategy
  ----------------------- --------- ---------------------------
  API timeout             3         Exponential backoff
  Database unavailable    5         Retry + circuit breaker
  LLM timeout             2         Retry with fallback model
  Invalid tool response   2         Revalidate
  Agent unavailable       3         Requeue task
  Event publish failed    5         Persistent queue

Retry metadata:

``` yaml
retry_count:
last_retry:
backoff:
failure_reason:
```

------------------------------------------------------------------------

# 8. Checkpoint Strategy

Checkpoint after:

-   Request validation
-   Planner
-   Every operational agent
-   Every business agent
-   Negotiation
-   CEO
-   Reporting
-   Persist State

Checkpoint data:

``` yaml
workflow_id:
node:
state_snapshot:
timestamp:
version:
```

Storage:

-   Redis (active)
-   PostgreSQL (persistent)

------------------------------------------------------------------------

# 9. Subgraphs

## Order Processing

``` text
Order
 │
Validate
 │
Inventory
 │
Warehouse
 │
Shipment
```

## Procurement

``` text
Supplier
 │
Finance
 │
Risk
 │
Purchase Order
```

## Manufacturing

``` text
Forecast
 │
Manufacturing
 │
Quality
```

## Delivery

``` text
Transportation
 │
Customer Service
```

## Executive

``` text
Planner
 │
Negotiation
 │
CEO
 │
Reporting
```

------------------------------------------------------------------------

# 10. Interrupt Points

Human approval required for:

-   High-value purchase
-   Supplier override
-   Strategic pricing
-   Executive policy conflict

------------------------------------------------------------------------

# 11. Error Handling

``` text
Node Failure
     │
Retry
     │
Fallback Tool
     │
Escalate Agent
     │
CEO
     │
Human
```

------------------------------------------------------------------------

# 12. Parallel Execution

These nodes may execute concurrently:

-   Finance
-   Risk
-   Pricing
-   Sustainability
-   Quality

Planner waits until all complete before continuing.

------------------------------------------------------------------------

# 13. State Transitions

``` text
Received
  │
Validated
  │
Planned
  │
Operational
  │
Business
  │
Negotiated
  │
Approved
  │
Reported
  │
Completed
```

------------------------------------------------------------------------

# 14. Graph Policies

-   Immutable workflow IDs
-   Idempotent node execution
-   Event sourcing for recovery
-   Explainable decisions
-   No shared mutable agent memory
-   Deterministic routing where possible

------------------------------------------------------------------------

# 15. Observability

Capture:

-   Node latency
-   Token usage
-   Retry counts
-   Tool calls
-   Event throughput
-   Workflow duration
-   Failure rate

------------------------------------------------------------------------

# 16. Future Enhancements

-   Dynamic graph composition
-   Multi-tenant workflows
-   Human-in-the-loop nodes
-   Streaming execution
-   Distributed graph execution
-   Adaptive routing
-   Graph versioning
-   A/B workflow testing
