# ScopeSentinel — Visual Workflow Designer Ideation
## Grounded in Mockup Analysis | March 2026

---

## Mockup Analysis — Key Observations

The mockup reveals an **n8n-style visual node canvas** with a structured node palette. Three critical design decisions to absorb:

1. **Nodes ARE the DSL.** Users never write YAML. The canvas serializes to YAML DSL behind the scenes. The node palette is the primary creation surface.

2. **MCP is the integration badge.** Every integration node in the mockup carries an `MCP` badge — this is not decorative. It signals that the connector exposes its tools via the Model Context Protocol, making all its tools auto-discoverable by Agent nodes.

3. **Separation of concerns is visual.** Core logic (Input/Output/Router), AI reasoning (Ask AI/Agent/Extract Data), and Integrations are distinct visual groupings — not just categories but different visual treatments.

---

## Node Taxonomy

The mockup's left panel maps to exactly **5 node groups** plus a **Frequently Used** shortcut shelf. Here is the complete taxonomy grounded in that structure and mapped to ScopeSentinel's platform primitives.

---

### Group 1: Core Nodes
*"Essential components for workflow construction"*

These are structural nodes — they don't call external systems or LLMs. They define the shape and flow of the DAG.

| Node | Icon Style | Purpose | Maps to DSL |
|---|---|---|---|
| **Input** | ↓ Arrow | Entry point for a run; declares INPUT schema fields | [trigger](file:///Users/kvelayudham/Personal%20Github/ScopeSentinel/services/api/routers/runs.py#119-156) block |
| **Output** | ↑ Arrow | Terminal success node; captures final result | End of DAG |
| **Router** | Fork | Condition-based branching; evaluates an expression and routes to one of N branches | `condition` step |
| **Merge** | Join | Waits for all incoming parallel branches to complete | `parallel.join_strategy` |
| **Set Variable** | { } | Store a computed value under a named key for downstream steps | `outputs` binding |
| **Extract Data** | Scissors | Extract a specific field from a prior step's output using a JSONPath selector | Template expression |
| **Delay** | Clock | Pause execution for a configurable duration | `delay` step |
| **Note** | Sticky | Non-executable canvas annotation | Metadata only |

**Visual design:** Neutral palette (grey/white), rectangular with rounded corners, compact.

---

### Group 2: Using AI
*"Leverage AI for various tasks"*

AI nodes invoke LLMs. Each node represents a distinct reasoning pattern. They share the same underlying LiteLLM gateway but offer different interaction models.

| Node | Icon Style | Purpose | Maps to DSL | Key Config |
|---|---|---|---|---|
| **Ask AI** | 💬 Chat bubble | Single-turn LLM prompt → structured or free-form response | [agent](file:///Users/kvelayudham/Personal%20Github/ScopeSentinel/services/api/routers/agents.py#89-99) step (1 iteration) | Prompt template, output schema, model |
| **Agent** | 🤖 Figure | Full ReAct loop with tool access; runs until goal is satisfied or max iterations | [agent](file:///Users/kvelayudham/Personal%20Github/ScopeSentinel/services/api/routers/agents.py#89-99) step (multi-turn) | agent_id, goal, tools, memory_mode, max_iterations |
| **Classify** | 🏷️ Tag | Input → {category, confidence, rationale} | [agent](file:///Users/kvelayudham/Personal%20Github/ScopeSentinel/services/api/routers/agents.py#89-99) step w/ classification prompt | Categories list, confidence threshold |
| **Summarize** | 📄 Compress | Long content → concise summary with configurable length | [agent](file:///Users/kvelayudham/Personal%20Github/ScopeSentinel/services/api/routers/agents.py#89-99) step w/ summarize prompt | Max tokens, format (bullets/prose) |
| **Extract Structured** | 🔍 Magnifier | Unstructured text → typed JSON matching a schema | [agent](file:///Users/kvelayudham/Personal%20Github/ScopeSentinel/services/api/routers/agents.py#89-99) step w/ extraction prompt | Output JSON schema |
| **Compare** | ⚖️ Scale | Evaluate two inputs and produce a judgment | [agent](file:///Users/kvelayudham/Personal%20Github/ScopeSentinel/services/api/routers/agents.py#89-99) step | Comparison criteria, output format |

**Visual design:** Purple/violet palette — visually distinct from core nodes. AI nodes glow subtly on hover to signal LLM cost.

**Important design rule:** Agent nodes show a live token counter badge during execution. Users see cost before approving.

---

### Group 3: Triggers
*"Automate actions based on events"*

Trigger nodes are placed at the **start** of every workflow. A workflow must have exactly one Trigger node (or a `manual` Input node). Trigger nodes are not re-executable mid-flow.

| Node | Icon Style | Event Source | Config Fields |
|---|---|---|---|
| **Webhook Trigger** | 🌐 Globe | Inbound HTTP POST from any system | Source connector, HMAC secret, event filter |
| **Cron Trigger** | ⏰ Clock | Time-based schedule | Cron expression, timezone |
| **Manual Trigger** | 👆 Cursor | User-initiated via UI or API | Input schema (becomes form in UI) |
| **Event Trigger** | 📡 Antenna | Internal Kafka event | Topic pattern, JMESPath filter |
| **Message Trigger** | 💬 Chat | Chat interface or Slack message | Channel, keyword filter |
| **App Event Trigger** | 🔗 Link | Event from a connected integration (e.g., "GitHub PR Opened") | Connector, event type |

**Visual design:** Green palette. Always placed left-most on canvas. Non-deletable if it is the only trigger.

**App Event Trigger detail:** When a user selects this node, they pick a connected integration → a list of available events from that connector populates. This replaces the need for users to know webhook URL structures.

---

### Group 4: Your Custom Nodes
*"Create your own nodes to automate your workflows"*

Custom Nodes are org-defined, packaged as Docker images or Python functions, registered in the platform's connector registry. They appear in this section after publishing.

| Sub-type | Description |
|---|---|
| **Code Node** | Inline Python snippet (sandboxed); input/output type-safe |
| **HTTP Request Node** | Generic REST call to any URL with configurable auth |
| **Custom Connector Node** | Org-packaged connector with `@Tool` methods, published to org registry |

**Visual design:** Orange palette. A "Build Custom Node" CTA at the bottom of this section opens the SDK docs.

---

### Group 5: Subflows
*"Automate your workflows with subflows"*

Subflow nodes embed another saved workflow as a callable step — like a function call. The parent workflow passes inputs; the subflow returns outputs.

| Node | Purpose |
|---|---|
| **Subflow** | Reference any saved workflow in the org as a step |
| **Error Handler** | A subflow invoked automatically when any step in the parent fails |

**Design rule:** Subflows can be nested up to 3 levels deep to prevent infinite cycles. Circular subflow references are rejected at save time.

---

### Group 6: Integrations (MCP-Badged)
*The section visible at the bottom of the mockup's left panel*

Every integration node maps to an **installed connector**. If the connector is not installed (OAuth not completed), the node is grayed out with a "Connect" CTA inline.

The `MCP` badge is load-bearing: it means the connector's tools are exposed via the Model Context Protocol and are **automatically available to any Agent node** in the same workflow — without explicit wiring.

#### Integration Node Model

Each integration node renders as a **two-level expandable**:

```
┌─────────────────────────────────────────────┐
│  🔗 GitHub                          [MCP]   │
│  "Manage repositories, PRs, issues"    >    │
└─────────────────────────────────────────────┘
          ↓ (expand)
┌─────────────────────────────────────────────┐
│  🔗 GitHub                          [MCP]   │
├─────────────────────────────────────────────┤
│  ○ Get Pull Request                        │
│  ○ Create Pull Request                     │
│  ○ List Issues                             │
│  ○ Create Issue                            │
│  ○ Post Review Comment                     │
│  ○ Get Repository                          │
│  ○ Trigger Workflow (Actions)              │
└─────────────────────────────────────────────┘
```

Each tool in the expansion is a draggable node. When dragged to canvas, it becomes a **Tool step** pre-configured with `connector_id` and `tool_name`.

#### Full Integration Catalog (with MCP tools)

| Connector | MCP | Category | Key Tools |
|---|---|---|---|
| **GitHub** | ✅ | VCS | get_pr_diff, create_pr, post_review_comment, list_issues, create_issue, trigger_action |
| **GitLab** | ✅ | VCS | get_mr_diff, create_mr, list_issues, create_issue, trigger_pipeline |
| **Jira** | ✅ | Issue Tracker | get_issue, create_issue, update_issue, transition_issue, add_comment, search_issues |
| **Linear** | ✅ | Issue Tracker | get_issue, create_issue, update_issue, list_teams, add_comment |
| **Slack** | ✅ | Messaging | post_message, create_channel, list_channels, upload_file, post_thread_reply |
| **Discord** | ✅ | Messaging | post_message, create_thread, list_channels |
| **Datadog** | ✅ | Monitoring | get_metrics, list_monitors, get_events, create_event, mute_monitor |
| **Prometheus** | ✅ | Monitoring | query_metrics, query_range, list_alerts |
| **PagerDuty** | ✅ | Alerting | trigger_incident, resolve_incident, list_oncall, create_note |
| **Jenkins** | ✅ | CI/CD | trigger_build, get_build_status, get_build_logs, list_jobs |
| **HTTP Request** | ❌ | Generic | Generic REST (no specific tools; user configures URL/method/auth) |

#### MCP Tool Auto-Discovery for Agent Nodes

When an **Agent node** is placed on the canvas, a "Tools" panel in its config sidebar shows all MCP tools available from connected integrations. The user **checks/unchecks** which tools the agent may use. This is visual representation of `Agent.tools_json`.

```
Agent: "Code Reviewer"
┌────────────────────────────────┐
│  Available Tools               │
│  ☑ github:get_pull_request_diff│
│  ☑ github:post_review_comment  │
│  ☐ github:create_pull_request  │
│  ☐ jira:create_issue           │
│  ☑ slack:post_message          │
└────────────────────────────────┘
```

---

## Frequently Used Shelf

The "Frequently Used" section in the mockup is a **dynamic shortcut shelf** — not a static list. It shows the 6 most-dragged nodes for the current user (or org). Defaults are:

| Node | Why it's default |
|---|---|
| Ask AI | Most common single-step AI use case |
| Input | Every workflow starts with one |
| Extract Data | Used in nearly every multi-step flow |
| Output | Every workflow ends with one |
| Agent | Core AI actor |
| Router | Required for any conditional flow |

---

## Canvas UX Model

### Toolbar (Top Bar — Exact Mockup Match)

| Element | Behavior |
|---|---|
| **Workflow Name** | Editable inline; auto-saved |
| **⭐ Bookmark** | Star/favorite the workflow |
| **Add Interface** | Opens a form builder — turns `Input` trigger into a user-facing form with labels, types, defaults |
| **Add Trigger** | Opens trigger selection modal (replaces the default Manual trigger) |
| **👤 Agent Profile** | Assigns a default agent persona to the entire workflow |
| **Share** | Generate a shareable read-only link or invite collaborators |
| **Save ▾** | Save | Save as Template | Export YAML |
| **▶ Run** | Manual run; opens input form if the workflow has an Input trigger |

### Canvas Behaviors

| Behavior | Detail |
|---|---|
| **Drag to add** | Drag any node from the palette onto the dot-grid canvas |
| **Connect nodes** | Click output port → drag to input port of next node; creates an edge |
| **Edge = data flow** | Hovering an edge shows the data expression it carries (e.g., `{{ steps.analyze.outputs.summary }}`) |
| **Node config sidebar** | Clicking any node opens a right-side panel with its config form — no YAML editing required |
| **Inline preview** | After a run, each node shows its output inline on the canvas (green = success, red = failed) |
| **Ask AI for help** | Bottom-center button; opens an AI assistant that can suggest the next node, debug a config, or generate a whole subflow from a text description |
| **Zoom & pan** | Standard 75% default; +/- and pinch-to-zoom; minimap toggle |

---

## Node Config Sidebar (Per Node Type)

Each node opens a right panel when selected. Key panels:

### Trigger Node Config
```
Trigger: Webhook
┌─────────────────────────────────┐
│ Source Connector  [GitHub    ▾] │
│ Event Type        [PR Opened ▾] │
│ HMAC Validation   [Enabled   ▾] │
│ Event Filter      [----------- ]│
│   {{ action == 'opened' }}      │
│                                 │
│ [Copy Webhook URL]              │
└─────────────────────────────────┘
```

### Agent Node Config
```
Agent: Analyzer
┌─────────────────────────────────┐
│ Agent    [Select from registry▾]│
│  → Or create new agent          │
│ Goal     [Text area ____________]│
│          [{{ step bindings }}   ]│
│ Model    [gpt-4o             ▾] │
│ Memory   [Session / Long-term ▾]│
│ Max Iter [10                   ]│
│ Tools    [✅ github:get_pr_diff ]│
│          [✅ slack:post_message ]│
│ On Fail  [abort / retry / skip ▾]│
└─────────────────────────────────┘
```

### Integration Tool Node Config
```
Tool: GitHub → Create Issue
┌─────────────────────────────────┐
│ Connector  GitHub (Connected ✓) │
│ Tool       create_issue         │
│                                 │
│ Inputs                          │
│  title   [{{ steps.ai.outputs.title }}]│
│  body    [{{ steps.ai.outputs.body }} ]│
│  labels  ["bug", "ai-generated"]│
│  assignee[{{ workflow.config.assignee}}]│
│                                 │
│ Outputs                         │
│  issue_id   → steps.create.q.id│
│  issue_url  → steps.create.url  │
└─────────────────────────────────┘
```

### HITL Node Config
```
HITL Gate: Approval Required
┌─────────────────────────────────┐
│ Message  [Text area ____________]│
│ Display  [+ Add field]          │
│  • Label [AI Summary]           │
│    Value [{{ steps.ai.summary }}]│
│ Notify   [+ Add channel]        │
│  • Slack → #ops                 │
│  • Email → reviewer@org.com     │
│ Timeout  [24 hrs          ]     │
│ On Expire[abort / auto-approve▾]│
└─────────────────────────────────┘
```

---

## Node-to-DSL Mapping (Under the Hood)

When the user saves, the canvas serializes to YAML DSL. This mapping is deterministic:

| Canvas Node | Generated DSL step type |
|---|---|
| Input / Trigger | `trigger:` block |
| Ask AI | `type: agent` with `max_iterations: 1` |
| Agent | `type: agent` with full config |
| Extract Data | Implicit `outputs:` binding on prior step |
| Router | `type: condition` |
| Merge | `type: parallel` with `join_strategy: all` |
| Delay | `type: delay` |
| Integration Tool | `type: tool` |
| Subflow | `type: subflow` with `workflow_id` |
| HITL Gate | `type: hitl` |
| Output | Terminal node marker |

YAML is **never shown to the user by default**. A "View YAML" toggle exists in the Save dropdown for advanced users and GitOps export.

---

## Implementation Gap Summary (Visual Designer)

| Gap | What's Needed |
|---|---|
| No visual canvas | React Flow canvas with custom node components per type |
| No node palette | Left panel component with search, categories, drag-to-canvas |
| No connection validation | Edge rules: output type must match input type; no back-edges (DAG enforced) |
| No node config sidebar | Right panel that opens on node click with type-specific form |
| No canvas → DSL serializer | Canvas state → YAML DSL on Save |
| No DSL → canvas deserializer | YAML DSL → canvas state on Load (for existing workflows) |
| No inline run output | Post-execution, each node renders output/error inline |
| No "Add Interface" form builder | Input trigger → user-facing form builder |
| No MCP tool auto-discovery in Agent node | Query installed connectors → populate tools checklist |
| No integration status on node | Gray out + "Connect" CTA for uninstalled connectors |

---

## Implementation Priority

| P | Component | Why |
|---|---|---|
| P0 | React Flow canvas shell + node drag | Without canvas, nothing works |
| P0 | 6 core node components (Input, Output, Router, Agent, Tool, HITL) | Covers 95% of use cases |
| P0 | Canvas → DSL serializer | Connects designer to backend |
| P1 | Node config sidebar (per type) | Makes nodes configurable |
| P1 | MCP tool selector in Agent node | Makes AI nodes useful |
| P1 | Integration node with tool expansion | Enables no-code tool calls |
| P2 | DSL → canvas deserializer | Required for editing saved workflows |
| P2 | Inline run output on nodes | Makes execution visible |
| P2 | "Add Interface" form builder | Turns workflows into user-facing apps |
| P3 | "Ask AI for help" assistant | Productivity multiplier |
| P3 | Custom Code node (sandboxed) | Power users |
| P3 | Subflow node | Reusable modular workflows |
