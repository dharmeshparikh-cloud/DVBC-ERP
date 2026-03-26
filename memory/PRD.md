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
| Penalty | 100 flat per late day |
| Penalty Status | pending_review (HR approves/rejects) |
| Monthly Reset | Late counter resets each month |
| OT blocked | If half-day or on leave |
| Leave Block | Check-in blocked if approved leave exists |

## RBAC Governance Rules
- **Sales** sees "Clients" terminology, only clients where they are sales_owner
- **Consulting** sees "Projects" terminology, only projects where they are in assigned_team/assigned_consultants
- **Admin/Finance** sees all data

## Sales Funnel - 9-Step Flow
1. Lead Capture → 2. Record Meeting → 3. Pricing Plan → 4. Scope of Work → 5. Quotation → 6. Agreement → 7. Record Payment → 8. Kickoff Request → 9. Project Created

### Key Business Rules
- Agreement must be submitted for approval → approved by Admin/PC before payment/kickoff steps unlock
- Quotation auto-calculates financial fields (subtotal, GST, grand total, meetings) from pricing plan
- All page navigations use path params (not query params) for entity IDs
- No Completion Checklists on funnel steps (removed per user request)
- SOW page uses enhanced SOWBuilderNew (old SalesScopeSelection deleted)

## What's Been Implemented

### Session 1 (Previous)
- GPS Reverse Geocoding, Attendance table overhaul, Leave Balance, Approvals Center, Leads features, HR Regularization, Expense features

### Session 2 (March 26, 2026)
- IST Timezone Fix (28+ files)
- Attendance Governance Model (Early In, Late Out, OT, Half Day, Penalties)
- Pure Numeric Tables for CSV exports
- Tested: iteration_235, iteration_236

### Session 3 (March 26, 2026) — Sales Funnel P0 Fixes
- **Proforma Invoice "Save & Create Invoice"** FIXED — optional client_name, auto-calculation from pricing plan
- **Agreements Creation/View** FIXED — accepts all frontend fields
- **Paginated Response Handling** FIXED across 7 sales-funnel files
- **Consulting Meeting Request Dialog** FIXED — overflow-y-auto
- **RBAC Consultant Data Filtering** FIXED — checks assigned_team/assigned_consultants
- Tested: iteration_237

### Session 4 (March 26, 2026) — Sales Funnel Flow & Navigation
- **VVS Quotation Data Recalculated** — Meetings: 48, GST: ₹1,35,000, Grand Total: ₹8,85,000
- **Quotation Recalculate Endpoint** — PATCH `/api/quotations/{id}/recalculate` for fixing old records
- **Review Agreement Navigation** FIXED — uses path param `/sales-funnel/agreement/{id}` instead of query param
- **SalesScopeSelection.js DELETED** — All scope-selection routes redirect to SOWBuilderNew
- **Completion Checklist REMOVED** from funnel onboarding (user requested cleaner flow)
- **Back to Funnel buttons** added on ProformaInvoice and AgreementView pages
- **Agreement Approval Flow** verified: submit-for-approval → approve (works for VVS)
- **Funnel Step Blocked IDs** fixed (record_payment, kickoff_request, project_created)
- Tested: iteration_238 (backend 100%, frontend 100%)

## P1 Upcoming Tasks
- Late Penalty Workflow (HR review with Confirm/Reject UI)
- Consultant Notifications (assignment alerts)

## P2 Future/Backlog
- Delete legacy `SOWBuilder.js` and `sow_legacy.py`
- Refactor `ConsultingMeetings.js` (2300+ lines)
- Governance Dashboard UI

## Key API Endpoints
- `PATCH /api/quotations/{id}/recalculate` — Recalculates quotation from pricing plan
- `PATCH /api/agreements/{id}/submit-for-approval` — Sales submits for PC/Admin approval
- `PATCH /api/agreements/{id}/approve` — Admin/PC approves agreement
- `GET /api/leads/{id}/funnel-progress` — Full funnel status with blocking logic

## Credentials
| Role | Employee ID | Password |
|---|---|---|
| Admin | EMP001 | admin123 |
| Sales | EMP003 | sales123 |
| Consultant | EMP004 | consultant123 |
