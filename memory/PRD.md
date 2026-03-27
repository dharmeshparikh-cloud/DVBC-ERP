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
3. **Sales Module** - Full E2E Sales Funnel, Proforma Invoices, Agreements, Onboarded Clients

## What's Been Implemented

### Sales Funnel (COMPLETE)
- 9-step funnel: Lead → Meeting → Pricing → SOW → Proforma Invoice → Agreement → Payment → Kickoff → Project
- Funnel progress bar now shows X/9 (was X/6) with all 9 stages mapped
- LeadStatus expanded: new, contacted, pricing, sow, proposal, agreement, payment, kickoff, closed
- Batch auto-sync (N+1 query optimization) for funnel stage updates
- Fixed collection name: `enhanced_sow` (was wrongly `enhanced_sows`)

### Onboarded Clients (COMPLETE - 27 Mar 2026)
- Separate page at `/onboarded-clients` in Sales sidebar (next to Leads)
- Shows leads with completed funnel (status: closed, closed_won, kickoff)
- "View Funnel" button opens SalesFunnelOnboarding in read-only mode
- Onboarded leads excluded from main Leads page (`exclude_onboarded=true`)
- Search by company, name, email

### Proforma Invoice (COMPLETE - 27 Mar 2026)
- B&W minimalist design with D&V logo
- Client GSTIN with real-time validation (format, state code, PAN extraction, company name matching)
- GSTIN details in Bill To section (PAN, Entity Type, State)
- GSTIN auto-populates from lead data when lead is selected
- Backend GSTIN validation API: POST /api/gstin/validate
- FIXED: PDF amounts no longer show ₹0.00 (was passing React event as invoice)

### Unified Penalty Management (COMPLETE - 26 Mar 2026)
- Single collection: `employee_penalties`
- Single UI: `/penalty-management` with 4 tabs
- Auto-detection + payroll engine integration
- 21 violation types across 5 categories

### Performance Optimization (27 Mar 2026)
- Leads endpoint: Batch queries replaced N+1 pattern (5-6 queries per lead → 1 per collection)
- Agreement page: No longer hangs (was caused by slow leads N+1 auto-sync)

## Credentials
| Role | Employee ID | Password |
|---|---|---|
| Admin | EMP001 | admin123 |
| Sales | EMP003 | sales123 |
| Consultant | EMP004 | consultant123 |

## Key Files
- `/app/frontend/src/pages/OnboardedClients.js` - Onboarded clients page
- `/app/frontend/src/components/sales/LeadsTable.jsx` - 9-stage funnel progress bar
- `/app/frontend/src/pages/sales-funnel/ProformaInvoice.js` - Proforma Invoice UI + PDF
- `/app/frontend/src/utils/gstin.js` - GSTIN validation utility
- `/app/backend/routers/gstin.py` - GSTIN validation API
- `/app/backend/routers/leads.py` - Leads with batch auto-sync
- `/app/backend/routers/models.py` - LeadStatus with 9 stages

## P1 - Upcoming Tasks
- Consultant Notifications: System notifications when assigned to project/SOW

## P2 - Future/Backlog
- Refactor ConsultingMeetings.js (>2300 lines)
- Governance Dashboard UI for /api/governance/* endpoints
- Realtime penalty badges in attendance/leave tables
