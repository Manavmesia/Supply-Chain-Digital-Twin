# AI Supply Chain Digital Twin

> An autonomous, event-driven multi-agent system that mirrors, predicts, and optimizes enterprise supply chain operations in real time using LangGraph, FastAPI, and PostgreSQL.

[![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agent_Orchestration-orange)](https://langchain-ai.github.io/langgraph/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?logo=postgresql)](https://www.postgresql.org)
[![RabbitMQ](https://img.shields.io/badge/RabbitMQ-Event_Bus-orange?logo=rabbitmq)](https://www.rabbitmq.com)
[![React](https://img.shields.io/badge/React-TypeScript-blue?logo=react)](https://react.dev)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker)](https://www.docker.com)

---

## Table of Contents

- [What Is This?](#what-is-this)
- [Architecture Overview](#architecture-overview)
- [Agent Catalogue](#agent-catalogue)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Documentation](#documentation)
- [Development Phases](#development-phases)
- [Key Design Principles](#key-design-principles)
- [API Reference](#api-reference)
- [Environment Variables](#environment-variables)
- [Contributing](#contributing)

---

## What Is This?

This project is a **production-grade AI Supply Chain Digital Twin** — a virtual, continuously updating replica of a real-world enterprise supply chain. Unlike traditional workflow systems, this platform is composed of **18 specialized AI agents** that autonomously cooperate, negotiate, and make decisions based on a shared world state.

### Core Capabilities

| Capability | Description |
|---|---|
| **Mirror** | Continuously reflects real supply chain state |
| **React** | Responds autonomously to disruption events |
| **Simulate** | Runs what-if scenarios without affecting production |
| **Explain** | Every AI decision is fully auditable and explainable |
| **Optimize** | Continuously improves routes, suppliers, inventory, pricing |
| **Coordinate** | 18 agents collaborate, negotiate, and reach consensus |

---

## Architecture Overview

```
                      React Dashboard (TypeScript)
                               │
                               ▼
                         FastAPI Gateway
                               │
                               ▼
                    LangGraph Orchestrator
                               │
   ┌───────────────────────────┼───────────────────────────┐
   │                           │                           │
Operational Layer       Business Layer          Coordination Layer
(8 Agents)              (6 Agents)              (4 Agents)
   │                           │                           │
   └───────────────────────────┼───────────────────────────┘
                               ▼
                  Shared State / Memory Layer
              PostgreSQL + Redis + pgvector
                               │
                               ▼
                    RabbitMQ Event Bus
                               │
                               ▼
                   Simulation Engine / Analytics
```

**Three-Layer Agent Model:**
- **Operational Layer** — Day-to-day execution (orders, inventory, shipping, manufacturing)
- **Business Intelligence Layer** — Analysis and optimization (finance, risk, pricing, sustainability)
- **Coordination Layer** — Governance and consensus (planning, negotiation, CEO approval, reporting)

---

## Agent Catalogue

### Operational Agents (8)

| ID | Agent | Responsibility |
|---|---|---|
| ADS-01 | Order Management | Validate, prioritize, and trigger order workflows |
| ADS-02 | Demand Forecast | Predict demand, detect anomalies and spikes |
| ADS-03 | Inventory | Prevent stock-outs, allocate and trigger replenishment |
| ADS-04 | Warehouse | Select optimal fulfillment warehouse |
| ADS-05 | Supplier | Evaluate and select best supplier per order |
| ADS-06 | Transportation | Route optimization, carrier selection, ETA |
| ADS-07 | Manufacturing | Production scheduling and capacity management |
| ADS-08 | Customer Service | Proactive notifications, issue resolution, escalation |

### Business Intelligence Agents (6)

| ID | Agent | Responsibility |
|---|---|---|
| ADS-09 | Finance | Budget evaluation, cost analysis, approval |
| ADS-10 | Risk | Multi-signal risk scoring and mitigation planning |
| ADS-11 | Pricing | Dynamic pricing based on demand and market data |
| ADS-12 | Procurement Strategy | Long-term sourcing strategy and supplier diversification |
| ADS-13 | Sustainability | Carbon footprint tracking and ESG compliance |
| ADS-14 | Quality Assurance | Defect detection, corrective actions, supplier quality |

### Coordination Agents (4)

| ID | Agent | Responsibility |
|---|---|---|
| ADS-15 | Planner | Enterprise execution planning and task orchestration |
| ADS-16 | Negotiation | Conflict resolution and multi-agent trade-off analysis |
| ADS-17 | CEO | Strategic governance, policy enforcement, final approvals |
| ADS-18 | Reporting | Executive dashboards, explainability reports, audit |

---

## Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | React + TypeScript + Vite | Dashboard and visualization |
| Charts | Apache ECharts | Supply chain maps, KPI charts |
| Backend API | FastAPI (Python 3.12) | REST API gateway |
| Agent Orchestration | LangGraph | Multi-agent workflow engine |
| LLM Providers | Groq / Anthropic / Gemini | Reasoning, negotiation, explanation |
| Relational Database | PostgreSQL 16 + pgvector | Source of truth + semantic memory |
| Cache / Checkpoints | Redis 7 | Active workflow state, LangGraph checkpoints |
| Event Bus | **RabbitMQ 3** | Async agent-to-agent communication |
| Background Jobs | Celery | Archival jobs, scheduled tasks |
| Observability | LangSmith + OpenTelemetry | LLM tracing + distributed tracing |
| Metrics | Prometheus + Grafana | System health and KPI dashboards |
| Authentication | JWT + RBAC | API security |
| Containers | Docker + Docker Compose | Local development |
| Production | Kubernetes | Autoscaling, managed cloud services |

> **Event Bus Decision:** RabbitMQ was chosen over Kafka because this system requires flexible per-agent routing (topic exchange + routing keys), low-to-medium throughput (< 10k events/sec), built-in Dead Letter Queue support, and simpler operational overhead for an initial enterprise deployment. See [`md_files/DECISION_Event_Bus.md`](md_files/DECISION_Event_Bus.md) for the full decision record.

---

## Prerequisites

Ensure the following are installed:

| Tool | Minimum Version | Installation |
|---|---|---|
| Docker Desktop | 4.x | https://www.docker.com/products/docker-desktop |
| Docker Compose | 2.x | Bundled with Docker Desktop |
| Python | 3.12+ | https://python.org |
| Node.js | 20+ | https://nodejs.org |
| Git | 2.x | https://git-scm.com |

Optional (for LLM features):
- Groq API Key, Anthropic API Key, or Google Gemini API Key
- LangSmith API Key (for LLM tracing)

---

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd multi-agent-system
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env with your API keys and database credentials
```

### 3. Start All Services

```bash
docker compose up --build
```

This starts:
- **FastAPI** at `http://localhost:8000`
- **React Dashboard** at `http://localhost:3000`
- **PostgreSQL** at `localhost:5432`
- **Redis** at `localhost:6379`
- **RabbitMQ** at `localhost:5672` (Management UI: `http://localhost:15672`)

### 4. Run Database Migrations

```bash
docker compose exec api alembic upgrade head
```

### 5. Seed Development Data

```bash
docker compose exec api python -m scripts.seed
```

### 6. Verify Installation

```bash
curl http://localhost:8000/health
# Expected: {"status": "ok", "version": "0.1.0", "db": "connected", "redis": "connected", "mq": "connected"}
```

---

## Project Structure

```
multi-agent-system/
├── backend/
│   ├── app/
│   │   ├── agents/                  # All 18 agent implementations
│   │   │   ├── operational/         # ADS-01 to ADS-08
│   │   │   ├── business/            # ADS-09 to ADS-14
│   │   │   └── coordination/        # ADS-15 to ADS-18
│   │   ├── api/                     # FastAPI routers
│   │   │   ├── orders.py
│   │   │   ├── inventory.py
│   │   │   ├── simulate.py
│   │   │   ├── reports.py
│   │   │   └── events.py
│   │   ├── core/                    # Shared infrastructure
│   │   │   ├── config.py            # Environment configuration
│   │   │   ├── database.py          # SQLAlchemy engine
│   │   │   ├── redis_client.py      # Redis connection
│   │   │   ├── rabbitmq.py          # RabbitMQ publisher/consumer
│   │   │   ├── security.py          # JWT + RBAC
│   │   │   └── logging.py           # Structured logging
│   │   ├── graph/                   # LangGraph orchestration
│   │   │   ├── state.py             # SupplyChainState TypedDict
│   │   │   ├── main_graph.py        # Main workflow graph
│   │   │   ├── routing.py           # Conditional routing functions
│   │   │   ├── retry.py             # Retry logic and circuit breakers
│   │   │   └── subgraphs/           # 5 subgraph implementations
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   ├── repositories/            # Repository pattern (data access)
│   │   ├── schemas/                 # Pydantic schemas and event models
│   │   └── services/                # Business services
│   ├── alembic/                     # Database migrations
│   │   ├── versions/
│   │   └── alembic.ini
│   ├── scripts/
│   │   ├── seed.py                  # Development seed data
│   │   └── dlq_processor.py         # Dead Letter Queue processor
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── simulation/
├── frontend/
│   ├── src/
│   │   ├── components/              # Dashboard modules (10)
│   │   ├── pages/
│   │   ├── services/                # API clients
│   │   └── hooks/
│   ├── package.json
│   └── vite.config.ts
├── md_files/                        # Architecture documentation
│   ├── AI_Supply_Chain_Digital_Twin_Complete_Architecture.md
│   ├── AI_Supply_Chain_Digital_Twin_Database_Design_Document.md
│   ├── AI_Supply_Chain_Digital_Twin_Development_Roadmap.md
│   ├── AI_Supply_Chain_Digital_Twin_LangGraph_Workflow_Document.md
│   ├── AI_Supply_Chain_Digital_Twin_System_Flow.md
│   ├── AI_Supply_Chain_Digital_Twin_System_Rules.md
│   ├── DECISION_Event_Bus.md        # Architectural decision: RabbitMQ
│   └── Agent Specification Document/
│       ├── AI_Supply_Chain_Digital_Twin_ADS_Volume_0.md
│       ├── AI_Supply_Chain_Digital_Twin_ADS_Volume_1_Operational_Agents.md
│       ├── AI_Supply_Chain_Digital_Twin_ADS_Volume_2_Business_Intelligence_Agents.md
│       └── AI_Supply_Chain_Digital_Twin_ADS_Volume_3_Coordination_Agents.md
├── sql/
│   ├── 01_schema.sql                # Full DDL — all tables, constraints, indexes
│   ├── 02_indexes.sql               # Composite, GIN, and vector indexes
│   └── 03_seed.sql                  # Reference/seed data
├── docker-compose.yml
├── .env.example
├── pyproject.toml
└── README.md
```

---

## Documentation

All architecture documentation lives in [`md_files/`](md_files/):

| Document | Description |
|---|---|
| [Complete Architecture](md_files/AI_Supply_Chain_Digital_Twin_Complete_Architecture.md) | Master blueprint — vision, agent catalogue, tech stack, guiding principles |
| [Database Design](md_files/AI_Supply_Chain_Digital_Twin_Database_Design_Document.md) | Full schema, relationships, indexes, event contracts |
| [LangGraph Workflow](md_files/AI_Supply_Chain_Digital_Twin_LangGraph_Workflow_Document.md) | Graph topology, state, routing, checkpoints, retry, subgraphs |
| [System Flow](md_files/AI_Supply_Chain_Digital_Twin_System_Flow.md) | End-to-end order and disruption flows |
| [System Rules](md_files/AI_Supply_Chain_Digital_Twin_System_Rules.md) | Mandatory design rules every agent must follow |
| [Development Roadmap](md_files/AI_Supply_Chain_Digital_Twin_Development_Roadmap.md) | 10-phase incremental build strategy |
| [ADS Volume 0](md_files/Agent%20Specification%20Document/AI_Supply_Chain_Digital_Twin_ADS_Volume_0.md) | Common agent standards and template |
| [ADS Volume 1 — Operational](md_files/Agent%20Specification%20Document/AI_Supply_Chain_Digital_Twin_ADS_Volume_1_Operational_Agents.md) | Specifications for ADS-01 to ADS-08 |
| [ADS Volume 2 — Business Intelligence](md_files/Agent%20Specification%20Document/AI_Supply_Chain_Digital_Twin_ADS_Volume_2_Business_Intelligence_Agents.md) | Specifications for ADS-09 to ADS-14 |
| [ADS Volume 3 — Coordination](md_files/Agent%20Specification%20Document/AI_Supply_Chain_Digital_Twin_ADS_Volume_3_Coordination_Agents.md) | Specifications for ADS-15 to ADS-18 |
| [Event Bus Decision](md_files/DECISION_Event_Bus.md) | Architectural decision record: RabbitMQ |

---

## Development Phases

| Phase | Goal | Agents Added |
|---|---|---|
| **Phase 0** | Planning & Design ✅ | — |
| **Phase 1** | Project Foundation | — |
| **Phase 2** | Shared Infrastructure (DB, Redis, RabbitMQ, Auth) | — |
| **Phase 3** | Core Supply Chain MVP | Order Mgmt, Inventory, Warehouse, Supplier, Transport, CEO |
| **Phase 4** | Business Intelligence | Finance, Risk, Demand Forecast, Reporting |
| **Phase 5** | Multi-Agent Coordination | Planner, Negotiation |
| **Phase 6** | Simulation Engine | All 18 agents in simulation mode |
| **Phase 7** | Dashboard & Visualization | — |
| **Phase 8** | Optimization & Performance | — |
| **Phase 9** | Production Deployment | — |

> **Rule:** The system must remain fully runnable at the end of every phase. Never build all 18 agents simultaneously.

---

## Key Design Principles

1. **One responsibility per agent** — Agents never duplicate each other's domain.
2. **Deterministic first** — Use algorithms for math; LLMs only for reasoning, negotiation, and explanations.
3. **Event-driven** — Every business action is triggered by an event; no synchronous coupling between agents.
4. **Explainable** — Every decision answers: What? Why? What data? What alternatives? What outcome?
5. **Auditable by default** — Every action produces an immutable audit log entry.
6. **State centralized** — PostgreSQL is the single source of truth; Redis for transient state only.
7. **Safe degradation** — Retry → fallback → escalate → human. System never silently fails.
8. **Correctness over speed** — Safety > Compliance > Policy > Data > Customer > Financial > Operational > Speed.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/token` | Issue JWT token |
| `POST` | `/orders` | Submit a new customer order |
| `GET` | `/orders/{id}` | Get order status and decision trail |
| `GET` | `/inventory` | Query current inventory levels |
| `GET` | `/suppliers` | List suppliers with health scores |
| `POST` | `/simulate` | Trigger a what-if simulation scenario |
| `GET` | `/simulation/{id}` | Get simulation results and KPIs |
| `POST` | `/events` | Inject a manual event into the system |
| `GET` | `/dashboard` | Aggregated dashboard data |
| `GET` | `/reports` | Generate or retrieve decision reports |
| `POST` | `/events/{id}/replay` | Replay a failed event from the DLQ |
| `POST` | `/workflows/{id}/approve` | Human approval for interrupted workflows |
| `POST` | `/workflows/{id}/reject` | Human rejection for interrupted workflows |
| `GET` | `/health` | System health check (DB, Redis, RabbitMQ) |
| `GET` | `/metrics` | Prometheus metrics endpoint |

Full interactive API documentation available at `http://localhost:8000/docs` (Swagger UI) when running locally.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the values:

```env
# Application
APP_ENV=development
APP_VERSION=0.1.0
SECRET_KEY=your-jwt-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/supply_chain
DATABASE_POOL_SIZE=10

# Redis
REDIS_URL=redis://redis:6379/0

# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@mq:5672/
RABBITMQ_DLQ_THRESHOLD=50

# LLM Providers (set at least one)
GROQ_API_KEY=gsk_...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# LLM Configuration
LLM_PROVIDER=groq
LLM_MODEL=llama-3.3-70b-versatile

# LangSmith (optional but recommended)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT=supply-chain-digital-twin

# Finance Thresholds
FINANCE_APPROVAL_THRESHOLD=50000
RISK_SCORE_THRESHOLD=70
SAFETY_STOCK_OVERRIDE_REQUIRES_CEO=true

# Performance
AGENT_RESPONSE_TIMEOUT_SECONDS=10
EVENT_PROCESSING_TIMEOUT_SECONDS=30
```

---

## Contributing

### Branch Strategy

| Branch | Purpose |
|---|---|
| `main` | Production-ready code only |
| `develop` | Integration branch |
| `feature/phase-N-description` | Feature work per phase |
| `fix/description` | Bug fixes |

### Development Workflow

```bash
# 1. Create a feature branch
git checkout -b feature/phase-3-inventory-agent

# 2. Install dependencies
pip install -e ".[dev]"

# 3. Run pre-commit hooks
pre-commit install
pre-commit run --all-files

# 4. Run tests
pytest tests/ -v

# 5. Commit with conventional commits
git commit -m "feat(inventory): implement ADS-03 stock allocation logic"
```

### Definition of Done (Per Story)

Before merging any pull request:
- [ ] Code reviewed by at least one other developer
- [ ] Unit tests written and passing
- [ ] Integration tests updated if workflow changed
- [ ] API documentation updated
- [ ] Structured logging added for all important actions
- [ ] Audit log entries produced for all agent decisions
- [ ] Error handling covers all documented failure scenarios
- [ ] Existing functionality still works (no regressions)
- [ ] Database migrations run cleanly

### Commit Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(agent):    New agent capability
fix(inventory): Bug fix in stock calculation
refactor(graph): Restructure LangGraph routing
test(supplier): Add unit tests for blacklist logic
docs(readme):   Update setup instructions
chore(deps):    Update dependencies
```

---

## Business KPIs

| KPI | Target |
|---|---|
| Fill Rate | > 98% |
| Inventory Turnover | Optimized per product category |
| Order Cycle Time | < 24 hours (standard) |
| Perfect Order Rate | > 95% |
| On-Time Delivery | > 97% |
| Customer Satisfaction | > 4.5 / 5.0 |

## Technical SLAs

| Metric | Target |
|---|---|
| Agent response time | < 2 seconds (excluding LLM latency) |
| Event processing latency | < 5 seconds |
| Dashboard refresh | < 2 seconds |
| API availability | > 99.9% |
| LLM call timeout | 30 seconds (with fallback model) |

---

*Built with LangGraph · FastAPI · PostgreSQL · RabbitMQ · React*
