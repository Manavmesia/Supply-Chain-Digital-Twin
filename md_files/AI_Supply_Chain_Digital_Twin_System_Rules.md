# AI Supply Chain Digital Twin

## System Rules & Design Principles (v1.0)

This document defines the mandatory rules governing the behaviour of the
AI Supply Chain Digital Twin. These rules ensure that every agent
behaves predictably, safely, consistently, and in a way that reflects
real-world enterprise operations.

------------------------------------------------------------------------

# 1. Core Principles

1.  The system is event-driven, not request-driven.
2.  Every agent has exactly one primary responsibility.
3.  No agent may modify another agent's internal state directly.
4.  All shared business state must be stored in the centralized state
    layer.
5.  Every important decision must be explainable.
6.  Every action must be traceable through audit logs.
7.  The system must prefer deterministic computation over LLM reasoning
    whenever possible.
8.  Human approval must remain possible for critical business decisions.

------------------------------------------------------------------------

# 2. Agent Rules

## Responsibility

-   Each agent owns one business domain.
-   Agents must never duplicate another agent's responsibility.
-   Agents may recommend actions but cannot execute actions outside
    their domain.

## Communication

-   Agents communicate only through structured events/messages.
-   Agents must never communicate using unstructured natural language
    unless generating explanations for humans.
-   Every message must contain:
    -   Sender
    -   Receiver
    -   Event type
    -   Correlation ID
    -   Timestamp
    -   Payload
    -   Priority

## Decision Making

-   Every decision must include:
    -   Reason
    -   Confidence score
    -   Data sources used
    -   Alternatives considered
    -   Expected business impact

------------------------------------------------------------------------

# 3. State Management Rules

-   PostgreSQL is the source of truth.
-   Redis stores only temporary state.
-   Historical records must never be overwritten.
-   Every state change must be versioned.
-   Agents must always read the latest committed state before making
    decisions.

------------------------------------------------------------------------

# 4. Event Rules

Every business action is triggered by an event.

Examples:

-   OrderCreated
-   InventoryLow
-   ShipmentDelayed
-   SupplierUnavailable
-   WarehouseOverloaded
-   DemandSpike
-   WeatherAlert

Rules:

-   Events are immutable.
-   Events are timestamped.
-   Events are idempotent.
-   Events must support retries.
-   Failed events move to a Dead Letter Queue (DLQ).

------------------------------------------------------------------------

# 5. LLM Usage Rules

LLMs MAY be used for:

-   Planning
-   Negotiation
-   Strategy comparison
-   Summarization
-   Explanations
-   Report generation

LLMs MUST NOT be used for:

-   Arithmetic
-   SQL calculations
-   Inventory math
-   Routing algorithms
-   Financial calculations
-   Validation of critical constraints

------------------------------------------------------------------------

# 6. Business Rules

Inventory

-   Stock must never become negative.
-   Safety stock cannot be violated without executive approval.
-   Inventory transfers require warehouse validation.

Suppliers

-   Every supplier has a reliability score.
-   Procurement should prefer higher reliability when costs are
    comparable.
-   Blacklisted suppliers cannot receive purchase orders.

Transportation

-   The cheapest route is not always the preferred route.
-   Time-critical shipments take priority over cost optimisation.

Finance

-   Budget constraints must always be evaluated before procurement.
-   High-cost emergency actions require executive approval.

------------------------------------------------------------------------

# 7. Negotiation Rules

When recommendations conflict:

1.  Planner gathers proposals.
2.  Negotiation Agent evaluates trade-offs.
3.  CEO Agent selects a strategy.
4.  Decision is logged with rationale.

No operational agent may override the CEO decision.

------------------------------------------------------------------------

# 8. Failure Handling

If an agent fails:

-   Retry using exponential backoff.
-   Log the failure.
-   Publish a failure event.
-   Notify dependent agents.
-   Escalate after retry threshold.

The system must continue operating wherever possible.

------------------------------------------------------------------------

# 9. Security Rules

-   Authenticate every API request.
-   Authorize every business action.
-   Encrypt sensitive information.
-   Never expose secrets to LLMs.
-   Validate all external input.
-   Maintain immutable audit logs.

------------------------------------------------------------------------

# 10. Observability Rules

Record for every workflow:

-   Processing time
-   Agent latency
-   LLM tokens
-   Estimated cost
-   Success/failure
-   Retry count
-   Decision confidence

------------------------------------------------------------------------

# 11. Explainability Rules

Every major decision must answer:

-   What happened?
-   Why was this decision chosen?
-   Which data was used?
-   Which alternatives were rejected?
-   What is the expected outcome?

------------------------------------------------------------------------

# 12. Simulation Rules

Simulation runs:

-   Must never modify production data.
-   Must run in isolated state.
-   Must support replay.
-   Must produce comparable KPIs.

------------------------------------------------------------------------

# 13. Performance Rules

Target metrics:

-   Agent response \< 2 seconds (excluding LLM latency)
-   Event processing \< 5 seconds
-   Dashboard refresh \< 2 seconds
-   API availability \> 99.9%
-   Workflow completion within defined SLA

------------------------------------------------------------------------

# 14. Coding Rules

-   Strong typing throughout the codebase.
-   Modular architecture.
-   Dependency injection where practical.
-   Comprehensive logging.
-   Unit tests for core business logic.
-   Integration tests for workflows.
-   Configuration via environment variables only.

------------------------------------------------------------------------

# 15. Data Integrity Rules

-   No duplicate order IDs.
-   No orphan records.
-   Referential integrity enforced.
-   Soft delete preferred for business entities.
-   Every transaction must be atomic.

------------------------------------------------------------------------

# 16. Human-in-the-Loop Rules

Require approval for:

-   Large procurement decisions.
-   Budget overrides.
-   Supplier blacklist changes.
-   Emergency policy overrides.
-   Manual inventory corrections.

------------------------------------------------------------------------

# 17. System Principles

1.  Correctness over speed.
2.  Explainability over opacity.
3.  Reliability over cleverness.
4.  Deterministic logic before AI reasoning.
5.  Event-driven architecture over synchronous coupling.
6.  Auditability by default.
7.  Graceful degradation under failure.
8.  Scalable, modular, and extensible design.
