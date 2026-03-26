# NETRA ERP - Product Requirements Document

## Original Problem Statement
Establish a unified and strict governance model for the SOW module, alongside comprehensive tracking for Attendance, Leaves, Expenses, and Leads. The system features real-time Approvals Center via WebSockets, GPS reverse geocoding, dynamic overtime calculation, HR regularization, and a full Sales Funnel.

## Architecture
- **Frontend**: React + Shadcn/UI + TanStack Query
- **Backend**: FastAPI + MongoDB
- **Timezone**: IST (UTC+5:30) — centralized via `/app/backend/utils/timezone.py` and `/app/frontend/src/utils/dateTimeIST.js`
- **Auth**: JWT-based with role-based access control (RBAC)

## Attendance Governance Model (FINAL)

### Core Formulas
```
Late           = max(0, in_time - shift_start)
Early Login    = max(0, shift_start - in_time)
Late Checkout  = max(0, out_time - shift_end)
Overtime       = Early Login + Late Checkout (capped, informational only)
```

### Rules
| Rule | Value |
|---|---|
| Shift | 10:00 AM - 7:00 PM (configurable) |
| Grace | 10 min noise filter, 3 days/month |
| OT Cap | 120 min/day |
| Half Day Cutoff | 3:00 PM |
| Penalty | ₹100 flat per late day |
| Penalty Status | pending_review (HR approves/rejects) |
| Monthly Reset | Late counter resets each month |
| OT blocked | If half-day or on leave |
| Leave Block | Check-in blocked if approved leave exists |

### Half Day Logic
- Check-in after 3:00 PM → status=half_day, half_day_type=first_half, auto-creates approved CL (0.5 day)
- Check-out before 3:00 PM → status=half_day, half_day_type=second_half, auto-creates approved CL (0.5 day)

### Data Display Rules
- All table cell values are PURE NUMBERS (no "m", "h" suffixes)
- Column headers indicate units: "Late (min)", "Hours (h)", "OT (min)"
- Summary card labels kept as-is
- All times displayed in IST (Asia/Kolkata) regardless of browser timezone

## What's Been Implemented

### Session 1 (Previous)
- GPS Reverse Geocoding, Attendance table overhaul, Leave Balance, Approvals Center, Leads features, HR Regularization, Expense features

### Session 2 (March 26, 2026)
- **IST Timezone Fix** — 28+ files across frontend and backend
- **Centralized IST utilities** — `utils/timezone.py` (backend), `utils/dateTimeIST.js` (frontend)
- **Attendance Governance Model** — Full implementation per rules above
- **Half Day Auto-Detection** — 3 PM cutoff, auto-leave creation
- **Late Penalty System** — ₹100 flat, pending_review for HR, monthly reset
- **Grace Period** — 10 min noise filter, 3 days/month tracking
- **Pure Numeric Tables** — Removed all "m"/"h" suffixes, headers show units
- **Leave Block on Check-in** — Returns 400 if approved leave exists
- **Dynamic Late Recalculation** — All records recalculated server-side using IST
- Tested: iteration_235 (IST fix 100%), iteration_236 (governance 100%)

## P0 Issues (Still Open)
1. **Sales Funnel Agreement step not loading** — `/sales-funnel/agreement/${id}` renders blank
2. **Proforma Invoice "Save & Create Invoice" button not working** — form validation/pricing plan issue

## P1 Upcoming Tasks
- Late Penalty Workflow (HR review with Confirm/Reject)
- Consultant Notifications (assignment alerts)

## P2 Future/Backlog
- Delete legacy `SOWBuilder.js` and `sow_legacy.py`
- Refactor `ConsultingMeetings.js` (2300+ lines)
- Deliverables master admin page UI
- Governance Dashboard UI

## Key DB Collections
| Collection | Purpose |
|---|---|
| `attendance` | Daily records with governance fields |
| `attendance_penalties` | ₹100 flat penalties, pending_review |
| `attendance_history` | Archived re-checkins/re-checkouts |
| `leave_requests` | Includes auto_generated half-day leaves |
| `business_policies` | Shift config, grace rules |

## Credentials
| Role | Employee ID | Password |
|---|---|---|
| Admin | EMP001 | admin123 |
| Sales | EMP003 | sales123 |
| Consultant | EMP004 | consultant123 |
