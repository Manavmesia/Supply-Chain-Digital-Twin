# AI Supply Chain Digital Twin

> An enterprise-grade, autonomous, event-driven multi-agent system that mirrors, predicts, and optimizes global supply chain operations in real time using **LangGraph**, **FastAPI**, **PostgreSQL**, and **React (TypeScript)**.

[![Python](https://img.shields.io/badge/Python-3.12%2B%20%7C%203.13-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-18_Agent_Mesh-orange)](https://langchain-ai.github.io/langgraph/)
[![React](https://img.shields.io/badge/React-19_TypeScript-61dafb?logo=react)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-8.x-646CFF?logo=vite)](https://vitejs.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-blue?logo=postgresql)](https://www.postgresql.org)
[![RabbitMQ](https://img.shields.io/badge/RabbitMQ-Event_Bus-orange?logo=rabbitmq)](https://www.rabbitmq.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://www.docker.com)

---

## Table of Contents

- [Overview & Capabilities](#overview--capabilities)
- [System Architecture](#system-architecture)
- [18-Agent Catalogue](#18-agent-catalogue)
- [System Requirements](#system-requirements)
- [Environment Configuration](#environment-configuration)
- [Project Setup & Installation](#project-setup--installation)
  - [Option A: Local Development Setup (Quickest, No Docker Needed)](#option-a-local-development-setup-quickest-no-docker-needed)
  - [Option B: Containerized Setup (Docker Compose)](#option-b-containerized-setup-docker-compose)
- [Running the Application](#running-the-application)
- [Default Demo Credentials](#default-demo-credentials)
- [Database Migrations & Data Seeding](#database-migrations--data-seeding)
- [Running the Test Suites](#running-the-test-suites)
- [Core API Reference](#core-api-reference)
- [Troubleshooting & Common FAQs](#troubleshooting--common-faqs)
- [License](#license)

---

## Overview & Capabilities

The **AI Supply Chain Digital Twin** is an autonomous multi-agent simulation and operations platform. Unlike rigid rule-based systems or monolithic LLM wrappers, it deploys **18 specialized AI agents** organized across three functional tiers to collaboratively govern procurement, warehouse inventory, freight transportation, dynamic pricing, risk mitigation, and executive decision-making.

### Key Capabilities

* **Autonomous Fulfillment & Routing:** Validates orders, allocates warehouse inventory across multi-echelon hubs, selects optimal freight corridors, and applies dynamic volume discounts.
* **Closed-Loop Disruption Remediation:** Ingests live operational disruption events (carrier delays, supplier outages, quality failures, safety stock breaches) and initiates autonomous multi-agent healing protocols.
* **Decentralized Multi-Agent Consensus:** Employs an agent negotiation protocol and shared blackboard memory to reconcile conflicting domain goals (e.g., Sustainability vs. Expedited Air Freight vs. Gross Margins).
* **Human-in-the-Loop Governance:** Enforces strict executive threshold policies (e.g., CEO approval sign-off for orders exceeding $50,000 or significant CapEx exceptions).
* **What-If Scenario Simulation:** Simulates extreme stress scenarios (e.g., 2.5× demand surges, 100% lot quarantines) without contaminating production databases.

---

## System Architecture

```
                    React 19 + TypeScript Control Tower (Vite)
                     [ http://localhost:5173  /  Port 5173 ]
                                        │
                                        ▼ (REST API / JWT Auth)
                        FastAPI Production Gateway
                     [ http://localhost:8000  /  Port 8000 ]
                                        │
                                        ▼
                       LangGraph 18-Agent State Graph
                                        │
   ┌────────────────────────────────────┼────────────────────────────────────┐
   │                                    │                                    │
   ▼                                    ▼                                    ▼
Operational Layer              Business Intelligence Layer           Coordination Layer
(8 Specialist Agents)          (6 Optimization Agents)               (4 Governance Agents)
   │                                    │                                    │
   └────────────────────────────────────┼────────────────────────────────────┘
                                        │
             ┌──────────────────────────┴──────────────────────────┐
             ▼                                                     ▼
Primary State & Vector Memory                      Event Bus & Async Messaging
PostgreSQL 16 (pgvector) / SQLite WAL              RabbitMQ 3 (Topic Exchanges & DLQ)
+ Redis 7 (Checkpoints & Caching)
```

---

## 18-Agent Catalogue

| Layer | Agent ID | Agent Role | Core Domain & Responsibilities |
| :--- | :--- | :--- | :--- |
| **Operational** | **ADS-01** | Order Management | Validates line items, enforces priority queues, ingests orders |
| **Operational** | **ADS-03** | Inventory Management | Stock reservation, multi-echelon allocation, deficit detection |
| **Operational** | **ADS-04** | Warehouse Operations | Warehouse facility selection, staging schedules, fulfillment rules |
| **Operational** | **ADS-05** | Supplier & Sourcing | Supplier reliability scoring, automated replenishment PO issuance |
| **Operational** | **ADS-06** | Transportation Agent | Carrier TMS selection, freight corridor routing, transit ETA |
| **Operational** | **ADS-07** | Manufacturing Agent | Assembly line scheduling, emergency remanufacturing batches |
| **Operational** | **ADS-08** | Customer Service | Client SLA monitoring, proactive notifications, issue escalation |
| **Business** | **ADS-02** | Demand Forecast | Statistical predictive modeling, market surge detection |
| **Business** | **ADS-09** | Finance & Margins | Gross margin calculation, budget thresholds, CapEx checks |
| **Business** | **ADS-10** | Supply Chain Risk | Disruption risk scoring, geopolitical hazard assessment |
| **Business** | **ADS-11** | Dynamic Pricing | Elasticity-based volume discounts, promotional pricing matrices |
| **Business** | **ADS-12** | Procurement Strategy | Strategic vendor diversification, contract terms compliance |
| **Business** | **ADS-13** | Sustainability & ESG | Carbon footprint telemetry (kg CO₂e), clean corridor incentives |
| **Business** | **ADS-14** | Quality Assurance | Batch inspection, lot quarantine management, defect audits |
| **Coordination** | **ADS-15** | Dynamic Planner | Master production scheduling, buffer replanning, SLA safeguarding |
| **Coordination** | **ADS-16** | Negotiation Protocol | Multi-agent trade-off mediation, blackboard consensus voting |
| **Coordination** | **ADS-17** | CEO Governance | Strategic alignment, threshold escalation (orders > $50,000) |
| **Coordination** | **ADS-18** | BI & Audit Reporting | Final state audit logging, executive explainability reports |

---

## System Requirements

### Hardware Requirements
* **RAM:** Minimum 8 GB (16 GB recommended when running Docker Compose)
* **Storage:** 5 GB free disk space
* **OS:** macOS (Apple Silicon or Intel), Ubuntu / Debian Linux, Windows 10/11 (via WSL2)

### Required Software
Ensure the following base runtimes are installed on your host machine:

| Software | Minimum Version | Installation Link / Command |
| :--- | :--- | :--- |
| **Python** | `3.12+` (3.12, 3.13 tested) | [python.org](https://www.python.org/downloads/) |
| **Node.js** | `20.x` or higher | [nodejs.org](https://nodejs.org/) (`node -v`) |
| **npm** | `10.x` or higher | Bundled with Node.js (`npm -v`) |
| **Git** | `2.x` | [git-scm.com](https://git-scm.com/) |

### Optional Software (for Containerized Setup)
* **Docker Desktop** (version 4.x or higher) with Docker Compose v2.

### Optional LLM Providers (for Live AI Reasoning)
The system operates seamlessly in deterministic offline mode using simulated heuristics. To activate live LLM intelligence:
* **Groq API Key** (Recommended: ultra-fast inference with `llama-3.3-70b-versatile` or `openai/gpt-oss-20b`)
* **OpenAI API Key** or **Anthropic API Key** (Alternative fallbacks)

---

## Environment Configuration

Create your local `.env` configuration file in the project root:

```bash
cp .env.example .env
```

Key environment settings:

```ini
# Application Mode & Security
ENVIRONMENT=development
APP_ENV=development
APP_VERSION=1.0.0
SECRET_KEY=dev-secret-key-change-in-production-must-be-32-chars-min
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Database Configuration (PostgreSQL / SQLite Dual Storage)
# When PostgreSQL is offline, system automatically falls back to SQLite WAL: backend/.storage/digital_twin.db
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=supply_chain
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/supply_chain

# Caching & Message Queue
REDIS_URL=redis://localhost:6379/0
RABBITMQ_URL=amqp://guest:guest@localhost:5672/

# LLM Providers (Optional for live LLM intelligence)
GROQ_API_KEY=gsk_your_groq_api_key_here
LLM_PROVIDER=groq
LLM_MODEL=llama-3.3-70b-versatile

# Governance Thresholds
FINANCE_APPROVAL_THRESHOLD=50000.0
RISK_SCORE_THRESHOLD=70.0
```

---

## Project Setup & Installation

You can set up and run the system using either of the two methods below:

### Option A: Local Development Setup (Quickest, No Docker Needed)

The backend includes a resilient local SQLite WAL persistence layer (`backend/.storage/digital_twin.db`). You can run both backend and frontend directly on your host machine without launching Docker, Postgres, or RabbitMQ.

#### 1. Setup Backend Environment

```bash
# Navigate to the backend directory
cd backend

# Create a Python virtual environment
python3 -m venv .venv

# Activate the virtual environment
# On macOS / Linux:
source .venv/bin/activate
# On Windows (Command Prompt):
# .venv\Scripts\activate.bat
# On Windows (PowerShell):
# .venv\Scripts\Activate.ps1

# Upgrade pip and install all backend dependencies
pip install --upgrade pip
pip install -e ".[dev]"
```

#### 2. Setup Frontend Environment

```bash
# Open a new terminal and navigate to the frontend directory
cd frontend

# Install all NPM dependencies
npm install
```

---

### Option B: Containerized Setup (Docker Compose)

To spin up the entire enterprise ecosystem (PostgreSQL 16 with pgvector, Redis 7, RabbitMQ 3, FastAPI backend, and React frontend):

```bash
# From the project root directory
docker compose up --build -d
```

To view container status:
```bash
docker compose ps
```

---

## Running the Application

### If Using Local Setup (Option A)

#### Step 1: Start the Backend Service
From the `backend` directory (with virtual environment activated):

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend API will start at:
* **API Server:** `http://localhost:8000`
* **Interactive Swagger UI:** `http://localhost:8000/docs`
* **ReDoc Documentation:** `http://localhost:8000/redoc`
* **Health Endpoint:** `http://localhost:8000/health`

#### Step 2: Start the Frontend Application
From the `frontend` directory:

```bash
cd frontend
npm run dev
```

The frontend web console will start at:
* **Web UI Dashboard:** `http://localhost:5173`

---

### If Using Docker Compose (Option B)

Services are automatically started and mapped to the following host endpoints:

| Service | Host URL | Description |
| :--- | :--- | :--- |
| **React Frontend** | `http://localhost:5173` (or `3000`) | Executive Control Tower & Visualizer |
| **FastAPI Backend** | `http://localhost:8000` | REST API Gateway |
| **API Docs (Swagger)** | `http://localhost:8000/docs` | Interactive API documentation |
| **RabbitMQ Management** | `http://localhost:15672` | Management console (`guest` / `guest`) |
| **PostgreSQL Database** | `localhost:5432` | Primary database (`postgres` / `postgres`) |
| **Redis Cache** | `localhost:6379` | Workflow checkpoints & state cache |

---

## Default Demo Credentials

The platform includes built-in role-based access control (RBAC) supporting PBKDF2 hashing:

| Username | Password | Role | Access Permissions |
| :--- | :--- | :--- | :--- |
| **`admin`** | `admin123` | **`admin`** | Full access to execute workflows, simulate disruptions, approve orders, and manage stock |
| **`analyst`** | `analyst123` | **`analyst`** | Access to run scans, view analytics, inspect decision traces, and view audit reports |
| **`viewer`** | `viewer123` | **`viewer`** | Read-only access to dashboard metrics and order status |

---

## Database Migrations & Data Seeding

### Seeding Rich Development Data
To populate the database with realistic products, warehouses, multi-tier suppliers, orders, and initial inventory:

**Local Setup:**
```bash
cd backend
source .venv/bin/activate
python -m scripts.seed_rich
```

**Docker Setup:**
```bash
docker compose exec backend python -m scripts.seed_rich
```

### Running Alembic Migrations (PostgreSQL)
To apply relational DDL migrations to a running PostgreSQL instance:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
```

---

## Running the Test Suites

### Backend Unit & Integration Tests
The backend test suite covers authentication, 18-agent execution, dual-storage synchronization, order item integrity, and event bus routing:

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

To run a specific test suite:
```bash
# Test 18-agent autonomous loop
pytest tests/test_autonomous_agentic_loop.py -v

# Test business intelligence agents
pytest tests/test_bi_agents.py -v

# Test authentication and RBAC workflows
pytest tests/test_f001_auth_workflows.py -v
```

### Frontend Typecheck & Production Build
To verify frontend TypeScript types and compile the production bundle:

```bash
cd frontend
npm run build
```

---

## Core API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/auth/login` | Authenticate with username and password; returns JWT Bearer token |
| `GET` | `/api/v1/analytics/dashboard` | Get real-time KPIs, inventory distribution, and recent commercial orders |
| `GET` | `/api/v1/inventory` | List warehouse stock levels (with `low_stock_only` filter) |
| `POST` | `/api/v1/inventory/autonomous-scan` | Trigger agentic stock scan; dispatches ADS-03 & ADS-05 replenishment |
| `POST` | `/api/v1/inventory/replenish/auto-heal` | Autonomously check in in-transit purchase orders and replenish warehouse stock |
| `POST` | `/api/v1/orders` | Submit a commercial order to trigger the full 18-agent LangGraph workflow |
| `GET` | `/api/v1/orders/{order_id}` | Fetch order details, logistics status, and full multi-agent decision audit trail |
| `GET` | `/api/v1/workflows/{id}/trace` | Retrieve execution timeline, inputs, decisions, and outputs for all 18 agents |
| `POST` | `/api/v1/workflows/{id}/approve` | Executive approval sign-off for orders requiring governance review |
| `POST` | `/api/v1/workflows/{id}/reject` | Executive rejection of orders violating policy or budget limits |
| `POST` | `/api/v1/events/inject` | Inject operational disruption event (e.g. `DeliveryDelayed`, `SupplierUnavailable`) |
| `POST` | `/api/v1/simulate` | Execute what-if disruptive scenario simulations |
| `GET` | `/health` | Live system health check probing DB, Redis, and RabbitMQ dependencies |

Full schema specifications and live request testing are available at [http://localhost:8000/docs](http://localhost:8000/docs).

---

## Troubleshooting & Common FAQs

### 1. "Port 8000 or 5173 is already in use"
Check and terminate any conflicting processes:
```bash
# On macOS / Linux:
lsof -i :8000 -i :5173
kill -9 <PID>
```

### 2. "RabbitMQ / Redis connection error in `/health`"
If you are running in local mode (Option A) without Docker, this is completely normal. The application logs an offline warning and automatically utilizes SQLite WAL persistence (`backend/.storage/digital_twin.db`) and in-memory event dispatching so that all agent workflows execute without external services.

### 3. "Net Available shows a negative number in the Inventory tab"
`Net Available = Available Qty - Reserved Qty`. A negative number indicates that customer sales orders exceed current physical shelf stock (backorder). 
* The system automatically generates inbound replenishment purchase orders (`in_transit`).
* To simulate the arrival of those goods and check them into warehouse stock, click **"Receive Stock"** in the Inventory page header or click **"Receive"** in the Procurement tab.

### 4. "Groq API rate limit or missing API key"
If no `GROQ_API_KEY` is provided, the system seamlessly uses deterministic heuristic decision engines across all 18 agents. No external API key is required to explore and evaluate the platform.

---

## License

This project is licensed under the Apache 2.0 License. See the [LICENSE](LICENSE) file for details.
