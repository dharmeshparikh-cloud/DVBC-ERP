# NETRA ERP - Product Requirements Document

## Latest Updates - March 24, 2026

### Consulting Meeting Travel Expense (COMPLETE) [March 24, Session 2]

**Replicated Sales Meeting travel feature in Consulting Meeting scheduling:**
- Full `MeetingLocationPicker` with Google Maps Places autocomplete, Via Locations, Calculate Distance
- Mode of Travel pill buttons: Car ₹7/km, Bike ₹3/km, Transit (manual amount), Accompanied (no expense)
- Round Trip checkbox (auto-doubles distance)
- Backend auto-creates expense record on submit: `status=pending`, linked to `meeting_id` + `payroll_month`
- Expense calc: Car = totalKm × ₹7, Bike = totalKm × ₹3, Transit = manual, Accompanied = ₹0
- `MeetingCreate` model extended: `travel_details`, `travel_companions`, `is_conveyance_claimable`, `scheduled_by`
- Used `useCallback` for stable onChange handler (prevents MeetingLocationPicker infinite re-render loop)

### Consultant Meeting Flow Fix (COMPLETE) [March 24, Session 2]

**Root Causes Found & Fixed:**
1. **Backend RBAC** (`projects.py`): Filter only checked `assigned_team` and `created_by` — now also checks `assigned_consultants`, `assigned_consultants.user_id`, `assigned_consultants.employee_id`, `assigned_team.user_id`
2. **Data gap**: EMP004 (consultant) had no project assignments — assigned to 3 projects (ERP Implementation, Process Optimization, Supply Chain Enhancement)
3. **Past meeting validation**: Blocked past dates entirely — now allows past dates when "Mark as delivered" is checked
4. **Status override**: `status` was hardcoded to `'SCHEDULED'` — now respects `is_delivered` flag, sets `'DELIVERED'` when checked
5. **formData init**: `is_delivered` was missing from initial state (was `undefined`)
6. **UX**: Button text dynamically changes "Schedule Meeting" → "Log Delivered Meeting"

### Data Governance - Phase 1: Dropdown Visibility & Inheritance (COMPLETE) [March 24, Session 2]

**Approach**: Zero-risk, non-breaking, reversible, additive-only.

**New Files Added (no existing code deleted/modified):**
- `useSOWsByProject.js` — Server-side SOW-by-project hook with normalizeSOW/normalizeProject/normalizeClient transformers
- `GovernedDropdown.jsx` — Reusable dropdown with Loading/Empty/Error/Refresh states

**Applied In**: ConsultingMeetings module ONLY (isolated rollout)

**What Changed:**
- Project dropdown: Now shows loading/empty/error states + Refresh button
- Client field: Auto-filled read-only from project selection
- SOW dropdown: Server-side filtered by project_id (useSOWsByProject hook), Refresh, empty state warning
- Meeting Purpose dropdown: Loading/Refresh states added
- Transformer layer normalizes `title` → `name`, `company_name` → `name` at hook level

**Testing**: 100% pass (iteration_208) — 11/11 backend, all frontend flows verified

---

### P0 System-Level Governance Fixes (COMPLETE) [March 24, Session 2]

**Fix 1: Payroll Approval Dialog** ✅
- Added `DialogFooter` with Cancel, Submit for Approval, Reject, and Approve & Lock buttons
- Added Status badge displaying current register state
- Added fallback UI when no payroll register exists

**Fix 2: Approvals Center - Stale State & Cache Invalidation** ✅
- Fixed stale state bug: handleKickoffAction/handleAgreementAction accept directReason
- Added queryClient.invalidateQueries() after actions

**Fix 3: Penalty Dashboard Server-Side Filters** ✅
- Backend accepts: employee_ids, day, department params
- Frontend filter bar: Period, Department, Employee multi-select, Day picker

---

### Previous Session Work (COMPLETE)
- System-wide ZERO-CRASH frontend refactor (1,294 safety fixes)
- Penalty Management UI for 21 penalty types
- Pro-rata salary calculation for mid-month joiners
- Penalty Arrears Auto-tagging for locked payrolls
- HR sidebar visibility fix & Attendance Settings crash fix

---

## Architecture

```
/app/
├── backend/
│   ├── routers/
│   │   ├── approvals.py
│   │   ├── sales_funnel_logic.py
│   │   ├── penalties.py
│   │   ├── attendance.py          # Penalty dashboard with server-side filters
│   │   ├── enhanced_sow.py       # SOW-by-project endpoint
│   │   └── projects.py           # RBAC-filtered project listing
│   └── services/
│       └── payroll_engine.py
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── GovernedDropdown.jsx  # NEW: Reusable dropdown governance
│       │   └── Layout.js
│       ├── hooks/
│       │   ├── useSOWsByProject.js   # NEW: Server-side SOW filter + transformers
│       │   ├── useProjects.js        # Existing (untouched)
│       │   ├── useSOW.js             # Existing (untouched)
│       │   └── useClients.js         # Existing (untouched)
│       ├── utils/
│       │   └── safeUtils.js
│       └── pages/
│           ├── ConsultingMeetings.js  # Updated: GovernedDropdown applied
│           ├── ApprovalsCenter.js     # Fixed: stale state + cache invalidation
│           ├── PayrollEngine.js       # Fixed: Approval Dialog + Penalty Filters
│           └── PenaltyManagement.js
```

---

## Backlog (Prioritized)

### P1 — Upcoming
- Appraisals Integration: Auto-reflect salary revisions in payroll engine
- Data Governance Phase 2: Deduplicate hooks (re-export pattern, no delete)
- Data Governance Phase 3: Transformer layer for remaining modules

### P2 — Future
- HR Dashboard Frontend UI (backend API `/api/hr/dashboard` exists)
- Bank Details Management UI
- Salary Slip PDF generation
- Arrears resolution tracking view for HR
- Data Governance Phase 4: Inline axios → hook migration (1-2 pages at a time)

### P3 — Backlog
- Refactor ConsultingMeetings.js (technical debt, recurrence count: 9)
- Naming standardization (forward-only: new code uses project_id, client_id, sow_id)

---

## Key Credentials
| Role | ID | Password |
|------|-----|----------|
| Admin | EMP001 | admin123 |
| HR Manager | EMP002 | hr123 |
| Sales | EMP003 | sales123 |
| Consultant | EMP004 | consultant123 |
| Employee | EMP005 | employee123 |
