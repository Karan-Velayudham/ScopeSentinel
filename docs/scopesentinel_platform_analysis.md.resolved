# ScopeSentinel — Product & Platform Analysis
## Role: Product & Platform Analyst | Date: March 2026

---

## Executive Summary

ScopeSentinel's vision is a compelling one: a **multi-tenant, event-driven, AI-augmented workflow automation platform** for autonomous software delivery. The enterprise architecture document defines a mature, microservices-grade system with Temporal, Kafka, Flink, Qdrant, and a full agent runtime loop. The current implementation, however, is an **early-stage monolith-in-a-single-API** that has built the right core primitives—but most of the connective tissue between them is either absent or misaligned. The gap between vision and implementation is not a quality problem; it is a **sequencing and completeness problem** that is entirely recoverable with a clear functional roadmap.

---

## Part 1: Current State Analysis

### 1.1 Architecture Map (What Exists Today)

```
┌────────────────────────────────────────────────────────────────────┐
│  Frontend (Next.js 15, App Router)                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │
│  │Dashboard │ │Workflows │ │  Agents  │ │Integr'ns │ │  Runs  │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └───┬────┘  │
└───────┼─────────────┼───────────┼─────────────┼───────────┼───────┘
        │  REST/JSON  │           │             │           │
┌───────▼─────────────▼───────────▼─────────────▼───────────▼───────┐
│  FastAPI Monolith (services/api)                                    │
│  /api/runs  /api/workflows  /api/agents  /api/connectors  /health  │
│                     Single PostgreSQL + Redis                       │
└───────────────────────────────────┬────────────────────────────────┘
                                    │ Temporal dispatch (runs only)
┌───────────────────────────────────▼────────────────────────────────┐
│  Agent Runtime (services/agent-runtime)                             │
│  PlannerAgent → ExecutorAgent → CoderAgent (Temporal workflow)     │
│  MCP pool (GitHub, Jira connectors via YAML config)                │
└────────────────────────────────────────────────────────────────────┘
        Trigger Engine & Webhook Receiver: stubs / empty
```

**What is built and functional:**
| Component | Status | Notes |
|---|---|---|
| FastAPI API skeleton | ✅ Working | Routers for runs, workflows, agents, connectors, health |
| PostgreSQL data model | ✅ Working | Org, User, Workflow, WorkflowRun, RunStep, HitlEvent, InstalledConnector |
| Temporal dispatch (runs) | ✅ Working | `POST /api/runs` dispatches to Temporal task queue |
| HITL Signal (decision) | ✅ Working | Signals `hitl-decision-signal` to Temporal workflow handle |
| WebSocket log streaming | ✅ Working | Redis pub/sub → WebSocket for real-time logs |
| YAML DSL for workflows | ✅ Working | Validated, stored, versioned, import/export |
| Workflow templates | ✅ Working | 5 hardcoded system templates |
| Agent CRUD | ✅ Working | Create/Read/Update/Delete agents with identity/model/tools |
| Connector catalog | ✅ Partial | Static catalog in registry, mock "install" with config_json |
| Mock auth (dev) | ✅ Working | API-key based auth for local development |
| Dashboard stats | ✅ Working | Real metrics from DB (active, executed, HITL, success rate) |
| Agent runtime (PlannerAgent, CoderAgent) | ✅ Working | Python agents with MCP pool, Temporal activities |
| Frontend UI (all screens) | ✅ Working | Next.js pages for all entities |

**What is NOT built or is a stub:**
| Component | Status | Notes |
|---|---|---|
| Real OAuth flows for connectors | ❌ Missing | [install_connector](file:///Users/kvelayudham/Personal%20Github/ScopeSentinel/services/api/routers/connectors.py#48-89) just dumps raw config_json; no OAuth PKCE |
| Credential storage in Vault | ❌ Missing | Credentials stored as plaintext JSON in PostgreSQL |
| Trigger Engine | ❌ Stub | `services/trigger-engine` is empty |
| Webhook Receiver | ❌ Stub | `services/webhook-receiver` is empty |
| Kafka event backbone | ❌ Missing | No Kafka producer/consumer anywhere in codebase |
| Stream processing (Flink) | ❌ Missing | No Flink jobs |
| Rules & Policy Engine | ❌ Missing | No OPA or Drools integration |
| Multi-tenancy (schema isolation) | ❌ Missing | All tables share a flat schema; `org_id` FK only |
| Vector DB / RAG (Qdrant) | ❌ Missing | No embedding, no semantic search |
| Notification Service | ❌ Missing | No Slack/email/PagerDuty notifications |
| Search Service | ❌ Missing | No full-text search over runs/logs |
| Metering & Billing | ❌ Missing | Token fields on DB but no aggregation, no Stripe |
| Keycloak / real OIDC | ❌ Missing | Mock auth only; Keycloak not active |
| Workflow → Run linkage (execution) | ❌ Missing | Runs are Jira-ticket-triggered only; workflow_id is nullable and not used in dispatch |
| Agent → Workflow integration | ❌ Missing | Agents are registry entries; not referenced in workflow execution |
| Visual DAG designer | ❌ Missing | Frontend has YAML text input; no ReactFlow canvas |
| Activity Chart on Dashboard | ❌ Missing | Marked as "Future Integration" placeholder |
| HITL notification & inbox | ❌ Missing | No user is notified when HITL is needed |

---

### 1.2 Entity-Level Current State

#### **Runs**
A `WorkflowRun` is the only truly functional entity today. It can be created via `POST /api/runs` with a `ticket_id`, dispatched to Temporal, tracked through state transitions (`PENDING → RUNNING → WAITING_HITL → SUCCEEDED/FAILED`), and observed via WebSocket. Each run has `RunStep` children and `HitlEvent` decisions.

**Gaps:** Runs are only triggered via the API (manual), never via webhooks or events. The `workflow_id` FK exists but is always null — a run is not yet a "workflow run" in the functional sense. Runs are coupled to Jira tickets as input, making the trigger model implicit and narrow.

#### **Workflows**
A `Workflow` is a stored YAML DSL definition with CRUD, versioning, and import/export. Templates exist. The DSL is structurally validated.

**Gaps:** Workflows are **never executed** — no code path connects a workflow definition to a run dispatch. The `POST /api/runs` route only takes a `ticket_id` and calls the hardcoded `AgentWorkflow` Temporal workflow. The workflow designer is a YAML text editor, not a visual canvas. There's no trigger binding (e.g., "when GitHub webhook fires, run workflow X").

#### **Agents**
An `Agent` is a named persona with `identity` (system prompt), `model`, and a `tools` list stored as JSON.

**Gaps:** Agents are a **registry only** — they are not referenced during workflow execution. The Temporal worker uses hardcoded `PlannerAgent` and `CoderAgent` classes, not the database-defined agents. There is no way to compose a workflow step that says "use agent X" and have it resolve to a database agent record.

#### **Integrations (Connectors)**
A static connector catalog is defined per connector class. Connectors can be "installed" by posting a raw config object. The `InstalledConnector` table stores `config_json`.

**Gaps:** No OAuth flows — credentials are passed raw by the client and stored unencrypted in PostgreSQL. Connector config is opaque (no schema per connector type). The MCP pool in the agent runtime reads from `mcp_servers.yaml`, completely separate from the installed connectors in the database — **no bridge between the two systems**.

---

## Part 2: Identified Gaps & Inconsistencies

### 2.1 The "Disconnected Quadrant" Problem

The four core entities (Runs, Workflows, Agents, Integrations) are each independently built but **none are wired together in the execution path**. The platform vision requires:

```
Trigger → Workflow (DAG) → Steps → Agents (with Tools via Connectors) → Run
```

The current reality is:

```
Manual API call → Hardcoded Temporal workflow → Hardcoded PlannerAgent → Hardcoded CoderAgent
                                                        (ignores DB Workflows)
                                                        (ignores DB Agents)
                                                        (ignores DB Connectors/OAuth)
```

### 2.2 Critical Functional Gaps (Prioritized)

| # | Gap | Business Impact | Severity |
|---|---|---|---|
| G1 | Workflows are never executed | Core product promise broken | 🔴 Critical |
| G2 | Agents not wired into execution | Agent builder is decorative | 🔴 Critical |
| G3 | OAuth not implemented (mock install only) | Integration platform not functional | 🔴 Critical |
| G4 | Credentials stored in plaintext PostgreSQL | Security risk, blocks production | 🔴 Critical |
| G5 | No event/webhook trigger system | Can't do event-driven automation | 🟠 High |
| G6 | No HITL notification | Users don't know when action is needed | 🟠 High |
| G7 | No multi-tenant isolation (schema-per-tenant) | Can't go to market with multiple orgs | 🟠 High |
| G8 | Dashboard has empty chart panels | Trust gap; product feels unfinished | 🟡 Medium |
| G9 | No visual DAG designer | Productivity gap vs. competitors | 🟡 Medium |
| G10 | Connector ↔ MCP pool not bridged | Runtime can't use installed integrations | 🔴 Critical |
| G11 | No run attribution to workflow | Metrics and traceability broken | 🟠 High |
| G12 | No token/cost aggregation | Billing is impossible | 🟡 Medium |
| G13 | No real Keycloak/OIDC in production auth | Security gap; roles not enforced | 🟠 High |
| G14 | Trigger Engine is empty service | Event-driven flows impossible | 🟠 High |

### 2.3 Architectural Inconsistencies

1. **Two separate MCP configurations**: The API's `InstalledConnector` table and the agent runtime's `mcp_servers.yaml` are completely disconnected. Tools registered in one system are invisible to the other.

2. **Run trigger is hardcoded to Jira tickets**: `TriggerRunRequest.ticket_id` makes Jira a first-class concept in the run model, limiting the platform's generality. The architecture envisions event-agnostic triggers.

3. **Agent model treats `tools` as a string list**: `Agent.tools_json` stores tool names as a JSON array of strings, but there's no resolution mechanism — you can't look up which connector provides a tool named `"github.create_pr"`.

4. **Workflow DSL and Temporal workflow types are separate**: The `WorkflowDSL` schema defines step types `["trigger", "agent", "tool", "condition", "hitl", "delay"]`, but the only Temporal workflow is `AgentWorkflow` (Jira-specific). There's no DAG interpreter that reads DSL steps and maps them to Temporal activities.

5. **`analysis_passed` and `analysis_feedback` on RunDetailResponse** suggest a feedback/reflection loop, but no `AnalyzerAgent` equivalent is wired in — the fields are always null.

---

## Part 3: Proposed Functional Architecture

### 3.1 Redefined Core Entities

#### **Workflow** (the blueprint)
A Workflow is a versioned, visual DAG definition stored as a YAML DSL. It defines:
- A **trigger** (webhook event, cron, manual, inbound message)
- An ordered set of **Steps**, each of which is one of:
  - `agent` – invoke a named Agent with a goal and context
  - `tool` – call a specific connector tool (e.g., `github.create_pr`)
  - `hitl` – pause and request human decision
  - `condition` – branch on a runtime value
  - `delay` – wait N seconds
- **Input/output bindings** between steps using template expressions (e.g., `{{ steps.plan.output.summary }}`)

#### **Agent** (the AI actor)
An Agent is a persona definition stored in the database, composed of:
- **Identity** – a system prompt defining behavior, expertise, and constraints
- **Model** – an LLM selection (resolved via LiteLLM at runtime)
- **Tools** – references to connector tool IDs (e.g., `["github:get_pr", "jira:create_issue"]`)
- **Memory mode** – short-term (session) or long-term (Qdrant-backed)

An agent is invoked by a workflow `agent` step. The runtime resolves the agent from DB, builds the system prompt, assembles available tools from the connector pool, and runs the LLM loop.

#### **Run** (the execution instance)
A Run is the live execution of a Workflow (or ad-hoc agent session). It has:
- Parent `workflow_id` (nullable for ad-hoc)
- `trigger_event` – the payload that initiated the run (e.g., webhook body, user message)
- Ordered list of **RunSteps** mirroring the workflow's step definitions
- **HITL events** at steps of type `hitl`
- Token/cost metering per step
- Live log stream via WebSocket

#### **Integration / Connection** (the tool provider)
A Connection is an authorized link between the platform and an external service. It has:
- `connector_id` – identifies the connector type (GitHub, Jira, Slack, etc.)
- OAuth tokens or API keys — **stored encrypted in Vault** (never in PostgreSQL)
- A **health status** checked on a background schedule
- **Tool schema** — the list of tool functions the connector exposes to the MCP pool

---

### 3.2 Expected User Journeys

#### Journey 1: Connect an Integration
```
User navigates to Integrations → clicks "Connect GitHub"
→ Platform initiates OAuth PKCE redirect to GitHub
→ GitHub redirects back with authorization code
→ Platform exchanges code for access token
→ Token encrypted and stored in Vault under `secret/tenants/{org_id}/github`
→ InstalledConnector record created in DB (no credentials, only references)
→ Connector tools registered in MCP pool for this org
→ User returns to Integrations page: GitHub shows "Connected ✓"
```

#### Journey 2: Build and Publish a Workflow
```
User navigates to Workflows → clicks "New Workflow"
→ Visual DAG canvas (React Flow) opens
→ User drags in trigger node: "GitHub PR Opened"
→ User adds agent node: "Code Reviewer" (selects from saved agents)
→ User adds hitl node: "Approve review comment?"
→ User adds tool node: "GitHub: Post Comment"
→ User sets data bindings: review output → comment body
→ User clicks "Save" → WorkflowCreateRequest POSTed; YAML DSL generated from canvas
→ User clicks "Activate" → workflow registered as a trigger listener
→ Dashboard shows workflow as "Active"
```

#### Journey 3: Event-Triggered Automated Run
```
GitHub fires pull_request.opened webhook
→ Webhook Receiver routes to Trigger Engine
→ Trigger Engine matches event to active workflow "PR Review Agent"
→ Trigger Engine emits WorkflowTriggerCommand to Kafka topic
→ Workflow Service consumes command, creates WorkflowRun, dispatches to Temporal
→ Temporal executes DAG:
    Step 1 (agent: Code Reviewer): resolves Agent from DB, calls LLM with PR diff
    Step 2 (hitl: Approval): run pauses to WAITING_HITL; notification sent to user
    Step 3 (tool: Post Comment): calls github connector with review body
→ Each step result written to RunStep; live stream via WebSocket
→ Run completes: SUCCEEDED; metrics updated in dashboard
```

#### Journey 4: Manual Ad-Hoc Run
```
User navigates to Runs → clicks "New Run"
→ Selects workflow template (or picks existing workflow)
→ Fills trigger inputs (e.g., PR number, Jira ticket ID)
→ Clicks "Run" → POST /api/runs with workflow_id and trigger data
→ Run detail page opens, live log stream starts
→ If HITL step triggered: notification badge appears; user reviews and approves in UI
```

#### Journey 5: HITL Review
```
Run reaches hitl step → status transitions to WAITING_HITL
→ Notification sent via Slack / email (Notification Service)
→ Dashboard "Needs Approval" widget shows count
→ User clicks notification → Runs detail page, HITL panel shows:
    - AI output from previous step
    - Approve / Reject / Modify (with feedback box) buttons
→ User clicks Approve → POST /api/runs/{id}/decision
→ Temporal receives signal, continues workflow execution
```

---

### 3.3 Data Flow & System Boundaries

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ INGRESS LAYER                                                                     │
│  ┌──────────────────┐  ┌─────────────────────┐  ┌──────────────────────────┐    │
│  │  Next.js Frontend│  │  Webhook Receiver    │  │  Cron / Manual Trigger   │    │
│  │  (users / HITL)  │  │  (GitHub, Jira, PD) │  │  (dashboard, API keys)   │    │
│  └────────┬─────────┘  └──────────┬──────────┘  └──────────────┬───────────┘    │
└───────────┼────────────────────── │ ──────────────────────────── │ ──────────────┘
            │ REST + WS             │ POST /webhooks/...            │
            ▼                       ▼                               ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│ PLATFORM API (FastAPI)                                                             │
│  /api/workflows  /api/runs  /api/agents  /api/connectors  /api/auth              │
│                        + JWT / API-key auth middleware                            │
└─────────┬─────────────────────────────────────────────────────────────┬──────────┘
          │ Workflow CRUD / OAuth initiation                             │ Run dispatch
          ▼                                                              ▼
┌─────────────────────────┐                                   ┌──────────────────────┐
│  TRIGGER ENGINE          │                                   │  TEMPORAL SERVER      │
│  Listen: Kafka events    │                                   │  Durable execution    │
│  Match: active workflows │                                   │  Retry / replay       │
│  Emit: WorkflowRun       │───────────────────────────────────▶  DAG interpreter     │
└─────────────────────────┘                                   └──────────┬───────────┘
                                                                         │ activities
                                                              ┌──────────▼───────────┐
                                                              │  AGENT RUNTIME        │
                                                              │  PlannerAgent         │
                                                              │  ExecutorAgent        │
                                                              │  AnalyzerAgent        │
                                                              │  MCP tool pool        │
                                                              └──────────┬───────────┘
                                                                         │ tool calls
                                                              ┌──────────▼───────────┐
                                                              │  INTEGRATION SERVICE  │
                                                              │  OAuth tokens (Vault) │
                                                              │  GitHub, Jira, Slack  │
                                                              └──────────────────────┘
          │                                                              │
          │ Events                                                       │ Run events
          ▼                                                              ▼
┌─────────────────────────┐                                   ┌──────────────────────┐
│  KAFKA EVENT BUS         │                                   │  NOTIFICATION SERVICE │
│  t.{org}.cicd.*          │                                   │  Slack / Email / PD  │
│  t.{org}.workflow.*      │                                   │  HITL alerts          │
│  t.{org}.agent.*         │                                   └──────────────────────┘
└─────────────────────────┘
          │
          ▼
┌─────────────────────────┐
│  DATA LAYER              │
│  PostgreSQL (relational) │
│  Redis (cache / pub-sub) │
│  Vault (credentials)     │
│  Qdrant (RAG/vectors)    │
│  S3/MinIO (artifacts)    │
└─────────────────────────┘
```

---

### 3.4 Integration Patterns

#### OAuth 2.0 PKCE (for user-delegated connectors: GitHub, Jira, Slack)
```
1. POST /api/connectors/{id}/oauth/init
   → Generates state param, stores in Redis (TTL 5min)
   → Returns OAuth authorization_url to frontend
2. Frontend redirects user to external OAuth provider
3. Provider redirects to GET /api/connectors/oauth/callback?code=&state=
   → Validates state from Redis (CSRF protection)
   → Exchanges code for access_token + refresh_token
   → Encrypts tokens; stores in Vault: secret/tenants/{org_id}/{connector_id}
   → Creates InstalledConnector DB record (no credentials in DB)
   → Redirects user back to frontend Integrations page
4. Background health-checker (every 5 min) validates token + preemptively refreshes
```

#### API Key / Service Account (for Datadog, PagerDuty, CI systems)
```
1. POST /api/connectors/{id}/install with { api_key, base_url }
   → Validates key by calling provider test endpoint
   → Encrypts key; stores in Vault
   → Creates InstalledConnector DB record
```

#### Event-Driven Trigger (Webhooks)
```
1. User activates a workflow with trigger type "webhook"
2. Platform generates a unique signed webhook URL: /webhooks/{org_id}/{workflow_id}/{token}
3. User configures this URL in their external system (GitHub, Jira, etc.)
4. Inbound event hits Webhook Receiver:
   → Validates HMAC signature
   → Publishes to Kafka: t.{org_id}.{domain}.events
5. Trigger Engine consumes event, matches to active workflow, creates Run
```

#### MCP Tool Registration
```
When connector is installed:
1. Load connector class from registry
2. Inspect @Tool-decorated methods to build tool schema
3. Register tools in org-scoped MCP pool under connector namespace
4. Agent steps can reference tools as: "{connector_id}:{tool_name}"
```

---

### 3.5 Multi-Tenancy & Extensibility

#### Multi-Tenancy Model (Recommended Progression)
| Phase | Strategy | When |
|---|---|---|
| **Now** | Shared schema, `org_id` FK on every table | MVP, <100 orgs |
| **Phase 2** | Schema-per-tenant (`tenant_{org_id}`) in PostgreSQL | Growth, >100 orgs |
| **Phase 3** | DB-per-tenant on request | Enterprise contracts |

**Immediate changes needed:** All queries already scope by `org_id` — this is correct. The gap is credential isolation (use Vault namespaces per org: `secret/tenants/{org_id}/`) and Kafka topic namespacing (already specified in enterprise architecture as `t.{org_id}.*`).

#### Extensibility Surface
1. **Connector SDK**: Define a base `Connector` class with `@Tool` decorator → any developer can package a new integration
2. **Workflow DSL import/export**: Already implemented — enables GitOps workflows
3. **Marketplace (future)**: Signed workflow templates and connectors published by community
4. **Custom Agent identities**: Already implemented in DB — enables per-org persona creation

---

## Part 4: Recommendations

### Priority Tier 1 — Fix the Execution Core (Weeks 1–3)

These are blocking the core product promise:

**R1: Wire Workflow Definitions into Run Execution**
- `POST /api/runs` should accept `workflow_id` (optional, falls back to default AgentWorkflow)
- The Temporal `AgentWorkflow` implementation should read the workflow DSL from PostgreSQL and dynamically interpret each step as a Temporal activity
- Start with supporting step types: `agent`, `tool`, `hitl`

**R2: Resolve DB Agents in the Runtime**
- The Temporal worker should accept an `agent_id` per step, fetch the `Agent` record from PostgreSQL during activity execution, and use `Agent.identity` as the system prompt and `Agent.model` for LLM selection

**R3: Bridge Connectors to MCP Pool**
- On startup (or on connector install), the agent runtime should query `GET /api/connectors/installed` for the org and register the corresponding tools in the MCP pool
- Tool IDs in `Agent.tools_json` should follow `"connector_id:tool_name"` notation

**R4: Implement OAuth for GitHub and Jira (the two most-used connectors)**
- Add `/api/connectors/{id}/oauth/init` and `/api/connectors/oauth/callback` endpoints
- Use Redis for state management, Vault for token storage
- Replace the current mock `install_connector` with real OAuth for these two

### Priority Tier 2 — Close the Event Loop (Weeks 4–6)

**R5: Implement Trigger Engine**
- Start with a simple FastAPI service (no Kafka yet) that polls for GitHub/Jira webhook events
- Register active workflows as trigger listeners
- Progress to Kafka-backed event bus as volume grows

**R6: Implement Webhook Receiver**
- Accept inbound webhooks from GitHub, Jira, PagerDuty
- Validate HMAC signatures
- Route to Trigger Engine

**R7: Implement HITL Notifications**
- When a run enters `WAITING_HITL`, emit a notification
- Minimum viable: Slack message via installed Slack connector
- UI: populate the "Needs Approval" dashboard widget with real clickable HITL items

### Priority Tier 3 — Fill in the Platform Layer (Weeks 7–12)

**R8: Add Visual Workflow Designer**
- Replace the YAML text editor with a React Flow canvas
- Each node type maps to a DSL step type
- Serialize the canvas state to YAML DSL on save

**R9: Real Authentication (Keycloak)**
- Complete the Keycloak integration for production auth
- Enforce RBAC roles (`ADMIN`, `DEVELOPER`, `REVIEWER`, `VIEWER`) at the router level
- Gate HITL decisions behind the `REVIEWER` role

**R10: Vault Integration for Credential Storage**
- Replace `config_json` in `InstalledConnector` with Vault references
- Never store credentials in PostgreSQL

**R11: Activity Timeline on Dashboard**
- Replace the "Future Integration" placeholder chart with a real run timeline
- Group by date/hour, color-coded by status

**R12: Token/Cost Aggregation**
- Aggregate per-step token counts from RunStep to WorkflowRun
- Surface in the run detail page and dashboard

### Priority Tier 4 — Scale & Observability (Future)

- Kafka full event bus integration
- Flink stream processing + anomaly detection
- Qdrant RAG memory for AnalyzerAgent
- Schema-per-tenant migration
- Metering & billing via Stripe

---

## Summary: Gap-to-Recommendation Traceability

| Gap | Recommendation | Priority |
|---|---|---|
| G1: Workflows never executed | R1: Wire workflow DSL → Temporal activities | Tier 1 |
| G2: Agents not in execution path | R2: Resolve DB agents in runtime | Tier 1 |
| G3: OAuth not implemented | R4: Implement OAuth for GitHub/Jira | Tier 1 |
| G4: Plaintext credentials in DB | R10: Vault integration | Tier 3 |
| G5: No event trigger system | R5, R6: Trigger Engine + Webhook Receiver | Tier 2 |
| G6: No HITL notification | R7: HITL notifications via Slack | Tier 2 |
| G7: No multi-tenant isolation | Schema-per-tenant (Phase 2 migration plan) | Tier 4 |
| G8: Empty dashboard charts | R11: Activity timeline | Tier 3 |
| G9: No visual DAG designer | R8: React Flow canvas | Tier 3 |
| G10: Connector ↔ MCP not bridged | R3: Bridge connectors to MCP pool | Tier 1 |
| G11: Runs not attributed to workflows | R1: workflow_id in run dispatch | Tier 1 |
| G12: No cost aggregation | R12: Token/cost display | Tier 3 |
| G13: No real OIDC | R9: Keycloak auth | Tier 3 |
| G14: Trigger Engine empty | R5: Trigger Engine implementation | Tier 2 |

---

*Analysis based on codebase review as of March 2026. All line references are to `main` branch.*
