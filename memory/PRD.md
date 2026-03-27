# D&V Business Consulting - ERP System PRD

## Original Problem Statement
Establish a unified and strict governance model across the ERP. Build customized HR, Consulting, and Sales modules with a full E2E Sales Funnel (Lead Capture -> Meeting -> Pricing Plan -> SOW -> Quotation -> Agreement -> Payment -> Kickoff -> Project).

## Tech Stack
- **Frontend**: React + Tailwind CSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB
- **AI**: GPT-4o-mini via Emergent LLM Key
- **Maps**: Google Maps API (Places Autocomplete)

## What's Been Implemented

### Sales Funnel (COMPLETE)
- 9-step funnel: Lead → Meeting → Pricing → SOW → Proforma Invoice → Agreement → Payment → Kickoff → Project
- Funnel progress bar shows X/9 with all 9 stages mapped
- LeadStatus: new, contacted, pricing, sow, proposal, agreement, payment, kickoff, closed
- Batch auto-sync for funnel stage updates (N+1 → batch queries)
- No manual closed_won shortcut — status fully managed by funnel completion
- Only `closed` (project created) = onboarded

### Proforma Invoice (COMPLETE - 27 Mar 2026)
- **Finalize function removed** — no longer a gate to Agreement. Just create invoice → proceed
- **Lead-scoped** — when navigating from funnel, only shows that lead's invoices, lead+pricing plan selectors locked
- **SOW detection fixed** — now queries `/api/enhanced-sow/by-pricing-plan/` (was using wrong endpoint)
- GSTIN validation with state/PAN/company match in Bill To section
- PDF amounts fixed (was ₹0.00)
- Versioning kept for any changes

### Onboarded Clients (COMPLETE - 27 Mar 2026)
- Standalone page at `/onboarded-clients` in Sales sidebar (next to Leads)
- Only leads with completed 9-step funnel (status=closed = project created)
- View Funnel button opens SalesFunnelOnboarding in read-only mode
- Onboarded leads excluded from main Leads page

### Performance (27 Mar 2026)
- Leads endpoint: batch queries replaced N+1 pattern
- Fixed collection name: `enhanced_sow` (was `enhanced_sows`)
- Fixed collection name: `sow` (was `sows`)

## Credentials
| Role | Employee ID | Password |
|---|---|---|
| Admin | EMP001 | admin123 |
| Sales | EMP003 | sales123 |
| Consultant | EMP004 | consultant123 |

## Key Files
- `/app/frontend/src/pages/sales-funnel/ProformaInvoice.js` - Invoice UI, lead-scoped, no finalize
- `/app/frontend/src/pages/OnboardedClients.js` - Onboarded clients page
- `/app/frontend/src/components/sales/LeadsTable.jsx` - 9-stage funnel bar
- `/app/backend/routers/leads.py` - Batch auto-sync, no manual won
- `/app/backend/routers/quotations.py` - Invoice CRUD
- `/app/backend/routers/gstin.py` - GSTIN validation API

## P1 - Upcoming Tasks
- Consultant Notifications: System notifications when assigned to project/SOW

## P2 - Future/Backlog
- Refactor ConsultingMeetings.js (>2300 lines)
- Governance Dashboard UI for /api/governance/* endpoints
