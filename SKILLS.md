# ScopeSentinel — Project Skills & Architecture Context

This document provides AI assistants with the necessary architectural context to work on ScopeSentinel without needing to read the entire codebase.

## 🏢 1. Core Architecture & Philosophy
ScopeSentinel is a multi-tenant, event-driven, AI-augmented workflow automation platform for autonomous software delivery.
- **Self-hosted first**: We prioritize open-source, self-hostable tools (PostgreSQL, Redis, Keycloak, Temporal, Redpanda) over managed cloud services.
- **Monorepo Structure**: All microservices are housed in one repository but deployed independently via Docker/k3s.
- **API-First**: Every feature must be available as a REST API before a UI is built for it.

## 🧩 2. Services Breakdown

### 2.1 `services/api/` (Control Plane API)
- **Role**: The main FastAPI backend serving HTTP requests, handling CRUD operations, and dispatching tasks to workers.
- **Tech Stack**: Python 3.12+, FastAPI, Uvicorn, SQLModel (ORM), Alembic, asyncpg, Celery (dispatcher).
- **Database**: PostgreSQL (async queries via `session.exec()`).
- **Key Concepts**:
  - Uses `structlog` for JSON-formatted logging.
  - Authentication via Keycloak JWTs or hashed API keys (`auth/api_keys.py`).
  - Idempotent database seeding runs on application startup (`db/seed.py`).

### 2.2 `services/agent-runtime/` (AI Execution Worker)
- **Role**: The Celery worker executing background tasks (e.g., executing AgentScope logic, LLM calls, tool interactions).
- **Tech Stack**: Python 3.12+, Celery, AgentScope, Redis (Pub/Sub).
- **Key Concepts**:
  - Consumes tasks dispatched by the `api` service.
  - Implements Human-in-the-Loop (HITL) gates using Redis pub/sub to pause and resume agent execution.
  - Contains all AI Agents (`PlannerAgent`, `CoderAgent`), Tools, and LLM Gateway logic.

### 2.3 `frontend/` (Web UI - Coming Soon)
- **Role**: The standalone browser-based dashboard for workflow monitoring and visual DAG building.
- **Tech Stack**: Next.js 15 (App Router), React, TailwindCSS, shadcn/ui, React Flow (DAG editor), Zustand, React Query.

### 2.4 `infra/` (Infrastructure & Deployment)
- **Role**: Contains configuration files for third-party self-hosted infrastructure.
- **Current Layout**: Contains Keycloak realm exports (`infra/keycloak/realm-export.json`). Will house Kubernetes/Helm/Terraform manifests in the future.

## 🗄️ 3. Data Stores & Infrastructure
- **Relational DB**: PostgreSQL (Async). `models.py` uses SQLModel schemas.
- **Message/State Brokers**: Redis (Celery broker, Pub/Sub for HITL, rate limiting).
- **Event Streaming**: Redpanda (Kafka-compatible, planned for Phase 3).
- **Identity**: Keycloak (OIDC/SAML).

## 🧪 4. Testing & QA
- **Backend Tests**: `pytest` and `pytest-asyncio`. Uses an in-memory `sqlite+aiosqlite` database for fast execution (`conftest.py`). **Must maintain >70% coverage.**
- **Formatting/Linting**: `ruff` is the standard for Python code.
