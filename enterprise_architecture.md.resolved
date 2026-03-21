# ScopeSentinel — Enterprise Architecture
## Principal Architect Technical Design

> **Platform Mission**: A multi-tenant, event-driven, AI-augmented workflow automation platform for autonomous software delivery — extensible to any domain.

---

## 1. System Overview

ScopeSentinel sits at the intersection of three paradigms:

| Paradigm | What it means for ScopeSentinel |
|---|---|
| **iPaaS** (Integration Platform as a Service) | Connect any tool via OAuth/API. Pre-built connectors |
| **Workflow Orchestration** | Visual DAG builder, execution engine, scheduling |
| **Agentic AI** | Autonomous multi-agent loops with memory, tools, and HITL |

The platform processes events from software infrastructure (CI/CD, monitoring, incidents), runs them through AI reasoning, and takes automated action — or pauses for human approval.

---

## 2. High-Level Architecture

```mermaid
graph TD
    subgraph "Ingress Layer"
        AGW["API Gateway (Kong/Nginx)\nAuth · Rate Limit · Routing"]
        WH["Webhook Receiver\n(GitHub, Jira, Datadog)"]
        CHAT["Chat Interface\n(Conversational AI)"]
    end

    subgraph "Platform Services"
        IAM["Identity & Access Service\n(Keycloak / Auth0)"]
        TENANT["Tenant Management Service"]
        WFS["Workflow Orchestration Service\n(DAG Engine)"]
        AGS["Agent Orchestration Service\n(Multi-Agent Coordinator)"]
        INT["Integration Service\n(App Connectors + OAuth)"]
        RULES["Rules & Policy Engine"]
        NOTIF["Notification Service"]
        SEARCH["Search & Query Service\n(Elasticsearch)"]
        METER["Metering & Billing Service"]
    end

    subgraph "Event Backbone"
        KAFKA["Apache Kafka\n(Event Bus)"]
        FLINK["Apache Flink\n(Stream Processing)"]
        SR["Schema Registry\n(Avro / Protobuf)"]
    end

    subgraph "AI / Agent Runtime"
        PLANNER["Planner Agent\n(Goal → DAG Plan)"]
        EXECUTOR["Executor Agent\n(Tool Calls)"]
        ANALYZER["Analyzer Agent\n(Feedback + Reflection)"]
        LLM["LLM Gateway\n(GPT-4o · Claude · Gemini)"]
        MCP["MCP Server Pool\n(Dynamic Tool Registry)"]
    end

    subgraph "Observability Ingestion"
        LOGS["Log Ingestion\n(Fluent Bit → OpenSearch)"]
        METRICS["Metric Ingestion\n(OTEL → TimescaleDB)"]
        TRACES["Trace Ingestion\n(Jaeger / Tempo)"]
        ANOMALY["Anomaly Detector\n(Flink ML)"]
    end

    subgraph "Data Layer"
        PG["PostgreSQL\n(Workflows, Runs, Users, Orgs)"]
        REDIS["Redis\n(Cache · Sessions · Pub/Sub)"]
        ES["OpenSearch / Elasticsearch\n(Logs · Full-text)"]
        TS["TimescaleDB\n(Metrics, Time-series)"]
        QDRANT["Qdrant\n(Vector Embeddings · RAG)"]
        VAULT["HashiCorp Vault\n(Secrets)"]
        S3["Object Storage S3\n(Artifacts · Logs · Exports)"]
    end

    subgraph "Frontend"
        UI["Next.js SPA\n(Workflow Designer · Dashboard · Chat)"]
    end

    UI --> AGW
    CHAT --> AGW
    WH --> AGW
    AGW --> IAM
    AGW --> WFS & AGS & INT & NOTIF & SEARCH & METER
    WFS & AGS --> KAFKA
    KAFKA --> FLINK
    FLINK --> ANOMALY & LOGS & METRICS
    AGS --> PLANNER & EXECUTOR & ANALYZER
    PLANNER & EXECUTOR & ANALYZER --> LLM
    EXECUTOR --> MCP --> INT
    WFS & AGS --> PG & REDIS
    INT --> VAULT
    LOGS --> ES
    METRICS --> TS
    AGS --> QDRANT
    RULES --> WFS
    ANOMALY --> KAFKA
```

---

## 3. Microservices — Responsibilities & Contracts

### 3.1 API Gateway / BFF
**Technology**: Kong Gateway + Next.js BFF (Backend for Frontend)
- **Responsibilities**: TLS termination, JWT validation, rate limiting (per tenant), request routing, response aggregation for UI
- **Inbound**: All client traffic (browser, webhooks, mobile)
- **Outbound**: Routes to internal services via gRPC or REST
- **Key Patterns**: Sidecar auth (Kong plugin), circuit breaker per upstream service

---

### 3.2 Identity & Access Service
**Technology**: Keycloak (self-hosted) or Auth0 (SaaS)
- **Responsibilities**: Authentication (OIDC/SAML/OAuth2), JWT issuance, RBAC role claims, SSO with Google/Okta, multi-tenant realm isolation
- **Token**: Short-lived JWT (15 min) + refresh token (7 days)
- **Roles**: `PLATFORM_ADMIN`, `ORG_ADMIN`, `DEVELOPER`, `REVIEWER`, `VIEWER`
- **API Contract**:
  - `POST /auth/token` — Login, return JWT
  - `GET /auth/userinfo` — Validate JWT, return user + org + roles
  - `POST /auth/orgs/{id}/members` — Invite user to org

---

### 3.3 Tenant Management Service
**Technology**: Spring Boot + PostgreSQL
- **Responsibilities**: Org lifecycle (create, suspend, delete), tenant config (default LLM model, token quota, plan), namespace provisioning (Kafka topics, DB schema, Qdrant collection)
- **Multi-tenancy hook**: On org creation, provisions:
  1. PostgreSQL schema `tenant_{org_id}`
  2. Kafka topic prefix `t.{org_id}.*`
  3. Qdrant collection `org_{org_id}_knowledge`
  4. Vault namespace `secret/tenants/{org_id}/`
- **API Contract**:
  - `POST /orgs` — Create new organization
  - `GET /orgs/{id}/config` — Fetch tenant config
  - `PUT /orgs/{id}/plan` — Upgrade plan / change quota

---

### 3.4 Workflow Orchestration Service
**Technology**: Python (FastAPI) + Temporal (workflow engine) + Redis
- **Responsibilities**: CRUD for workflow definitions (DAG as JSON/YAML), schedule management (cron triggers), execution lifecycle management, step state machine, retry/timeout policies
- **Core State Machine per Step**:
  ```
  PENDING → RUNNING → SUCCEEDED
                    → FAILED → RETRYING → SUCCEEDED/FAILED
                    → WAITING_HITL → APPROVED → RUNNING
  ```
- **API Contract**:
  - `POST /workflows` — Create workflow definition
  - `POST /workflows/{id}/runs` — Trigger a run
  - `GET /runs/{id}` — Get run status + step trace
  - `POST /runs/{id}/steps/{step_id}/decision` — HITL approve/reject
  - `GET /runs/{id}/stream` — WebSocket live log stream
- **Temporal Activities**: Each step node maps to a Temporal Activity. Workflow (DAG) maps to a Temporal Workflow. Provides durability, replay, and timeout free of charge.

---

### 3.5 Agent Orchestration Service
**Technology**: Python (FastAPI) + AgentScope + Celery
- **Responsibilities**: Multi-agent session management, LLM call routing (model selection, fallback), MCP tool pool management, memory context assembly, HITL gate coordination
- **Agent Loop** (per run):
  ```
  Goal → PlannerAgent[LLM] → DAG Steps
       → ExecutorAgent[Tools via MCP] → Result
       → AnalyzerAgent[LLM] → Feedback
       → (if not done) → loop back to Executor
  ```
- **Memory Strategy**:
  - Short-term: Redis (conversation context per session, TTL 24h)
  - Long-term: Qdrant (embeddings of past runs, codebase, docs)
- **API Contract**:
  - `POST /agents/sessions` — Start new agent session with goal + context
  - `GET /agents/sessions/{id}/messages` — Retrieve agent thought stream
  - `POST /agents/sessions/{id}/message` — Inject human message (HITL feedback)
  - `DELETE /agents/sessions/{id}` — Terminate session

---

### 3.6 Integration Service
**Technology**: Spring Boot + PostgreSQL + Vault
- **Responsibilities**: App connector registry (50+ integrations), OAuth2 PKCE flow management, credential lifecycle (store → rotate → revoke), per-connection health monitoring, tool schema exposure to MCP pool
- **Connection Lifecycle**:
  ```
  Register App → OAuth Redirect → Callback → Token Exchange
  → Encrypt + Store in Vault → Health Check (every 5 min)
  → Expose tools via MCP → Auto-refresh token before expiry
  ```
- **API Contract**:
  - `GET /integrations/apps` — List all available connector apps
  - `POST /integrations/connections` — Initiate OAuth flow
  - `GET /integrations/connections` — List tenant's active connections
  - `DELETE /integrations/connections/{id}` — Revoke connection

---

### 3.7 Event Streaming Service
**Technology**: Apache Kafka + Schema Registry (Confluent / Redpanda)
- **Responsibilities**: Central nervous system. Routes all platform events. Decouples producers from consumers.
- **Topic Naming Convention**: `t.{org_id}.{domain}.{event_type}`
  - e.g., `t.abc123.cicd.build_failed`, `t.abc123.monitoring.anomaly_detected`
- **Core Topics**:

| Topic | Producer | Consumer(s) |
|---|---|---|
| `t.{org}.cicd.events` | Webhook Receiver | Workflow Service, Flink |
| `t.{org}.agent.actions` | Agent Service | Audit Log, Metering |
| `t.{org}.observability.metrics` | OTEL Collector | Flink, TimescaleDB |
| `t.{org}.workflow.run_events` | Workflow Service | Notification, Metering |
| `t.platform.anomalies` | Flink | Workflow Service (trigger) |

- **Schema enforcement**: All events use Avro schemas registered in Schema Registry. Breaking changes rejected.

---

### 3.8 Observability Ingestion Service
**Technology**: Fluent Bit + OpenTelemetry Collector + Flink + OpenSearch / TimescaleDB
- **Responsibilities**: Receive logs/metrics/traces from customer infra, normalize and enrich with tenant/env metadata, fan out to appropriate stores
- **Ingestion Pipeline**:
  ```
  Customer Infra (OTEL SDK / Fluent Bit agent)
    → OTEL Collector (normalize, filter)
    → Kafka (t.{org}.observability.*)
    → Flink Job (enrich, window, aggregate)
    → [Logs → OpenSearch] [Metrics → TimescaleDB] [Traces → Tempo/Jaeger]
    → Anomaly Detector (ML job in Flink)
    → t.platform.anomalies → Workflow Trigger
  ```

---

### 3.9 Rules & Policy Engine
**Technology**: Drools (JVM) or OPA (Open Policy Agent)
- **Responsibilities**: Rule-based incident detection (threshold breaches), workflow trigger policies, governance guardrails (e.g., "never auto-deploy to prod without HITL"), tenant-level configuration of rules
- **Rule Example** (OPA Rego):
  ```rego
  deny[msg] {
    input.action == "deploy"
    input.target_env == "production"
    not input.hitl_approved
    msg := "Production deployments require HITL approval"
  }
  ```
- Works in tandem with AI anomaly detector: rules fire on known thresholds, AI acts on unknown patterns.

---

### 3.10 Notification Service
**Technology**: Spring Boot + Kafka Consumer + SendGrid / Twilio / Slack SDK
- **Responsibilities**: Fan-out notifications from workflow events (run failed, HITL waiting, anomaly detected). Supports Email, Slack, PagerDuty, Webhook channels. Per-tenant notification preferences.
- Consumes `t.{org}.workflow.run_events` and `t.platform.anomalies` from Kafka.

---

### 3.11 Search & Query Service
**Technology**: OpenSearch + FastAPI
- **Responsibilities**: Full-text search across runs, logs, workflows. Semantic search over knowledge base (via Qdrant). Powers the "find similar past incidents" and "search my workflows" features.

---

### 3.12 Metering & Billing Service
**Technology**: Spring Boot + PostgreSQL + Stripe SDK
- **Responsibilities**: Track all billable events (workflow executions, AI tokens, API calls), aggregate into tenant usage buckets, enforce quotas and rate limits, generate invoices, expose usage dashboards
- **Metering Events** consumed from Kafka: `t.{org}.agent.actions`, `t.{org}.workflow.run_events`
- **Quota Enforcement**: Redis-based sliding window counters checked at API Gateway before routing to Agent/Workflow service

---

## 4. End-to-End Data Flow

### Flow A: Event-Triggered AI Workflow

```
[Customer Infra]
  │   Prometheus scrape → OTEL Collector → Kafka t.{org}.observability.metrics
  ▼
[Flink Stream Processing]
  │   Window aggregate (5-min tumbling) → ML anomaly scoring
  │   Score > threshold → emit to t.platform.anomalies
  ▼
[Rules & Policy Engine]
  │   Evaluate: is this actionable? Does a workflow trigger match?
  │   Match found → emit WorkflowTriggerCommand
  ▼
[Workflow Orchestration Service]
  │   Lookup workflow DAG by trigger rule
  │   Create Run, persist to PostgreSQL
  │   Enqueue Temporal WorkflowExecution
  ▼
[Temporal Worker / Workflow Steps]
  │   Step 1: fetch_logs (Integration Service → Datadog connector)
  │   Step 2: AI_analyze_logs (Agent Service → LLM via GPT-4o)
  │   Step 3: HITL Gate → pause, notify team via Notification Service
  │   Step 4 (on approve): create_jira_ticket (Integration Service → Jira connector)
  │   Step 5: post_slack_summary (Integration Service → Slack connector)
  ▼
[State Persistence]
  │   Every step result written to PostgreSQL runs/steps tables
  │   Step I/O stored in S3 (for replay / debugging)
  │   Run event emitted to t.{org}.workflow.run_events → Metering
  ▼
[Feedback Loop]
  AnalyzerAgent scores outcome → embeds summary in Qdrant for future RAG context
```

---

### Flow B: User-Triggered Agent Run (Chat Interface)

```
User: "Analyze the failed build for PR #421 and suggest a fix"
  ▼
Chat Interface → API Gateway → Agent Orchestration Service
  ▼
PlannerAgent (LLM):
  Goal: { fetch PR, fetch CI logs, analyze, suggest fix, create PR comment }
  Output: DAG of tool calls
  ▼
ExecutorAgent:
  Step 1: github.get_pull_request(421) → PR diff
  Step 2: jenkins.get_build_logs(run_id) → log output
  Step 3: LLM(analyze diff + logs, system prompt) → root cause + fix
  Step 4: HITL Check → "Apply fix?" → user approves in UI
  Step 5: github.create_pull_request_comment(fix_suggestion)
  ▼
AnalyzerAgent: Score result, embed into Qdrant knowledge base
  ▼
Streaming response back to Chat UI via WebSocket
```

---

## 5. Multi-Tenancy Strategy

Three models evaluated:

### Option A: Shared DB, Shared Schema
- Single schema, `org_id` FK on every table
- Row-level security (PostgreSQL RLS)
- ✅ Low ops overhead, cheap
- ❌ Risk of noisy neighbor, data leak if RLS bypass, complex queries

### Option B: Shared DB, Schema Per Tenant ⭐ Recommended for MVP → Scale
- Database cluster shared, each tenant gets `tenant_{org_id}` schema
- Connection pooling via PgBouncer (schema-aware routing)
- ✅ Strong isolation, easy backup per tenant, cleaner queries
- ✅ Schema migration per tenant (can canary-deploy schema changes)
- ❌ More complex migration tooling (Flyway with tenant-scoped scripts)

### Option C: Database Per Tenant
- Full isolated RDS/Postgres instance per tenant
- ✅ Strongest isolation, custom SLAs per tenant
- ❌ Very expensive at scale ($N/tenant/month), hard to manage 1000s of DBs
- ✅ Best for enterprise contracts / regulated industries (HIPAA, FedRAMP)

### Recommended Hybrid Strategy

```
Shared DB + Schema-per-tenant for startups/SMB plan
DB-per-tenant on-demand for Enterprise plan (dedicated instance)
```

Tenant metadata (org config, plan) lives in a single shared `public` schema.
Everything else (`workflows`, `runs`, `steps`, `connections`) lives in `tenant_{org_id}` schema.

---

## 6. Technology Stack

### Backend Services

| Service | Language | Framework | Rationale |
|---|---|---|---|
| API Gateway | — | Kong | Industry standard, plugin ecosystem |
| Identity | — | Keycloak | Self-hosted OIDC/SAML, no vendor lock |
| Tenant Mgmt | Java 21 | Spring Boot 3 | Strong typing, mature ecosystem |
| Workflow Orch | Python | FastAPI + Temporal | Temporal for durable execution, Python for agent ecosystem |
| Agent Orch | Python | FastAPI + AgentScope | Python-native agent frameworks |
| Integration | Java 21 | Spring Boot 3 | Strong async HTTP, OAuth2 support |
| Event Streaming | — | Apache Kafka (Redpanda) | Redpanda is Kafka-compatible, faster, simpler ops |
| Stream Processing | — | Apache Flink | Stateful stream processing, ML integration |
| Rules Engine | — | OPA (Go) | Lightweight, declarative, embeddable |
| Notification | Java 21 | Spring Boot 3 | Kafka consumer + SDK integrations |
| Metering | Java 21 | Spring Boot 3 + Stripe | Java for reliable financial computation |
| Search | — | OpenSearch | OSS Elasticsearch fork, no license risk |

### Frontend

| Component | Technology | Rationale |
|---|---|---|
| SPA Framework | Next.js 15 (React) | SSR for dashboard, App Router |
| Component Library | shadcn/ui + Radix | Unstyled, accessible primitives |
| Workflow Designer | React Flow | Production-grade DAG editor |
| Styling | Tailwind CSS | Utility-first, consistent design system |
| State Mgmt | Zustand + React Query | Lightweight global state + server sync |
| Real-time | Native WebSocket + Zustand | Live log streaming, HITL notifications |
| Chat | Vercel AI SDK | Streaming LLM responses to UI |

### Data Stores

| Store | Technology | Used For |
|---|---|---|
| Primary DB | PostgreSQL 16 + PgBouncer | All relational data (per-tenant schema) |
| Cache / Pub-Sub | Redis (Valkey) | Sessions, rate limiting, pub/sub |
| Vector DB | Qdrant | RAG embeddings, semantic search |
| Log Store | OpenSearch | Full-text log search |
| Metrics | TimescaleDB | Time-series metrics, dashboards |
| Traces | Grafana Tempo | Distributed trace storage |
| Object Storage | AWS S3 / MinIO | Step I/O artifacts, exports |
| Secrets | HashiCorp Vault | Tenant credentials, API keys |

### AI / LLM Layer

| Component | Technology |
|---|---|
| LLM Gateway | LiteLLM (unified API for GPT-4o, Claude, Gemini) |
| Agent Framework | AgentScope (Python) |
| Tool Protocol | MCP (Model Context Protocol) |
| Embedding Model | text-embedding-3-small (OpenAI) or bge-large |
| Prompt Versioning | PromptLayer or custom DB-backed registry |

### Infrastructure

| Layer | Technology |
|---|---|
| Container Orchestration | Kubernetes (EKS / GKE) |
| Service Mesh | Istio (mTLS, traffic policies, circuit breaker) |
| CI/CD | GitHub Actions + ArgoCD (GitOps) |
| Observability | OpenTelemetry + Grafana Stack (Loki, Tempo, Mimir) |
| IaC | Terraform + Helm |
| Secret Injection | Vault Agent Sidecar |
| Sandbox Runtime | gVisor (runsc) on Kubernetes |

---

## 7. Scaling Strategy

### Horizontal Scaling by Service Class

| Service Class | Scale Dimension | Strategy |
|---|---|---|
| API Gateway | Request throughput | HPA on RPS, min 3 replicas across AZs |
| Workflow Service | Concurrent DAG executions | HPA on queue depth (Temporal backlog) |
| Agent Service | Active agent sessions | HPA on CPU + memory; GPU node pool for local LLMs |
| Integration Service | Connector call volume | HPA on active connection count |
| Flink Jobs | Event throughput | Flink autoscaler (reactive mode), partition-level parallelism |
| Kafka | Topic throughput | Partition scaling (1 partition = 1 Flink task), broker autoscaling on Redpanda Cloud |
| Qdrant | Vector index size | Qdrant cluster sharding (by org_id) |
| PostgreSQL | Read throughput | PgBouncer + read replicas per tenant tier |

### Kafka Partitioning Strategy
- Partition key = `org_id` → ensures all events for a tenant land on the same partition → preserves ordering within tenant
- Flink reads per-partition → parallelism = `num_partitions / tasks_per_job`
- Replication factor = 3 across AZs

### Database Partitioning
- PostgreSQL table partitioning by `org_id` (range/list) for `runs` and `steps` tables (high-volume)
- Time-based partitioning on log/metric tables + automated partition drop (rolling 90-day window)

---

## 8. Failure Handling & Resilience

### Patterns Applied

| Pattern | Where Applied | Behavior |
|---|---|---|
| **Circuit Breaker** | Integration Service → external APIs | Open after 5 failures in 30s, half-open after 60s |
| **Retry with Backoff** | Temporal Activities | Exponential backoff (1s, 2s, 4s... max 5 attempts) |
| **Dead Letter Queue** | Kafka consumers | Failed events → `t.dlq.{original_topic}` for inspection |
| **Idempotency Keys** | Workflow trigger → run creation | `trigger_event_id` as idempotency key, dedup in Redis |
| **Saga Pattern** | Multi-step agent operations | Compensating transactions (e.g., undo branch creation if PR fails) |
| **Bulkhead** | Agent session pool | Max concurrent sessions per tenant enforced by semaphore |
| **Health Checks** | All services | Kubernetes liveness + readiness probes; Istio health checks |
| **Graceful Degradation** | LLM Gateway | If GPT-4o fails → fallback to Claude → fallback to cached response |

### Temporal Workflow Durability
Temporal persists every workflow step to its internal DB. If a worker crashes mid-step, Temporal replays from last checkpoint on the next worker. No step is lost.

### Chaos Engineering
- Chaos Mesh runs on staging cluster weekly:
  - Kill random Kafka broker → verify consumer rebalancing
  - Kill Flink taskmanager → verify checkpoint recovery
  - Inject network latency to Postgres → verify circuit breaker fires

---

## 9. Extensibility Plan

### Plugin / Connector SDK
Published as `@scopesentinel/connector-sdk` (TypeScript) and `scopesentinel-sdk` (Python).

```python
# Python Connector SDK Example
from scopesentinel.sdk import Connector, Tool, OAuthConfig

class DatadogConnector(Connector):
    name = "datadog"
    oauth = OAuthConfig(auth_url="...", token_url="...", scopes=["monitors:read"])

    @Tool(description="Get monitor status")
    async def get_monitor(self, monitor_id: str) -> dict:
        return await self.client.get(f"/api/v1/monitor/{monitor_id}")
```

SDK connectors are packaged as Docker images, loaded dynamically by the Integration Service via a **connector registry** (stored in PostgreSQL, pulled at runtime).

### Workflow DSL & Import/Export

Every workflow serializes to a portable YAML DSL:

```yaml
version: "1.0"
name: build_failure_remediation
trigger:
  type: kafka_event
  topic: "t.{org_id}.cicd.events"
  filter: { event_type: "build_failed" }
steps:
  - id: fetch_logs
    type: tool
    tool: jenkins.get_build_logs
    inputs: { build_id: "{{ trigger.build_id }}" }
  - id: analyze
    type: agent_step
    agent: AnalyzerAgent
    model: gpt-4o
    prompt_id: "analyze_build_failure_v3"
    inputs: { logs: "{{ steps.fetch_logs.output }}" }
  - id: human_review
    type: hitl
    message: "Review AI analysis for build {{ trigger.build_id }}"
  - id: create_ticket
    type: tool
    tool: jira.create_issue
    inputs:
      summary: "Build failure: {{ trigger.build_id }}"
      description: "{{ steps.analyze.output.root_cause }}"
```

This DSL can be imported/exported as JSON or YAML, enabling:
- **Template Marketplace**: publish community workflows
- **GitOps Workflows**: store workflow definitions in Git, deploy via ArgoCD
- **Cross-tenant Sharing**: import a workflow template from the marketplace into your org

### Marketplace Architecture (Future)
- **Publisher**: Any org can package a workflow/skill/connector as a marketplace listing
- **Registry**: Listing stored in a central `marketplace` PostgreSQL schema
- **Distribution**: Listings are cryptographically signed → consumers verify signature before install
- **Monetization**: Per-use credits or subscription via Stripe Connect (revenue share model)

---

## 10. Developer-Centric Use Cases (Implementation Examples)

### Use Case 1: Build Failure → Root Cause → Ticket

```
Trigger: Jenkins build_failed webhook
→ Step 1: jenkins.get_build_logs → 5000 lines of logs
→ Step 2: LLM(chunk logs, extract error, classify failure type)
→ Step 3: RAG search Qdrant("similar build failures last 30 days")
→ Step 4: LLM(synthesize root cause + suggested fix)
→ Step 5: HITL — "Create Jira ticket with this analysis?" [Approve/Edit]
→ Step 6: jira.create_issue(summary, description, auto-assign to last committer)
→ Step 7: slack.post_message("#builds channel with summary")
```

### Use Case 2: Metrics Anomaly → Auto-Remediation

```
Trigger: Flink detects p99 latency spike (>500ms for 5min)
→ Step 1: datadog.get_metrics(service, last_15min)
→ Step 2: LLM(analyze metrics pattern, identify service bottleneck)
→ Step 3: Rules Engine: "Is auto-scale approved for this service?"
→ Step 4a (auto-scale approved): kubernetes.scale_deployment(+2 replicas)
→ Step 4b (not approved): HITL — "Scale up api-gateway?" + pagerduty.alert on-call
→ Step 5: Monitor for 10min → validate recovery
→ Step 6: AnalyzerAgent scores outcome → update Qdrant knowledge
```

### Use Case 3: PR Review Agent

```
Trigger: GitHub pull_request.opened webhook
→ Step 1: github.get_pull_request_diff(pr_number)
→ Step 2: RAG search Qdrant("coding standards, past review comments")
→ Step 3: LLM(analyze diff for: style violations, security issues, test coverage)
→ Step 4: snyk.scan_code(repo, branch) → security vulnerabilities
→ Step 5: LLM(synthesize review summary with inline comments)
→ Step 6: github.create_review_comment(pr_number, file, line, comment)
→ Step 7: If critical security issue → block merge + notify lead
```

---

## 11. Observability of the Platform Itself

Every service emits **OpenTelemetry** signals:

| Signal | Storage | Dashboard |
|---|---|---|
| Metrics | Grafana Mimir | Service RPM, error rate, p99 latency |
| Logs | Grafana Loki | Structured JSON logs, correlated by trace_id |
| Traces | Grafana Tempo | Distributed trace per workflow run |

Every **workflow run** has a `run_id` that propagates as an OTEL trace context through every service call, LLM invocation, and tool call — making the entire execution fully traceable end-to-end.

**AI Cost Tracking**: LLM Gateway emits `{org_id, model, prompt_tokens, completion_tokens, latency}` per call → Metering Service aggregates → surfaced in tenant billing dashboard.

---

## 12. Deployment Architecture

```
Production:
  ├── AWS EKS (primary region: us-east-1)
  │   ├── System Namespace: kong, keycloak, vault, kafka, flink
  │   ├── Platform Namespace: all microservices (HPA-managed)
  │   ├── Agent Namespace: agent workers (GPU node pool optional)
  │   └── Sandbox Namespace: gVisor runtime class (ephemeral pods)
  ├── AWS EKS (replica region: eu-west-1, active-active)
  ├── RDS Aurora PostgreSQL (multi-AZ, read replicas)
  ├── ElastiCache Redis (cluster mode)
  ├── Redpanda Cloud (Kafka-compatible, multi-region)
  └── CloudFront CDN (Next.js static assets)

Staging:
  └── Single-region EKS, shared DB, Redpanda single-node

Dev:
  └── Docker Compose (all services local, SQLite option)
```

### Blue-Green Deployments
- ArgoCD manages all service deployments (GitOps)
- Canary: traffic split 5% → 25% → 100% with Istio weighted routing
- Automatic rollback: if error rate > 1% detected by Grafana alert → ArgoCD triggers rollback

---

## 13. Security & Compliance

| Area | Control |
|---|---|
| **Transport** | TLS 1.3 enforced everywhere (Istio mTLS between services) |
| **Secrets** | Vault Agent Sidecar injects secrets as env vars at pod start |
| **LLM Inputs** | PII scrubber middleware before any data hits LLM API |
| **Sandbox** | gVisor (`runsc`) for all code execution — syscall interception |
| **Audit Log** | Immutable append-only log in PostgreSQL (`audit_events` table, WAL-archived to S3) |
| **Compliance** | SOC2 Type II (Vanta automates evidence collection) |
| **Scanning** | Snyk in CI pipeline, Trivy for container image vulnerability scanning |
| **RBAC** | Enforced at API Gateway (Kong plugin) + service layer (Spring Security / FastAPI middleware) |

---

## Summary: Architecture Decision Log

| Decision | Choice | Rationale |
|---|---|---|
| Workflow engine | Temporal | Durable execution, replay, saga — removes retry/state boilerplate |
| Agent framework | AgentScope | Python-native, MCP-compatible, active |
| Multi-tenancy | Schema-per-tenant | Balance of isolation and ops simplicity |
| Message broker | Redpanda (Kafka API) | Kafka-compatible, simpler ops, lower latency |
| Stream processor | Flink | Stateful, ML-capable, handles millions of events/sec |
| Vector DB | Qdrant | Fast filtered ANN search, Rust-native performance |
| Frontend | Next.js + React Flow | SSR performance + best-in-class DAG editor |
| Secrets | HashiCorp Vault | Industry standard, no vendor lock |
| Service mesh | Istio | mTLS, traffic policies, observability out-of-box |
