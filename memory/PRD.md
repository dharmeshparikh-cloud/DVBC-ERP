# D&V Business Consulting - ERP System PRD

## Original Problem Statement
Establish a unified and strict governance model across the ERP. Build customized HR, Consulting, and Sales modules with a full E2E Sales Funnel (Lead Capture -> Meeting -> Pricing Plan -> SOW -> Quotation -> Agreement -> Payment -> Kickoff -> Project).

## Tech Stack
- **Frontend**: React + Tailwind CSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB
- **AI**: GPT-4o-mini via Emergent LLM Key
- **Maps**: Google Maps API (Places Autocomplete)

## Core Modules
1. **HR Module** - Attendance, Leaves, Salary Slips, Expenses
2. **Consulting Module** - Meetings, Consultant Management
3. **Sales Module** - Full E2E Sales Funnel, Proforma Invoices, Agreements

## What's Been Implemented

### Sales Funnel (COMPLETE)
- Lead Capture -> Meeting -> Pricing Plan -> SOW -> Quotation -> Agreement -> Payment -> Kickoff -> Project
- Pricing Plan auto-upsert (PUT instead of POST error on duplicates)
- SOW Builder (SOWBuilderNew.js is the primary handler)
- Agreement creation and approval workflow

### Proforma Invoice (COMPLETE - Last Updated: 26 Mar 2026)
- B&W minimalist design with D&V logo
- "Management Consulting Services — Professional Fees" as description
- No role-wise rates shown in team deployment table
- Client GSTIN field in create/edit dialog
- Payment Terms & Conditions box at bottom (replaced Amount Due black box)
- Bank Details alongside T&C in 2-column layout
- Data-driven PDF export (self-contained HTML, inline styles, no DOM cloning)
- Table actions (Download PDF, Print) use proper PDF generator
- Amount, Meetings, Version columns in table
- Edit action with PUT endpoint

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
- `/app/frontend/src/pages/sales-funnel/ProformaInvoice.js`
- `/app/frontend/src/components/sales/ProformaInvoiceTable.jsx`
- `/app/backend/routers/quotations.py`
- `/app/backend/routers/pricing_plans.py`

## P1 - Upcoming Tasks
- Late Penalty Workflow: HR UI to review auto-generated penalty records (₹100 flat) approve/reject before payroll
- Consultant Notifications: System notifications when assigned to project/SOW

## P2 - Future/Backlog
- Delete legacy SOWBuilder.js and sow_legacy.py
- Refactor ConsultingMeetings.js (>2300 lines)
- Governance Dashboard UI for /api/governance/* endpoints
