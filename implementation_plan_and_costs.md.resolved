# ScopeSentinel — Phased Implementation Plan
## Principal Engineer & Project Manager View

> **Philosophy**: Ship something real every 4–6 weeks. Each phase has a working, demoable artifact. Open-source and self-hosted first — no paid managed services until revenue justifies it.

---

## Principles

- **Self-hosted everything**: Redpanda, Temporal, Keycloak, Qdrant, PostgreSQL, Vault, Grafana Stack — all run in Docker Compose (dev) → k3s (prod)
- **Open-source LLMs**: Use Ollama + Llama 3 / Mistral locally. OpenAI API only as an optional premium backend
- **Monorepo**: All services in one repo, deployed independently but developed together
- **API-first**: Every feature is a callable API before it has a UI
- **No premature scaling**: PostgreSQL + Redis handles millions of rows. Add Kafka only in Phase 3

---

## Tech Stack (Fully Open-Source / Self-Hosted)

| Layer | Open-Source Choice | Managed Alternative (future) |
|---|---|---|
| Workflow Engine | **Temporal** (self-hosted) | Temporal Cloud |
| Message Broker | **Redpanda** (self-hosted) | Confluent Cloud / AWS MSK |
| Stream Processor | **Apache Flink** (self-hosted) | AWS Kinesis Analytics |
| Identity | **Keycloak** (self-hosted) | Auth0 / Okta |
| API Gateway | **Kong OSS** (self-hosted) | Kong Cloud |
| Primary DB | **PostgreSQL** (self-hosted) | RDS / Cloud SQL |
| Cache | **Redis / Valkey** (self-hosted) | ElastiCache |
| Vector DB | **Qdrant** (self-hosted) | Pinecone / Weaviate Cloud |
| Log Store | **OpenSearch** (self-hosted) | Elastic Cloud |
| Metrics | **TimescaleDB** (self-hosted) | InfluxDB Cloud |
| Traces | **Grafana Tempo** (self-hosted) | Datadog |
| Observability | **Grafana + Loki + Mimir** | Grafana Cloud |
| Secrets | **HashiCorp Vault** (self-hosted) | AWS Secrets Manager |
| Container Orch | **k3s** (self-hosted) | EKS / GKE |
| LLM | **Ollama + Llama 3.3** (local) | OpenAI GPT-4o API |
| CI/CD | **Gitea + Woodpecker CI** | GitHub + GitHub Actions |

---

## Implementation Phases

---

## 🔵 Phase 0 — Foundation Hardening *(Now → 4 weeks)*
**Goal**: Make the existing Python CLI bulletproof and properly structured before adding anything new.

**Exit Criteria**: A clean, tested, Dockerized CLI that any developer can run in 5 minutes.

### Epics & Stories

#### Epic 0.1 — Code Quality & Structure
| # | Story | Size | Notes |
|---|---|---|---|
| 0.1.1 | Restructure repo as monorepo: `services/agent-runtime/`, `services/api/`, `frontend/`, `infra/` | S | Move existing code into `services/agent-runtime/` |
| 0.1.2 | Add structured logging (JSON format: `run_id`, `ticket_id`, `step`, `level`) | S | Replace `print()` with `structlog` |
| 0.1.3 | Global error handler — catch MCP failures, LLM timeouts, Docker socket errors gracefully | S | Wrap [run_planner_workflow](file:///Users/kvelayudham/Personal%20Github/ScopeSentinel/main.py#54-132) with typed exceptions |
| 0.1.4 | `--dry-run` flag: run planner + HITL only, skip coder + git | S | |
| 0.1.5 | [.env.example](file:///Users/kvelayudham/Personal%20Github/ScopeSentinel/.env.example) coverage — document every variable with examples | XS | |

#### Epic 0.2 — Testing
| # | Story | Size | Notes |
|---|---|---|---|
| 0.2.1 | Unit tests for `PlannerAgent`: mock LLM, assert plan schema | M | pytest + respx for HTTP mocking |
| 0.2.2 | Unit tests for `CoderAgent`: mock LLM, assert file write/delete logic | M | |
| 0.2.3 | Unit tests for [mcp_pool.py](file:///Users/kvelayudham/Personal%20Github/ScopeSentinel/mcp_pool.py): mock `StdIOStatefulClient`, test env var substitution | S | |
| 0.2.4 | Integration test for sandbox runner: use real Docker on CI | M | Requires Docker-in-Docker in Woodpecker CI |
| 0.2.5 | Test coverage gate at 70% minimum (fail CI if below) | XS | |

#### Epic 0.3 — Containerization
| # | Story | Size | Notes |
|---|---|---|---|
| 0.3.1 | `Dockerfile` for agent-runtime: multi-stage build, non-root user | S | |
| 0.3.2 | `docker-compose.yml` for local dev: agent-runtime + PostgreSQL + Redis | S | SQLite for Phase 0, Postgres for Phase 1 |
| 0.3.3 | `Makefile` with targets: `make dev`, `make test`, `make build`, `make run TICKET=SCRUM-8` | XS | |

**Phase 0 Velocity**: ~3 weeks solo | ~1.5 weeks with 2 engineers

---

## 🟡 Phase 1 — FastAPI Control Plane *(Weeks 5–10)*
**Goal**: Turn the CLI into a durable, async service with a real database and REST API. The CLI becomes just a client.

**Exit Criteria**: `curl -X POST /api/runs -d '{"ticket_id":"SCRUM-8"}'` triggers the full workflow. Status queryable. HITL via API.

### Epics & Stories

#### Epic 1.1 — Database Schema
| # | Story | Size | Notes |
|---|---|---|---|
| 1.1.1 | Schema design: `orgs`, `users`, `workflows`, `workflow_runs`, `run_steps`, `hitl_events` | M | With Alembic migrations |
| 1.1.2 | SQLAlchemy models + async session management | M | Use `asyncpg` driver |
| 1.1.3 | Seed: default org + admin user on first boot | S | |
| 1.1.4 | PostgreSQL in Docker Compose with init scripts | XS | |

#### Epic 1.2 — FastAPI API Server
| # | Story | Size | Notes |
|---|---|---|---|
| 1.2.1 | `POST /api/runs` — trigger workflow, return `run_id` | M | |
| 1.2.2 | `GET /api/runs` — list runs with status, pagination | S | |
| 1.2.3 | `GET /api/runs/{id}` — full run detail with steps | S | |
| 1.2.4 | `GET /api/runs/{id}/plan` — return structured plan JSON | S | |
| 1.2.5 | `POST /api/runs/{id}/decision` — HITL approve/reject/modify | M | |
| 1.2.6 | `GET /api/runs/{id}/logs` — WebSocket real-time log stream | L | |
| 1.2.7 | `GET /api/health` — liveness + dependency check | XS | |

#### Epic 1.3 — Async Execution
| # | Story | Size | Notes |
|---|---|---|---|
| 1.3.1 | Celery + Redis setup: agent-runtime as a Celery worker | M | Replace `asyncio.run()` with `task.delay()` |
| 1.3.2 | Task state machine: PENDING → RUNNING → SUCCEEDED / FAILED / WAITING_HITL | M | Stored in PostgreSQL `workflow_runs` |
| 1.3.3 | HITL pause mechanism: task pauses and writes HITL event, resumes on `/decision` call | L | Use Celery chord or asyncio.Event |
| 1.3.4 | Step-level state persistence: write each step result to `run_steps` table | M | |

#### Epic 1.4 — Auth (Basic)
| # | Story | Size | Notes |
|---|---|---|---|
| 1.4.1 | Keycloak in Docker Compose: pre-configured realm + client | M | Use `keycloak-config-cli` for declarative config |
| 1.4.2 | FastAPI JWT middleware: validate Keycloak-issued JWTs | M | `python-jose` or `fastapi-users` |
| 1.4.3 | API key support: hash-stored keys as alternative to JWT | M | For CLI/machine-to-machine use |

**Phase 1 Velocity**: ~5 weeks solo | ~3 weeks with 2 engineers

---

## 🟠 Phase 2 — Web UI Monitoring Dashboard *(Weeks 11–18)*
**Goal**: A real browser UI. Teams can see runs, logs, and approve HITL gates without using `curl`.

**Exit Criteria**: Full run lifecycle visible and actionable in the browser.

### Epics & Stories

#### Epic 2.1 — Frontend Foundation
| # | Story | Size | Notes |
|---|---|---|---|
| 2.1.1 | Next.js 15 app setup: App Router, shadcn/ui, TailwindCSS | M | `npx create-next-app` |
| 2.1.2 | Auth integration: Keycloak OIDC via `next-auth` | M | |
| 2.1.3 | API client layer: typed React Query hooks for all backend endpoints | M | OpenAPI → codegen |
| 2.1.4 | Sidebar navigation: Runs, Workflows, Integrations, Settings | S | |
| 2.1.5 | Design system: color palette, typography, component tokens | S | |

#### Epic 2.2 — Run Monitoring
| # | Story | Size | Notes |
|---|---|---|---|
| 2.2.1 | Runs list page: table with status badge, ticket link, start time, duration | M | |
| 2.2.2 | Run detail page: step timeline (⏳PENDING → ✅DONE → ❌FAILED) | L | |
| 2.2.3 | Live log stream panel: WebSocket connected, auto-scroll, ANSI color support | L | |
| 2.2.4 | Step detail drawer: input/output JSON viewer per step | M | |
| 2.2.5 | Run replay: re-trigger a completed run with same inputs | M | |

#### Epic 2.3 — HITL Panel
| # | Story | Size | Notes |
|---|---|---|---|
| 2.3.1 | HITL notification banner: "Waiting for your approval" with deep link | M | Poll or WebSocket push |
| 2.3.2 | Plan review panel: markdown-rendered plan with Approve / Reject buttons | M | |
| 2.3.3 | Modify flow: text input for feedback → submit → re-plan triggers | M | |
| 2.3.4 | Code diff viewer: syntax-highlighted diff of generated files | L | Monaco Editor or `react-diff-view` |

#### Epic 2.4 — App Connections Screen
| # | Story | Size | Notes |
|---|---|---|---|
| 2.4.1 | Connections page: installed apps grid with status indicator | M | |
| 2.4.2 | OAuth connection flow: "Connect Jira" → redirect → callback → stored | L | Integration Service |
| 2.4.3 | API key connection flow: for tools that use API key auth (GitHub PAT, etc.) | M | |
| 2.4.4 | Connection health display: last successful call timestamp + error state | S | |

**Phase 2 Velocity**: ~7 weeks solo | ~4 weeks with 2 engineers

---

## 🔴 Phase 3 — Event Backbone + Visual Workflow Builder *(Weeks 19–30)*
**Goal**: The visual DAG builder and event-driven trigger system. This is the Gumloop-level capability.

**Exit Criteria**: User drags-and-drops a workflow, saves it, gets triggered by a GitHub webhook, runs end-to-end.

### Epics & Stories

#### Epic 3.1 — Event Streaming Infrastructure
| # | Story | Size | Notes |
|---|---|---|---|
| 3.1.1 | Redpanda in Docker Compose + k3s: single-node, Kafka-compatible | M | Simpler than Kafka, same API |
| 3.1.2 | Webhook Receiver service: ingest GitHub, Jira, Datadog events → validate → publish to Redpanda | L | Signature verification per source |
| 3.1.3 | Schema Registry (Redpanda built-in): define Avro schemas for all platform events | M | |
| 3.1.4 | Workflow trigger engine: Kafka Consumer that matches events to workflow trigger rules | L | |
| 3.1.5 | Cron trigger: register cron expressions → emit trigger events at scheduled time | M | APScheduler or Temporal Scheduler |

#### Epic 3.2 — Temporal Workflow Engine
| # | Story | Size | Notes |
|---|---|---|---|
| 3.2.1 | Temporal self-hosted in Docker Compose (server + worker + UI) | M | Official Temporal Docker images |
| 3.2.2 | Migrate agent-runtime from Celery tasks to Temporal Workflows + Activities | XL | Core refactor: each step = Activity |
| 3.2.3 | Temporal HITL: Workflow pauses via `workflow.wait_condition()`, resumes on Signal | L | |
| 3.2.4 | Temporal retry policies per step: configurable in workflow definition JSON | M | |
| 3.2.5 | Step I/O capture: save input/output of each Activity to S3 (MinIO self-hosted) | M | |

#### Epic 3.3 — Workflow Definition System
| # | Story | Size | Notes |
|---|---|---|---|
| 3.3.1 | Workflow YAML DSL spec + JSON Schema validation | M | Define the grammar |
| 3.3.2 | CRUD API for workflow definitions: `POST/GET/PUT/DELETE /api/workflows` | M | |
| 3.3.3 | Workflow template library: 5 pre-built templates (Jira→PR, Build Failure, PR Review, etc.) | L | |
| 3.3.4 | Workflow import/export: upload/download YAML files | S | |
| 3.3.5 | Workflow versioning: track definition changes with `version` field | M | |

#### Epic 3.4 — Visual Workflow Designer
| # | Story | Size | Notes |
|---|---|---|---|
| 3.4.1 | React Flow canvas: pan, zoom, node drag/drop | L | `@xyflow/react` |
| 3.4.2 | Node palette: categories (Triggers, AI, Tools, Logic, HITL) | M | |
| 3.4.3 | Node types: Trigger, Agent Step, Tool Call, Condition (if/else), HITL Gate, Delay | XL | Each node has its own config panel |
| 3.4.4 | Node config sidebar: edit inputs, bind `{{ steps.xyz.output }}` expressions | L | |
| 3.4.5 | Canvas → YAML serializer: save the visual graph as workflow YAML | L | |
| 3.4.6 | YAML → Canvas deserializer: load saved workflow back into the visual editor | M | |
| 3.4.7 | Run from designer: "Test Run" button triggers a run without saving | M | |
| 3.4.8 | Execution replay on canvas: step-by-step highlight of a past run's path | L | |

#### Epic 3.5 — App Connector Expansion (10+ apps)
| # | Story | Size | Notes |
|---|---|---|---|
| 3.5.1 | Connector SDK: `BaseConnector` with `list_tools()`, `call_tool()`, OAuth2 mixin | L | |
| 3.5.2 | Connectors: GitHub, GitLab, Jira, Linear | L | |
| 3.5.3 | Connectors: Slack, Discord, PagerDuty | M | |
| 3.5.4 | Connectors: Jenkins, CircleCI, GitHub Actions | M | |
| 3.5.5 | Connectors: Kubernetes (kubectl via REST), Datadog, Prometheus | L | |
| 3.5.6 | Marketplace UI: searchable connector grid with "Install" button | M | |

**Phase 3 Velocity**: ~11 weeks solo | ~6 weeks with 3 engineers

---

## 🟣 Phase 4 — AI Enhancement + Knowledge Layer *(Weeks 31–38)*
**Goal**: Agents get smarter. RAG over codebases, local LLM support, prompt management.

**Exit Criteria**: Agent can semantically search your repo before generating code. Ollama runs locally as default LLM.

### Epics & Stories

#### Epic 4.1 — LLM Gateway
| # | Story | Size | Notes |
|---|---|---|---|
| 4.1.1 | LiteLLM proxy: unified API for OpenAI, Anthropic, Ollama, Gemini | M | Self-hosted LiteLLM server |
| 4.1.2 | Model routing: per-workflow model selection (GPT-4o for complex, Llama for simple) | M | |
| 4.1.3 | Ollama integration: pull and serve Llama 3.3 / Mistral locally | M | GPU optional, CPU works for dev |
| 4.1.4 | Prompt versioning: DB-backed prompt registry with A/B test support | L | |
| 4.1.5 | Token cost tracking: log `{model, prompt_tokens, completion_tokens}` per call → Metering | M | |

#### Epic 4.2 — Knowledge Layer (RAG)
| # | Story | Size | Notes |
|---|---|---|---|
| 4.2.1 | Qdrant self-hosted in Docker Compose | S | |
| 4.2.2 | Repo ingestion pipeline: clone repo → chunk files → embed → upsert into Qdrant | L | `langchain.text_splitter` + `bge-large` embedding model |
| 4.2.3 | `search_codebase(query, top_k)` tool exposed to agents | M | |
| 4.2.4 | UI: "Knowledge Bases" page — connect a repo, trigger indexing, view status | M | |
| 4.2.5 | Re-index on push: GitHub webhook → re-ingest changed files only | M | |
| 4.2.6 | Past run memory: embed plan + outcome summaries → agent searches similar past runs | L | |

#### Epic 4.3 — Multi-Agent Enhancement
| # | Story | Size | Notes |
|---|---|---|---|
| 4.3.1 | Analyzer Agent: after each run, score quality + write structured feedback | M | |
| 4.3.2 | Short-term memory: Redis-backed conversation context per agent session (TTL 24h) | M | |
| 4.3.3 | Agent session UI: view agent thought stream step-by-step in the browser | L | |
| 4.3.4 | Conversational interface: chat panel to trigger workflows via natural language | XL | Streaming responses via Vercel AI SDK |

**Phase 4 Velocity**: ~8 weeks solo | ~4 weeks with 2 engineers

---

## 🔵 Phase 5 — Enterprise Features *(Weeks 39–50)*
**Goal**: Multi-tenancy, RBAC, audit logging, usage metering. Ready to onboard real teams.

**Exit Criteria**: Multiple orgs can run in isolation. Admin can manage users/roles. Usage tracked in dashboard.

### Epics & Stories

#### Epic 5.1 — Multi-Tenancy
| # | Story | Size | Notes |
|---|---|---|---|
| 5.1.1 | Schema-per-tenant provisioning: on org create → Alembic creates `tenant_{id}` schema | L | |
| 5.1.2 | Tenant-aware DB session: middleware injects `search_path=tenant_{id}` per request | M | |
| 5.1.3 | Tenant-aware Redpanda topics: `t.{org_id}.*` auto-created on org setup | M | |
| 5.1.4 | Tenant-aware Qdrant collections: `org_{id}_knowledge` isolated per tenant | S | |
| 5.1.5 | Tenant config: per-org LLM model, token quota, feature flags | M | |

#### Epic 5.2 — RBAC & Access Control
| # | Story | Size | Notes |
|---|---|---|---|
| 5.2.1 | Roles: `ORG_ADMIN`, `DEVELOPER`, `REVIEWER`, `VIEWER` — enforced at API layer | M | |
| 5.2.2 | Role management UI: invite users, assign roles, revoke access | M | |
| 5.2.3 | Resource-level permissions: who can trigger/approve workflows | M | |
| 5.2.4 | API key scoping: API keys tied to specific roles and resources | M | |

#### Epic 5.3 — Audit Log
| # | Story | Size | Notes |
|---|---|---|---|
| 5.3.1 | Append-only `audit_events` table: who, what, when, on what resource | M | WAL-replicated to MinIO for immutability |
| 5.3.2 | Audit middleware: auto-log all mutating API calls | M | FastAPI middleware |
| 5.3.3 | Audit log viewer UI: filterable table by user/action/date | M | |

#### Epic 5.4 — Usage Metering & Billing
| # | Story | Size | Notes |
|---|---|---|---|
| 5.4.1 | Metering events: emit to Redpanda on every run, step, and LLM call | M | |
| 5.4.2 | Metering consumer: aggregate into `usage_buckets` table (hourly rollup) | M | |
| 5.4.3 | Quota enforcement: Redis sliding window counter at API Gateway | M | |
| 5.4.4 | Usage dashboard UI: charts for executions, tokens, API calls per billing period | L | |
| 5.4.5 | Stripe integration: subscription plans, invoices, upgrades | XL | Optional for private beta |

#### Epic 5.5 — Observability Pipeline
| # | Story | Size | Notes |
|---|---|---|---|
| 5.5.1 | Flink job: window aggregate metrics → anomaly detection (Z-score baseline) | XL | |
| 5.5.2 | OpenSearch self-hosted: log ingestion via Fluent Bit → OpenSearch | L | |
| 5.5.3 | TimescaleDB: metrics storage + Grafana dashboard | M | |
| 5.5.4 | Grafana stack: Loki + Tempo + Mimir self-hosted | L | |
| 5.5.5 | Platform observability: OTEL instrumentation on all services | L | |

**Phase 5 Velocity**: ~12 weeks solo | ~6 weeks with 3 engineers

---

## 📊 Story Size Key

| Size | Effort |
|---|---|
| XS | < 2 hours |
| S | 2–8 hours (half-day to full-day) |
| M | 1–3 days |
| L | 3–5 days (one sprint story) |
| XL | 1–2 weeks (needs breakdown) |

---

## 💰 Build Cost Analysis

> Assumes you are the solo builder, or have input on team size. All figures in USD.

### Option A: Solo Builder

| Phase | Duration | Cost (opportunity cost @ $60/hr) |
|---|---|---|
| Phase 0 | 3 weeks | ~$7,200 |
| Phase 1 | 5 weeks | ~$12,000 |
| Phase 2 | 7 weeks | ~$16,800 |
| Phase 3 | 11 weeks | ~$26,400 |
| Phase 4 | 8 weeks | ~$19,200 |
| Phase 5 | 12 weeks | ~$28,800 |
| **Total** | **~46 weeks (~11 months)** | **~$110,400** |

### Option B: Small Team (1 Full-stack + 1 Backend + 1 DevOps/part-time)

| Phase | Duration | Team Cost |
|---|---|---|
| Phase 0 | 1.5 weeks | ~$9,000 |
| Phase 1 | 3 weeks | ~$18,000 |
| Phase 2 | 4 weeks | ~$24,000 |
| Phase 3 | 6 weeks | ~$36,000 |
| Phase 4 | 4 weeks | ~$24,000 |
| Phase 5 | 6 weeks | ~$36,000 |
| **Total** | **~25 weeks (~6 months)** | **~$147,000** |

> **Practical advice**: MVP (Phase 0+1+2) in ~3.5 months solo gets you a working, demoable product. That's the real target before hiring.

### External Costs During Build

| Item | Cost/Month | Notes |
|---|---|---|
| OpenAI API (dev testing) | ~$30–80 | Use Ollama locally to minimize this |
| Domain + SSL | ~$15 | Caddy handles SSL automatically |
| GitHub (private repos) | $0–4 | Free tier covers most |
| Total | **~$45–100/month** | |

---

## 🖥️ Hosting Cost Analysis (Self-Hosted, Open-Source)

### Local Development (Phase 0–1)
**Cost: $0/month**
- Docker Compose on your local Mac
- All services: PostgreSQL, Redis, Keycloak, Temporal, Qdrant
- Everything fits in 16 GB RAM

### Staging Environment (Phase 1–2)
**Cost: ~$30–60/month**

| Server | Spec | Provider | Cost/Month |
|---|---|---|---|
| 1x VPS (all-in-one) | 8 vCPU / 32 GB RAM / 320 GB SSD | Hetzner CX52 | ~$34 |
| Backups | 20% of server cost | Hetzner | ~$7 |
| **Total** | | | **~$41/month** |

Runs on k3s (lightweight Kubernetes):
- PostgreSQL, Redis, Keycloak, Temporal, Qdrant, agent-runtime, API server, Next.js frontend

### Production Environment (Phase 3+, MVP live users)
**Cost: ~$200–300/month (fully self-hosted on Hetzner)**

| Component | Spec | Cost/Month |
|---|---|---|
| Control plane node | CX32 (4 vCPU / 8 GB) | ~$18 |
| Worker node 1 (Platform services) | CX52 (8 vCPU / 32 GB) | ~$34 |
| Worker node 2 (Data: PG, Redis, Qdrant) | CX52 (8 vCPU / 32 GB) | ~$34 |
| Worker node 3 (Redpanda + Flink) | CX42 (8 vCPU / 16 GB) | ~$24 |
| Load Balancer | Hetzner LB11 | ~$7 |
| Object Storage (MinIO) | Hetzner Volume 200 GB | ~$10 |
| Backups | ~20% | ~$25 |
| Bandwidth | 20 TB free | $0 |
| **Total** | | **~$152/month** |

> **Compare:** AWS equivalent = $1,500–3,000/month (EKS + RDS + ElastiCache + MSK + OpenSearch)
> **Hetzner savings: ~90% cost reduction** vs managed AWS

### Cost at Scale (10+ paying tenants, Phase 5)
Once you have paying customers, you can justify managed services selectively:

| Selective Migration | Cost | Reason |
|---|---|---|
| Temporal Cloud | ~$25–100/month | Eliminate Temporal ops burden |
| Neon PostgreSQL | ~$19/month | Serverless, branching for tenants |
| Everything else | Self-hosted | Redpanda, Qdrant, Keycloak stay self-hosted |

**Estimated break-even**: 5 paying customers at $50/month each covers full infra costs.

---

## 🗓️ Milestone Summary

```
Month 1  → Phase 0 complete: Clean, tested, Dockerized CLI
Month 3  → Phase 1 complete: FastAPI + Database + Async worker + Auth
Month 5  → Phase 2 complete: Full web UI, live logs, HITL panel in browser
Month 8  → Phase 3 complete: Visual designer, event triggers, 10+ connectors
Month 10 → Phase 4 complete: RAG, Ollama LLM, conv. chat interface
Month 12 → Phase 5 complete: Multi-tenancy, RBAC, metering → ready for paying customers
```

---

## 🚦 What to Build Next (Immediate Priorities)

Based on current state, the next 3 sprints should be:

1. **Sprint 1 (Week 1–2)**: Epic 0.1 + 0.3 — Monorepo restructure + Dockerization
2. **Sprint 2 (Week 3–4)**: Epic 0.2 — Test suite (get to 70% coverage)
3. **Sprint 3 (Week 5–7)**: Epic 1.1 + 1.2 — PostgreSQL schema + FastAPI endpoints

This gives you a clean, API-driven foundation without breaking anything that works today.
