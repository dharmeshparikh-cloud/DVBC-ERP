# NETRA ERP - Product Requirements Document

## Original Problem Statement
Establish a unified and strict governance model for the SOW module, alongside comprehensive tracking for Attendance, Leaves, Expenses, and Leads. The system features real-time Approvals Center via WebSockets, GPS reverse geocoding, dynamic overtime calculation, HR regularization, and a full Sales Funnel.

## Architecture
- **Frontend**: React + Shadcn/UI + TanStack Query
- **Backend**: FastAPI + MongoDB
- **Timezone**: IST (UTC+5:30) — centralized via `/app/backend/utils/timezone.py`
- **Auth**: JWT-based with role-based access control (RBAC)

## Core Modules
1. **Attendance** — Self-service check-in/out with GPS, late detection (IST), overtime calc, HR regularization
2. **Leaves** — Dynamic balance from approved leave_requests, leave application blocked if attendance marked
3. **Expenses** — Draft support, E2E tracking, sent-back resubmission, meeting context
4. **Leads** — Pause/resume, CSV export, role-based reassignment
5. **Sales Funnel** — SOW delivery, agreements, proforma invoices
6. **Approvals Center** — Real-time WebSocket, collapsible sections, expense tabs

## What's Been Implemented

### Session 1 (Previous)
- GPS Reverse Geocoding for Attendance Check-in
- Attendance table overhaul (DD/MM/YYYY, OT/Late calculations, re-check-in, CSV download)
- Real-time Leave Balance from approved leave_requests
- Backend validation blocking leave if attendance already marked
- Approvals Center WebSocket fix
- Leads Pause/Resume + CSV Export
- Sales Team reassign fix
- HR Attendance Regularization API + UI
- Approvals Center restructure (CollapsibleSection, Expense Tabs)
- Expense Meeting Context API + slide-out
- Sent-back expense edit/resubmit

### Session 2 (March 26, 2026) — IST Timezone & Late Detection Fix
- **Created centralized IST timezone utility** (`/app/backend/utils/timezone.py`)
- **Fixed late detection** — was using UTC, hardcoded to 9AM; now uses IST + business policy shift start (10:00)
- **Fixed late_minutes calculation** — now correctly calculates from configured shift start
- **Blocked check-in on approved leave days** — returns 400 error if approved leave exists
- **Fixed leave_type display** — no longer shows CL/SL on "present" status rows
- **Dynamic late recalculation** — all records (old + new) are recalculated server-side using IST
- **Normalized field names** — handles both `check_in`/`check_in_time` field variants
- **IST for check-out** — working hours calculated using IST-aware timestamps
- **IST for regularization** — late status recalculated using IST when HR regularizes records
- Tested: iteration_235.json — 100% pass rate (13/13 backend, all frontend)

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

## Key API Endpoints
| Endpoint | Description |
|---|---|
| `GET /api/my/attendance?month=YYYY-MM` | User's attendance with IST late calc |
| `POST /api/my/check-in` | Self check-in (blocks if leave exists) |
| `POST /api/my/check-out` | Self check-out with OT calc |
| `PUT /api/attendance/{id}/regularize` | HR regularization with IST late recalc |
| `GET /api/my/leave-balance` | Dynamic leave balance |

## Credentials
| Role | Employee ID | Password |
|---|---|---|
| Admin | EMP001 | admin123 |
| Sales | EMP003 | sales123 |
