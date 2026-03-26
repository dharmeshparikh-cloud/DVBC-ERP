# D&V Business Consulting - ERP System PRD

## Original Problem Statement
Establish a unified and strict governance model across the ERP. Build customized HR, Consulting, and Sales modules with a full E2E Sales Funnel (Lead Capture -> Meeting -> Pricing Plan -> SOW -> Quotation -> Agreement -> Payment -> Kickoff -> Project).

## Tech Stack
- **Frontend**: React + Tailwind CSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB
- **AI**: GPT-4o-mini via Emergent LLM Key
- **Maps**: Google Maps API (Places Autocomplete)

## Core Modules
1. **HR Module** - Attendance, Leaves, Salary Slips, Expenses, Penalty Management
2. **Consulting Module** - Meetings, Consultant Management
3. **Sales Module** - Full E2E Sales Funnel, Proforma Invoices, Agreements

## What's Been Implemented

### Sales Funnel (COMPLETE)
- Lead Capture -> Meeting -> Pricing Plan -> SOW -> Quotation -> Agreement -> Payment -> Kickoff -> Project
- Pricing Plan auto-upsert (PUT instead of POST error on duplicates)
- SOW Builder (SOWBuilderNew.js is the primary handler)
- Agreement creation and approval workflow

### Proforma Invoice (COMPLETE - 26 Mar 2026)
- B&W minimalist design with D&V logo
- Client GSTIN field in create/edit dialog
- Payment Terms & Conditions box at bottom (replaced Amount Due black box)
- Data-driven PDF export (self-contained HTML, inline styles, no DOM cloning)
- Amount, Meetings, Version columns in table

### Unified Penalty Management (COMPLETE - 26 Mar 2026)
- **Single collection**: `employee_penalties` (deprecated: `attendance_penalties`, `payroll_inputs.penalty`)
- **Single UI**: `/penalty-management` with 4 tabs (Pending Review | Approved | Rejected | Apply Manual)
- **Backend endpoints**: approve, reject, send-back, bulk-action, edit, summary-by-employees
- **Auto-detection**: Late check-in auto-creates penalty with `status: pending_review`, `source: auto_attendance`
- **Attendance validation**: Creates `pending_review` penalties, navigates HR to Penalty Management
- **Payroll engine**: Simplified from 4 sources to 1 — reads ONLY `employee_penalties` where `status: approved`
- **No double-counting**: Single collection + status-based filtering
- **21 violation types** across 5 categories (Attendance, Leave, Travel, Expense, General HR)
- **Testing**: 100% pass rate — 16/16 backend, all frontend flows verified (iteration_239)

### Pagination (FIXED)
- All list APIs return `{data: [], total, page}` format
- Frontend properly extracts `response.data.data`

## Credentials
| Role | Employee ID | Password |
|---|---|---|
| Admin | EMP001 | admin123 |
| Sales | EMP003 | sales123 |
| Consultant | EMP004 | consultant123 |

## Key Files
- `/app/frontend/src/pages/PenaltyManagement.js` - Unified penalty UI
- `/app/backend/routers/penalties.py` - All penalty CRUD + approve/reject/bulk
- `/app/backend/services/payroll_engine.py` - Simplified penalty deduction logic
- `/app/frontend/src/pages/sales-funnel/ProformaInvoice.js`
- `/app/backend/routers/quotations.py`

## P1 - Upcoming Tasks
- Consultant Notifications: System notifications when assigned to project/SOW

## P2 - Future/Backlog
- Delete legacy SOWBuilder.js and sow_legacy.py
- Refactor ConsultingMeetings.js (>2300 lines)
- Governance Dashboard UI for /api/governance/* endpoints
- Realtime penalty badges in attendance/leave tables (GET /api/penalties/summary-by-employees already built)
