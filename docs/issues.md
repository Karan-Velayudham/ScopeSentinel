# ScopeSentinel — Issue Backlog (Phase 1–3 QA Audit)

> **Audited:** 2026-03-21 | 14 issues total | Ordered by severity

---

## 🔴 Critical

### [C-1] Runs page displays hardcoded mock data
- **File:** `frontend/src/app/runs/page.tsx`
- **Severity:** Critical
- **Category:** Mock Data / Feature Gap
- **Reproduce:** Navigate to `/runs` in the UI — rows from `MOCK_RUNS` show up, not real database records.
- **Root Cause:** `const MOCK_RUNS = [...]` hardcoded constant is used directly; no `useEffect` or API call exists in the component.
- **Impact:**
  - Real run data is completely invisible to users.
  - The HITL banner on the dashboard links to mocked run IDs that don't exist in the DB.
  - "Trigger New Run" button renders but does nothing (not wired up).
- **Fix:**
  ```tsx
  const [runs, setRuns] = useState<any[]>([])
  useEffect(() => {
    fetch('http://localhost:8000/api/runs/', {
      headers: { 'X-Api-Key': '<user-api-key>' }
    })
      .then(r => r.json())
      .then(data => setRuns(data.items || []))
  }, [])
  ```
- **Related Issues:** m-1 (no shared auth client), C-3 (run trigger broken)

---

### [C-2] Connector API — missing `await` on async session queries
- **File:** `services/api/routers/connectors.py` — lines 31, 60
- **Severity:** Critical
- **Category:** Backend Bug / Runtime Error
- **Reproduce:** Call `GET /api/connectors/installed` or `POST /api/connectors/{id}/install` with any data in the DB.
- **Root Cause:** `SessionDep` is an async SQLModel session. `session.exec(stmt)` must be `await`ed before calling `.all()` or `.first()`.
- **Impact:** Both endpoints throw `AttributeError` at runtime the moment real queries execute. The Marketplace "Install" flow silently fails.
- **Buggy code:**
  ```python
  items = session.exec(stmt).all()       # line 31 — crashes
  existing = session.exec(stmt).first()  # line 60 — crashes
  ```
- **Fix:**
  ```python
  items = (await session.exec(stmt)).all()
  existing = (await session.exec(stmt)).first()
  ```
- **Test to add:** `test_connectors.py::test_list_installed_connectors` and `test_install_connector`

---

### [C-3] Temporal server missing from local docker-compose
- **File:** `docker-compose.yml`
- **Severity:** Critical
- **Category:** Infrastructure Gap
- **Reproduce:** Run `POST http://localhost:8000/api/runs/` with a valid API key and ticket ID → returns `HTTP 500`.
- **Root Cause:** `runs.py` calls `Client.connect(os.getenv("TEMPORAL_ADDRESS", "localhost:7233"))` but no Temporal service is defined in `docker-compose.yml`. Connection is refused → exception → 500.
- **Impact:** Every single workflow run trigger fails. The entire agentic pipeline is effectively dead in local dev.
- **Fix:** Add the following service to `docker-compose.yml`:
  ```yaml
  temporal:
    image: temporalio/auto-setup:latest
    ports:
      - "7233:7233"
    environment:
      - DB=postgresql
      - DB_PORT=5432
      - POSTGRES_USER=scopesentinel
      - POSTGRES_PWD=scopesentinel
      - POSTGRES_SEEDS=postgres
    depends_on:
      postgres:
        condition: service_healthy
  ```
  Also add `TEMPORAL_ADDRESS=temporal:7233` to the `api` service's environment block.
- **Related Issues:** M-1 (decision endpoint docstring mismatch)

---

## 🟡 Major

### [M-1] runs.py decision endpoint has stale Celery docstring
- **File:** `services/api/routers/runs.py` — lines 233–237
- **Severity:** Major
- **Category:** Documentation / Code Quality
- **Reproduce:** Read the docstring of `submit_decision()`.
- **Root Cause:** When we migrated from Celery → Temporal, the function body was updated but the docstring was not.
- **Current docstring says:**
  > "The Celery worker task is paused on a Redis pub/sub channel. This endpoint writes the HitlEvent to DB and publishes to that channel so the worker can resume."
- **Actual behaviour:** Sends a `hitl-decision-signal` to the live Temporal workflow handle via `handle.signal(...)`.
- **Impact:** Misleads developers on how HITL works; wrong mock target in tests (`aioredis` vs `temporalio.client.Client`).
- **Fix:** Replace docstring with accurate Temporal description.

---

### [M-2] Visual Designer "Test Run" hardcodes ticket_id = SCRUM-8
- **File:** `frontend/src/components/workflow-designer/Designer.tsx` — line 110
- **Severity:** Major
- **Category:** UI Bug / Usability
- **Reproduce:** Open any workflow in `/workflows/{id}/designer` → click "Test Run" → alert says run started for SCRUM-8 only.
- **Root Cause:**
  ```ts
  body: JSON.stringify({ ticket_id: "SCRUM-8", dry_run: false })
  ```
- **Impact:** Users cannot test their workflow against a different ticket. The feature is non-functional for real use-cases.
- **Fix:** Show a `<Dialog>` prompting for `ticket_id` input before triggering. Use `dry_run: true` as the default safe option.

---

### [M-3] `GET /api/workflows/templates` has no authentication guard
- **File:** `services/api/routers/workflows.py` — line 53–54
- **Severity:** Major
- **Category:** Security / API Consistency
- **Reproduce:** `curl http://localhost:8000/api/workflows/templates` (no API key) → returns 200 with data.
- **Root Cause:** Handler signature is `async def get_templates():` — no `CurrentUserDep` parameter unlike every other endpoint in the router.
- **Impact:** Unauthenticated access to template data. Inconsistent security posture. Templates could expose org-specific data if made dynamic later.
- **Fix:**
  ```python
  async def get_templates(current_user: CurrentUserDep):
  ```

---

### [M-4] Only 2 of 5 planned workflow templates implemented
- **File:** `services/api/routers/workflows.py` — lines 60–82
- **Severity:** Major
- **Category:** Feature Gap
- **Reproduce:** `GET /api/workflows/templates` returns only 2 items.
- **Root Cause:** Only "Jira to PR Pipeline" and "Build Failure Triager" were implemented; 3 more were planned.
- **Missing templates:**
  1. PR Review Agent
  2. Incident Responder
  3. Deploy Validator / Post-deploy Check
- **Impact:** Reduced out-of-box value; template picker in UI looks sparse.
- **Fix:** Add 3 more `WorkflowResponse` objects in `get_templates()`. For full MVP, migrate templates to YAML files loaded from `services/api/templates/*.yaml`.

---

### [M-5] Only 4 connectors implemented (10+ planned)
- **File:** `services/api/connectors/apps/`
- **Severity:** Major
- **Category:** Feature Gap
- **Reproduce:** `GET /api/connectors/available` returns 4 items only.
- **Implemented:** `github.py`, `slack.py`, `jira.py`, `datadog.py`
- **Missing per plan:**
  - VCS: GitLab
  - Issue Tracking: Linear
  - Chat: Discord, PagerDuty
  - CI/CD: Jenkins, CircleCI, GitHub Actions
  - Observability: Kubernetes, Prometheus
- **Impact:** Marketplace looks sparse; promised feature coverage not met.
- **Fix:** Add stub files following `BaseConnector` pattern. Each only needs `info()`, `list_tools()`, and `call_tool()` returning mocked values for MVP.

---

### [M-6] No "Uninstall Connector" API endpoint
- **File:** `services/api/routers/connectors.py`
- **Severity:** Major
- **Category:** Missing Feature / API Gap
- **Reproduce:** After installing a connector, there is no way to remove it via API or UI.
- **Root Cause:** `DELETE /api/connectors/{connector_id}/uninstall` was never implemented.
- **Impact:** Users are permanently stuck with any connector they install. "Configure Settings" button in the Marketplace is a dead placeholder.
- **Fix:**
  ```python
  @router.delete("/{connector_id}/uninstall", status_code=204)
  async def uninstall_connector(connector_id: str, session: SessionDep, current_user: CurrentUserDep):
      stmt = select(InstalledConnector).where(
          InstalledConnector.org_id == current_user.org_id,
          InstalledConnector.connector_id == connector_id
      )
      existing = (await session.exec(stmt)).first()
      if not existing:
          raise HTTPException(404, "Connector not installed")
      await session.delete(existing)
      await session.commit()
  ```
- **Related Issues:** m-3 (no uninstall UI)

---

### [M-7] Epic 3.4.8 — Execution Replay on designer canvas not implemented
- **File:** `frontend/src/components/workflow-designer/Designer.tsx`
- **Severity:** Major
- **Category:** Feature Gap (planned epic item)
- **Reproduce:** Open a designer for a workflow that has completed runs — there is no way to visualise which steps were executed.
- **Root Cause:** Epic 3.4.8 was deferred and never implemented; only items 3.4.1–3.4.7 exist.
- **Impact:** Users cannot debug failed workflows visually. Key differentiating feature missing.
- **Fix approach:**
  1. Add a "Replay Run" button in the Designer toolbar.
  2. Prompt for a `run_id` (or derive from query param `?replay=<run_id>`).
  3. Fetch `GET /api/runs/{run_id}` → extract `steps[]` with their `status`.
  4. Match step names to node labels; apply a `highlight` CSS class or override node `style` based on status (green=SUCCEEDED, red=FAILED, grey=SKIPPED).

---

## 🟢 Minor

### [m-1] Frontend API calls missing authentication headers
- **File:** `frontend/src/app/workflows/page.tsx` — line 12; also in `integrations/page.tsx`
- **Severity:** Minor
- **Category:** Code Quality / Security Hygiene
- **Reproduce:** Deploy frontend in an environment where session-based seeded keys are not pre-configured → all data fetches return 401 silently.
- **Root Cause:** Each page does ad-hoc `fetch('http://localhost:8000/...')` without a shared utility that injects auth headers.
- **Impact:** Inconsistent auth handling across pages; will break in staging/production without hardcoded seeded keys.
- **Fix:** Create `frontend/src/lib/api-client.ts`:
  ```ts
  export const apiFetch = (path: string, options?: RequestInit) =>
    fetch(`http://localhost:8000${path}`, {
      ...options,
      headers: { 'X-Api-Key': process.env.NEXT_PUBLIC_API_KEY || 'dev-key-1', ...options?.headers },
    })
  ```
  Use `apiFetch` everywhere instead of raw `fetch`.

---

### [m-2] Missing `__init__.py` in connector packages
- **File:** `services/api/connectors/` and `services/api/connectors/apps/`
- **Severity:** Minor
- **Category:** Code Quality / Conventions
- **Reproduce:** Python import tools and some IDEs fail to resolve the package correctly without `__init__.py`.
- **Root Cause:** Files were not created when the connector SDK was scaffolded.
- **Impact:** May cause issues with certain static analysis tools, coverage reporting, and IDE imports.
- **Fix:** `touch services/api/connectors/__init__.py services/api/connectors/apps/__init__.py`

---

### [m-3] No "Disconnect/Uninstall" UI flow in Marketplace
- **File:** `frontend/src/app/integrations/page.tsx`
- **Severity:** Minor
- **Category:** UI/UX Gap
- **Reproduce:** Install any connector → card shows "Configure Settings" button → clicking it does nothing; no way to remove the connector.
- **Root Cause:** The button is a placeholder; no handler or API call is wired. Depends on M-6 being fixed first.
- **Impact:** Connector installs are irreversible from the UI.
- **Fix:** After M-6 is implemented, replace "Configure Settings" with:
  - "Configure Settings" → opens a modal for credential update
  - "Remove" → calls `DELETE /api/connectors/{id}/uninstall` and refreshes the list

---

### [m-4] Alembic `script.py.mako` template file is missing
- **File:** `services/api/migrations/script.py.mako`
- **Severity:** Minor
- **Category:** Developer Tooling / DX
- **Reproduce:** `cd services/api && alembic revision --autogenerate -m "test"` → `FileNotFoundError: script.py.mako`
- **Root Cause:** The file was temporarily created during Epic 3.5 work and subsequently deleted.
- **Impact:** Developers cannot use `alembic revision --autogenerate` to generate new migration files. They must write migrations by hand.
- **Fix:** Restore the standard Alembic Mako template file. Content:
  ```mako
  """${message}
  Revision ID: ${up_revision}
  Revises: ${down_revision | comma,n}
  Create Date: ${create_date}
  """
  from alembic import op
  import sqlalchemy as sa
  import sqlmodel

  revision = ${repr(up_revision)}
  down_revision = ${repr(down_revision)}

  def upgrade() -> None:
      ${upgrades if upgrades else "pass"}

  def downgrade() -> None:
      ${downgrades if downgrades else "pass"}
  ```

---

## 🧪 Mock Usage Inventory

| Location | Mock Type | Should Use Real Data? |
|---|---|---|
| `frontend/src/app/runs/page.tsx` | `MOCK_RUNS` constant | **Yes** — wire to `GET /api/runs/` (C-1) |
| `connectors/apps/*.py` — `call_tool()` | Returns hardcoded string | Yes — real API calls for each tool |
| `routers/connectors.py` — install flow | Saves config JSON; no real OAuth | Acceptable for MVP |
| `routers/workflows.py` — `get_templates()` | Two hardcoded `WorkflowResponse` objects | Extend to 5+, ideally load from YAML files |

---

## 📋 Gap vs. Implementation Plan

| Epic | Planned | Implemented | Gap |
|---|---|---|---|
| 3.2 Temporal | Worker + HITL signals in compose | Code exists, not in local compose | ❌ C-3 |
| 3.3 Templates | 5 pre-built templates | 2 templates | ❌ M-4 |
| 3.4.8 Replay | Canvas step-highlight of past run | Not started | ❌ M-7 |
| 3.5 Connectors | 10+ connectors | 4 connectors | ❌ M-5 |
| 3.5 Uninstall | DELETE endpoint + UI | Neither exists | ❌ M-6, m-3 |

---

## Summary

| Severity | Count |
|---|---|
| 🔴 Critical | 3 |
| 🟡 Major | 7 |
| 🟢 Minor | 4 |
| **Total** | **14** |
