# Architectural Decision Record — Event Bus Selection

> **ADR-001**  
> **Status:** Accepted  
> **Date:** 2026-07-28  
> **Authors:** Principal Enterprise Architect  
> **Resolves:** AUD-15, AUD-16 (Architecture Audit Report)

---

## Context

The AI Supply Chain Digital Twin requires an asynchronous event bus for agent-to-agent communication. The original documentation listed two options ambiguously:

- **Complete Architecture Document §23** — lists only RabbitMQ
- **System Flow Document §Tech Stack** — lists "RabbitMQ (or Kafka)"

A formal decision is required before Phase 2 (Shared Infrastructure) implementation begins.

---

## Options Evaluated

### Option A — RabbitMQ 3.x (AMQP)

**Strengths:**
- Built-in topic exchanges with per-agent routing key binding — perfect for the documented per-agent queue topology
- Native Dead Letter Queue (DLQ) support — directly satisfies System Rules §4 and AUD-26
- Built-in message TTL, priority queues, and delayed message plugin
- Management UI out of the box (useful during development and operations)
- Lower operational overhead — single binary, no ZooKeeper/KRaft dependency
- Simpler to run in Docker Compose for local development
- Well-suited for **request-reply patterns** (Planner → Agent task assignments)
- Throughput: up to ~50k messages/sec per node — sufficient for this system's event volume
- Native support for `aio-pika` (async Python client)

**Weaknesses:**
- Not designed for log-based event sourcing or high-throughput stream processing
- Message replay requires dedicated DLQ replay logic (already planned as US-14)
- Less suitable if event volume exceeds 100k/sec (not expected at launch or scale)

---

### Option B — Apache Kafka

**Strengths:**
- Designed for high-throughput event streaming (millions of events/sec)
- Log-based storage enables native event replay and time-travel
- Strong ecosystem for stream processing (Kafka Streams, Flink)
- Better fit for future IoT sensor integration (Future Enhancements §22)

**Weaknesses:**
- Operationally complex: requires KRaft (or ZooKeeper) coordination
- No native per-agent routing — requires consumer group management and topic proliferation
- No built-in DLQ — requires custom implementation or additional tooling (Kafka Dead Letter Topics)
- No native request-reply pattern — unsuitable for Planner Agent task dispatch
- Higher memory/CPU footprint in Docker Compose development environment
- Overkill for the projected event volume of this system (< 10k events/sec at full 18-agent load)

---

## Decision

**✅ Selected: RabbitMQ 3.x with `aio-pika` (async Python)**

### Justification

| Requirement | RabbitMQ | Kafka | Winner |
|---|---|---|---|
| Per-agent message routing | Topic Exchange + Routing Keys | Consumer Groups + Topics | RabbitMQ |
| Dead Letter Queue | Native support | Manual implementation | RabbitMQ |
| Request-reply (Planner dispatch) | Native AMQP pattern | Workaround required | RabbitMQ |
| Operational complexity (dev) | Low (single container) | High (KRaft required) | RabbitMQ |
| Expected throughput (< 10k/sec) | Sufficient | Overkill | RabbitMQ |
| Event replay (DLQ) | Via replay endpoint (US-14) | Native log replay | Kafka |
| Future IoT integration | Plugin-based | Better native fit | Kafka |

RabbitMQ wins on **6 of 7** criteria relevant to the current system scope.

### Future Migration Path

If the system evolves to require high-throughput IoT sensor streams or native event sourcing (listed in Future Enhancements), an outbox pattern can be added on top of RabbitMQ or a hybrid Kafka cluster can be introduced for the sensor ingestion path only — without redesigning the agent communication topology.

---

## Background Job Worker Decision (Resolves AUD-16)

**✅ Selected: Celery with Redis as broker**

**Justification:**
- Celery is already proven with FastAPI
- Redis is already in the stack (no additional dependency)
- Tasks: DB archival, simulation cleanup, scheduled forecasts, DLQ monitoring
- Dramatiq is a valid alternative but offers fewer ecosystem integrations and less community support
- Celery Beat handles scheduled tasks (cron-equivalent) without an additional scheduler service

---

## Topology

```
Exchange: supply_chain.events (topic)
Exchange: supply_chain.dlq   (fanout, Dead Letter)

Agent Queues (examples):
  inventory.orders      → binds to routing key "order.*"
  supplier.procurement  → binds to routing key "procurement.*"
  risk.alerts           → binds to routing key "risk.*"
  ceo.approvals         → binds to routing key "approval.*"

Dead Letter Queue:
  supply_chain.dlq.queue → receives all messages that exceed max retries
```

---

## Implementation Notes

- Use `aio-pika` for async Python publisher and consumer
- Use `pydantic` for schema validation before every publish (US-13)
- DLQ consumer logs to `audit_logs` with `action = 'EVENT_DLQ'`
- Manual replay via `POST /events/{event_id}/replay` (US-14)
- All topology declared programmatically on startup (idempotent)
- RabbitMQ Management UI: `http://localhost:15672` (dev: guest/guest)

---

## References

- [AUD-15 — Event Bus Ambiguity](../enterprise_audit_and_epics.md)
- [AUD-16 — Background Worker Ambiguity](../enterprise_audit_and_epics.md)
- [US-12 — RabbitMQ Topology Setup](../enterprise_audit_and_epics.md)
- [US-13 — Event Publisher & Schema Validation](../enterprise_audit_and_epics.md)
- [US-14 — DLQ Processing Workflow](../enterprise_audit_and_epics.md)
