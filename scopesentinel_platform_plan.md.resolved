# ScopeSentinel — Platform Vision & Implementation Roadmap

## What We're Building

ScopeSentinel is an **agentic workflow orchestration platform** in the same space as Gumloop — but with a **developer-first, software-delivery focus**. Where Gumloop is generalist (marketing, sales, support), ScopeSentinel goes deep on the **software development lifecycle**: Jira → Code → Review → Deploy.

The platform allows teams to:
- Build and customize **agentic workflows** visually or via config
- Connect to **80+ tools** (Jira, GitHub, Slack, Linear, Notion, etc.) via MCP or native integrations
- Define **Human-in-the-Loop checkpoints** for governing what the AI is allowed to do autonomously
- Trigger workflows via **Webhooks**, **schedules**, or **manual runs**
- Monitor all agent activity with **full trace visibility**

---

## High-Level Architecture

```mermaid
graph TD
    subgraph "User-Facing Layer"
        UI["🖥️ Web UI\n(Workflow Designer + Dashboard)"]
        API["🔌 REST/WebSocket API\n(FastAPI)"]
        WH["🔔 Webhook Triggers\n(Jira, GitHub, Slack)"]
    end

    subgraph "Orchestration Layer"
        ORCH["🧠 Workflow Orchestrator\n(DAG Executor)"]
        HITL["🛑 HITL Gateway\n(Approval Engine)"]
        STATE["📋 State Manager\n(Run Logs, Artifacts)"]
    end

    subgraph "Agent Layer"
        PLANNER["📐 Planner Agent\n(LLM: GPT-4o / Claude)"]
        CODER["💻 Coder Agent\n(LLM: GPT-4o)"]
        CUSTOM["🤖 Custom Agents\n(User-defined)"]
    end

    subgraph "Tool & Integration Layer"
        MCP["🔧 MCP Server Pool\n(Dynamic Registry)"]
        APPS["📦 App Connectors\n(Jira, GitHub, Linear, Slack, Notion...)"]
        SANDBOX["🔒 Sandbox Runtime\n(Docker/gVisor)"]
    end

    subgraph "Knowledge Layer"
        VECTDB["🗄️ Vector DB\n(Qdrant)"]
        RAG["📚 RAG Engine\n(Repo + Docs Indexer)"]
    end

    subgraph "Infra"
        DB["🐘 PostgreSQL\n(Workflows, Users, Orgs)"]
        QUEUE["📨 Task Queue\n(Celery + Redis)"]
        VAULT["🔐 Secret Store\n(Vault / AWS Secrets)"]
    end

    UI --> API
    WH --> API
    API --> ORCH
    ORCH --> PLANNER & CODER & CUSTOM
    ORCH --> HITL
    ORCH --> STATE
    PLANNER & CODER --> MCP
    MCP --> APPS
    CODER --> SANDBOX
    PLANNER & CODER --> RAG
    RAG --> VECTDB
    STATE --> DB
    ORCH --> QUEUE
    MCP --> VAULT
```

---

## Core Concepts

| Concept | Description |
|---|---|
| **Workflow** | A DAG of steps: Triggers → Agents → Tools → HITL Gates → Outputs |
| **Agent** | An LLM-powered node that reasons and calls Tools |
| **Tool / App Connector** | An integration with an external service (Jira, GitHub, etc.) |
| **Run** | A single execution instance of a Workflow with full state/logs |
| **HITL Gate** | A pause point requiring human approval before proceeding |
| **Skill** | A reusable, parameterized sub-workflow (e.g., "Triage Bug Ticket") |

---

## Implementation Iterations

### 🔵 Iteration 1 — MVP (Hardened CLI)
> **Goal:** Make the current Python CLI production-quality and demo-able.

**What you have now (exit state):**
- [main.py](file:///Users/kvelayudham/Personal%20Github/ScopeSentinel/main.py) CLI orchestrator
- Planner + Coder Agents (GPT-4o)
- MCP registry via [mcp_servers.yaml](file:///Users/kvelayudham/Personal%20Github/ScopeSentinel/mcp_servers.yaml) (Jira + GitHub tools)
- Docker sandbox with self-correction loop
- HITL terminal gate

**What to add:**
- Persistent run logs to a local SQLite DB
- Clean error handling, structured logging, retry logic
- `--dry-run` mode (plan only, no code)
- Dockerize the whole CLI for easy sharing

---

### 🟡 Iteration 2 — FastAPI Control Plane + Persistent Storage
> **Goal:** Turn the CLI into a callable service. The brain lives in a server now.

**Key Deliverables:**
- `POST /runs` — trigger a workflow by ticket ID
- `GET /runs/{id}` — poll status and logs
- `GET /runs/{id}/plan` — fetch the generated plan
- `POST /runs/{id}/approve` — HITL approval endpoint
- PostgreSQL for runs, steps, users, organizations
- Async background workers (Celery + Redis) for non-blocking runs
- WebSocket stream for real-time log tailing

**Architecture shift:** [main.py](file:///Users/kvelayudham/Personal%20Github/ScopeSentinel/main.py) logic moves into a `WorkflowService`. Agents become stateless, called by the service.

---

### 🟠 Iteration 3 — Web UI (Monitoring Dashboard)
> **Goal:** Give the agent a face. Teams can trigger and observe runs without touching a terminal.

**Key Deliverables:**
- **Run Dashboard**: List of all runs (status, ticket, PR link)
- **Run Detail Page**: Step-by-step trace, plan viewer, log stream
- **HITL Panel**: Review plan/diff in UI, click Approve / Reject / Modify
- **Workflow Trigger Form**: Enter ticket ID, pick config, hit Run
- **App Connections Screen**: OAuth-connect Jira, GitHub, Slack

**Tech Stack:** Next.js (React) + TailwindCSS, real-time via WebSocket

---

### 🔴 Iteration 4 — Visual Workflow Designer + App Marketplace
> **Goal:** Gumloop-level capability. Users build custom workflows visually.

**Key Deliverables:**
- **Node-based Workflow Designer** (React Flow): Drag agents, tools, conditionals, HITL gates into a DAG
- **App Marketplace**: 20+ pre-built connectors (Linear, Notion, Confluence, PagerDuty, Datadog, Slack, etc.)
- **Skill Library**: Reusable workflow templates (e.g., "Bug Triage", "Feature Branch", "On-call Alert")
- **Workflow YAML DSL**: Every visual workflow serialized to a portable YAML definition

**Workflow YAML Example:**
```yaml
name: jira_to_pr
trigger:
  type: webhook
  source: jira
  event: issue_transitioned
  filter: { status: "In Progress" }
steps:
  - id: plan
    agent: PlannerAgent
    inputs: { ticket_id: "{{ trigger.issue.key }}" }
  - id: approve_plan
    type: hitl
    message: "Review the plan for {{ trigger.issue.key }}"
  - id: code
    agent: CoderAgent
    inputs: { plan: "{{ steps.plan.output }}", ticket_id: "{{ trigger.issue.key }}" }
  - id: create_pr
    tool: github.create_pull_request
    inputs: { branch: "sentinel/{{ trigger.issue.key }}" }
```

---

### 🟣 Iteration 5 — Knowledge Layer + Enterprise Features
> **Goal:** Handle brownfield (legacy) repos and enterprise security.

**Key Deliverables:**
- **RAG Engine**: Ingest & index repos into Qdrant. Agents can search codebase context.
- **Multi-Tenancy**: Full org isolation (workspaces, knowledge bases, secrets per org)
- **Secret Manager**: HashiCorp Vault / AWS Secrets Manager integration. Zero LLM exposure of credentials.
- **Audit Log**: Immutable log of every agent action, every approval, every tool call
- **Role-Based Access Control (RBAC)**: Admin, Developer, Reviewer roles per org
- **Greenfield Scaffolding**: Agent scaffolds new repo from scratch (DDD/MVC with CI/CD boilerplate)

---

## Epics & Stories

### Epic 1 — CLI Hardening & Productionization *(Iteration 1)*
| Story | Description |
|---|---|
| 1.1 | Structured logging with context (run_id, ticket_id, step) on every log line |
| 1.2 | Persistent run state to local SQLite — survive crashes and `--resume` |
| 1.3 | `--dry-run` flag: generate plan only, skip coding and PRs |
| 1.4 | Global error handler with graceful MCP client cleanup |
| 1.5 | Unit tests for all agents, tools, sandbox runner |
| 1.6 | Docker Compose file to run ScopeSentinel as a container |

---

### Epic 2 — FastAPI Control Plane *(Iteration 2)*
| Story | Description |
|---|---|
| 2.1 | `POST /api/runs` — accept `{ ticket_id, workflow_config }`, return `run_id` |
| 2.2 | Background task runner (Celery + Redis) for async workflow execution |
| 2.3 | `GET /api/runs/{id}` — returns status, steps, logs |
| 2.4 | `POST /api/runs/{id}/decision` — HITL approve/reject/modify endpoint |
| 2.5 | PostgreSQL schema: `orgs`, `users`, `workflows`, `runs`, `steps`, `hitl_events` |
| 2.6 | WebSocket endpoint `/ws/runs/{id}` for real-time log streaming |
| 2.7 | JWT-based auth (signup, login, API key generation) |
| 2.8 | `GET /api/runs/{id}/plan` — expose generated plan as structured JSON |

---

### Epic 3 — Monitoring UI *(Iteration 3)*
| Story | Description |
|---|---|
| 3.1 | Setup Next.js app with shadcn/ui component library |
| 3.2 | Run List page: table of runs with status badges, ticket links, timestamps |
| 3.3 | Run Detail page: step-by-step trace, collapsible log viewer |
| 3.4 | Live log streaming panel (WebSocket connected, auto-scrolling) |
| 3.5 | HITL Review Panel: display plan + diff, confirm/reject buttons |
| 3.6 | Trigger Workflow form: enter ticket ID, select config, start run |
| 3.7 | App Connections screen: OAuth connection flows for Jira and GitHub |

---

### Epic 4 — App Connectors & Marketplace *(Iteration 4)*
| Story | Description |
|---|---|
| 4.1 | Abstract `AppConnector` interface with `list_tools()` and `call_tool()` |
| 4.2 | Native connectors: Linear, Confluence, Notion, Slack |
| 4.3 | Native connectors: PagerDuty, Datadog, Sentry |
| 4.4 | App Marketplace UI: searchable grid of available apps |
| 4.5 | OAuth flow for each app (store encrypted tokens per org) |
| 4.6 | Connector health check + reconnect logic |

---

### Epic 5 — Visual Workflow Designer *(Iteration 4)*
| Story | Description |
|---|---|
| 5.1 | React Flow canvas: drag-and-drop agent, tool, trigger, and HITL gate nodes |
| 5.2 | Node configuration sidebar: edit inputs, map outputs between nodes |
| 5.3 | Workflow YAML DSL spec and serializer/deserializer |
| 5.4 | "Save Workflow" and "Run Workflow" buttons |
| 5.5 | Workflow library / template gallery (pre-built workflows like "Jira → PR") |
| 5.6 | Trigger configurator: Webhook (Jira, GitHub), Schedule (cron), Manual |

---

### Epic 6 — Knowledge Layer & RAG *(Iteration 5)*
| Story | Description |
|---|---|
| 6.1 | Qdrant setup (Docker Compose + seeded with example repo) |
| 6.2 | Repo ingestion pipeline: clone, chunk, embed, upsert into Qdrant |
| 6.3 | `search_codebase(query)` tool exposed to CoderAgent |
| 6.4 | Brownfield Mode: agent automatically retrieves relevant context before coding |
| 6.5 | Re-indexing on new PRs / pushes (GitHub webhook triggers re-ingest) |

---

### Epic 7 — Multi-Tenancy & Enterprise Security *(Iteration 5)*
| Story | Description |
|---|---|
| 7.1 | Org model: isolate workflows, runs, knowledge bases, secrets per org |
| 7.2 | RBAC: Admin, Developer, Reviewer roles with enforced permission checks |
| 7.3 | HashiCorp Vault integration: store and inject credentials without LLM exposure |
| 7.4 | Immutable audit log: every agent action, tool call, and HITL event recorded |
| 7.5 | Multi-stage HITL: Plan Approval → Commit Approval → Deploy Approval gates |
| 7.6 | SSO integration (Google OAuth, Okta/SAML for enterprise) |

---

## Technology Stack

| Layer | Technology |
|---|---|
| **Orchestrator / Agents** | Python, AgentScope, GPT-4o / Claude Sonnet |
| **Tool Integration** | MCP (Model Context Protocol), [mcp_servers.yaml](file:///Users/kvelayudham/Personal%20Github/ScopeSentinel/mcp_servers.yaml) registry |
| **API Server** | FastAPI, Pydantic v2 |
| **Background Jobs** | Celery + Redis |
| **Database** | PostgreSQL (primary), SQLite (dev/MVP) |
| **Real-time** | WebSocket (FastAPI native) |
| **Frontend** | Next.js (React), TailwindCSS, shadcn/ui, React Flow |
| **Sandbox** | Docker / gVisor (ephemeral containers) |
| **Vector DB** | Qdrant |
| **Secrets** | HashiCorp Vault (Iteration 5) |
| **Infra** | Docker Compose (dev), Kubernetes + Helm (prod) |

---

## Iteration Summary

| Iteration | Theme | Output |
|---|---|---|
| **1** | CLI Hardening | Robust, tested, Dockerized CLI |
| **2** | FastAPI Control Plane | Callable API, async workers, DB |
| **3** | Monitoring UI | Web dashboard, live logs, HITL panel |
| **4** | Designer + Marketplace | Visual builder, 20+ app connectors |
| **5** | Enterprise | RAG, multi-tenancy, Vault, RBAC |
