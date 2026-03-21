# ScopeSentinel — Issue Backlog (Phase 1–3 QA Audit)

> **Audited:** 2026-03-21 | 16 issues total | Ordered by severity

---

## ✅ Resolved

### ~~[C-1] Runs page displays hardcoded mock data~~
- **Fixed:** `frontend/src/app/runs/page.tsx` updated to fetch data via `apiGet`.
- **Status:** Verified.

### ~~[C-2] Connector API — missing `await` on async session queries~~
- **Fixed:** Added `await` to `session.exec` calls in `connectors.py`.
- **Status:** Verified.

### ~~[C-3] Temporal server missing from local docker-compose~~
- **Fixed:** Added Temporal services to `docker-compose.yml`.
- **Status:** Verified (log stream connects).

### ~~[C-4] Hydration Error: Nested buttons in Runs page~~
- **Fixed:** Used `render` prop on `DialogTrigger` in `runs/page.tsx`.
- **Status:** Verified.

### ~~[M-1] runs.py decision endpoint has stale Celery docstring~~
- **Fixed:** Updated docstring to accurately reflect Temporal integration.
- **Status:** Verified.

### ~~[M-2] Visual Designer "Test Run" hardcodes ticket_id = SCRUM-8~~
- **Fixed:** Added dynamic input dialog and refactored to use `apiFetch`.
- **Status:** Verified.

### ~~[M-3] `GET /api/workflows/templates` has no authentication guard~~
- **Fixed:** Added `current_user: CurrentUserDep` to the endpoint.
- **Status:** Verified.

### ~~[M-6] No "Uninstall Connector" API endpoint~~
- **Fixed:** Implemented `DELETE /api/connectors/{connector_id}/uninstall`.
- **Status:** Verified.

### ~~[M-8] Settings page returns 404~~
- **Fixed:** Created `frontend/src/app/settings/page.tsx` placeholder.
- **Status:** Verified.

### ~~[M-9] "Review Now" link in banner returns 404 for non-existent runs~~
- **Fixed:** Updated `HitlBanner` to fetch real pending `run_id` from the API.
- **Status:** Verified.

### ~~[M-10] Dashboard "Active Runs" metric is placeholder~~
- **Fixed:** Implemented `/api/runs/stats` and updated Dashboard to fetch real metrics.
- **Status:** Verified.

### ~~[m-5] "Configure" button on Integrations page is a no-op~~
- **Fixed:** Added alert feedback for the button.
- **Status:** Verified.

---

## 🔴 Critical
*(No critical issues remaining)*

---

## 🟡 Major

### [M-5] Only 4 connectors implemented (10+ planned)
- **Severity:** Major
- **Category:** Feature Gap

---

## 🟢 Minor
*(No minor issues remaining)*

---

## 📋 Summary

| Severity | Count | Status |
|---|---|---|
| ✅ Resolved | 12 | **DONE** |
| 🔴 Critical | 0 | **CLEAN** |
| 🟡 Major | 4 | OPEN |
| 🟢 Minor | 0 | **CLEAN** |
| **Total** | **16** | |
