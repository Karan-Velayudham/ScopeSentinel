# ScopeSentinel — Project Skills & Architecture Context

This document provides AI assistants with the necessary architectural context to work on ScopeSentinel without needing to read the entire codebase.

## 🏢 1. Core Architecture & Philosophy

**Vision:** We envision a world where engineering teams operate as orchestrators of intelligent systems, seamlessly delegating work to autonomous agents that continuously build, test, and improve software—making high-quality software delivery faster, more scalable, and universally accessible.

**Mission:** To transform software development from manual execution to intent-driven automation by enabling autonomous agents to design, implement, and validate code end-to-end within a controlled, human-governed workflow.

**Goal:** Build a multi-tenant, extensible platform where engineers can delegate software tasks to autonomous agents that operate in isolated environments, execute work end-to-end, and deliver production-ready outputs—allowing teams to scale engineering throughput through parallel, asynchronous execution while retaining human control over critical decisions.

**Product Principles:**
The product is built on the principle of **intent over implementation**, where users define what needs to be done and autonomous agents handle execution end-to-end with full ownership, producing validated, production-ready outcomes. Agents operate with **autonomy but strict accountability**, ensuring every action is traceable, reviewable, and reversible, while **human judgment remains the final gate** for all critical decisions. The system combines **deterministic workflows with intelligent execution**, enabling predictable orchestration and adaptive problem-solving, all within **safe, isolated environments**. It is designed to be **parallel by default**, allowing multiple agents to run concurrently, with **tight feedback loops** for continuous validation and self-correction. Deep **tool integration over model dependency**, along with **transparency, extensibility, and multi-tenant scalability**, ensures the platform remains reliable, explainable, and adaptable—prioritizing **progress over perfection** to deliver fast, iterative value.

> [!IMPORTANT]
> **No Mock Implementations**: Always provide real, functional code for both backend and frontend. Avoid placeholders, "coming soon" markers, or mock data. If a task is too large, break it down rather than using mocks.

---

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
