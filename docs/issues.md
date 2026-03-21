# ScopeSentinel — Issue Backlog (Phase 1–3 QA Audit)

> **Audited:** 2026-03-21 | 16 issues total | Ordered by severity

---

## ✅ Resolved

### [C-1] Runs page displays hardcoded mock data
- **Fixed:** `frontend/src/app/runs/page.tsx` updated to fetch data via `apiGet`.
- **Status:** Verified.

### [C-2] Connector API — missing `await` on async session queries
- **Fixed:** Added `await` to `session.exec` calls in `connectors.py`.
- **Status:** Verified.

### [C-3] Temporal server missing from local docker-compose
- **Fixed:** Added Temporal services to `docker-compose.yml`.
- **Status:** Verified (log stream connects).

### [C-4] Hydration Error: Nested buttons in Runs page
- **Fixed:** Used `render` prop on `DialogTrigger` in `runs/page.tsx`.
- **Status:** Verified.

### [M-1] runs.py decision endpoint has stale Celery docstring
- **Fixed:** Updated docstring to accurately reflect Temporal integration.
- **Status:** Verified.

### [M-6] No "Uninstall Connector" API endpoint
- **Fixed:** Implemented `DELETE /api/connectors/{connector_id}/uninstall`.
- **Status:** Verified.

---

## 🔴 Critical

### [M-8] Settings page returns 404
- **File:** `frontend/src/app/settings/page.tsx` (missing)
- **Severity:** Critical
- **Category:** Missing Page
- **Reproduce:** Click "Settings" in the sidebar.
- **Impact:** Users cannot manage organization or user settings.

### [M-9] "Review Now" link in banner returns 404 for non-existent runs
- **File:** `frontend/src/components/layout/app-sidebar.tsx` (likely source of banner)
- **Severity:** Critical
- **Category:** Broken Link
- **Reproduce:** Click "Review Now" for a run ID that doesn't exist in the DB (e.g., `run-126`).
- **Impact:** Frustrating UX; links to data that isn't present.

---

## 🟡 Major

### [M-10] Dashboard "Active Runs" metric is placeholder
- **File:** `frontend/src/app/page.tsx`
- **Severity:** Major
- **Category:** Stale Data
- **Reproduce:** Observe "12 Active Runs" on dashboard regardless of actual run count.
- **Impact:** Misleading dashboard metrics.

### [M-2] Visual Designer "Test Run" hardcodes ticket_id = SCRUM-8
- **Severity:** Major
- **Category:** UI Bug
- **Fix:** Needs dynamic input dialog.

### [M-3] `GET /api/workflows/templates` has no authentication guard
- **Severity:** Major
- **Category:** Security
- **Fix:** Add `CurrentUserDep`.

### [M-5] Only 4 connectors implemented (10+ planned)
- **Severity:** Major
- **Category:** Feature Gap

---

## 🟢 Minor

### [m-5] "Configure" button on Integrations page is a no-op
- **Severity:** Minor
- **Category:** UI Gap
- **Fix:** Should open a modal or navigate to a configuration page.

---

## 📋 Summary

| Severity | Count | Status |
|---|---|---|
| ✅ Resolved | 6 | FIXED |
| 🔴 Critical | 2 | OPEN |
| 🟡 Major | 6 | OPEN |
| 🟢 Minor | 2 | OPEN |
| **Total** | **16** | |
