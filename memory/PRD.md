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
- **Unified 9-step stepper header** on ALL funnel pages with "Next action" guide
- Funnel progress bar shows X/9 on leads table
- Batch auto-sync for stage updates
- No manual closed_won — status managed by funnel
- Only `closed` (project created) = onboarded

### FunnelStepperHeader Component (27 Mar 2026)
- 9-step stepper with green checkmarks for completed steps
- "Next: [Step] — [What to do]" guide with Go button
- Shows on: MeetingRecord, PricingPlanBuilder, SOWBuilderNew, ProformaInvoice, Agreements, AgreementView, PaymentVerification
- Clickable completed/current steps for navigation
- "Full Funnel View" link

### Proforma Invoice (COMPLETE - 27 Mar 2026)
- Finalize function removed — just create invoice → proceed
- Lead-scoped when from funnel (locked lead+pricing selectors)
- SOW detection fixed (correct endpoint)
- GSTIN validation + Bill To details
- PDF amounts fixed

### Onboarded Clients (COMPLETE - 27 Mar 2026)
- Standalone page at `/onboarded-clients`
- Only leads with completed 9-step funnel (status=closed)
- Read-only funnel view

### VVS Lead Fix (COMPLETE - 28 Mar 2026)
- Fixed project auto-creation order: project now created BEFORE kickoff status update
- Fixed funnel-progress to verify project actually EXISTS in DB (not just kickoff status)
- Fixed PaymentVerification model: added lead_id field, auto-populated from agreement
- Fixed SOW detection: enhanced_sow checked FIRST before legacy sow; added `items` field fallback
- Fixed bulk auto-sync payment detection via agreement_id chain
- Database repair: created missing project PROJ-20260325-0001 for VVS, backfilled payment lead_id

## Credentials
| Role | Employee ID | Password |
|---|---|---|
| Admin | EMP001 | admin123 |
| Sales | EMP003 | sales123 |
| Consultant | EMP004 | consultant123 |

## Key Files
- `/app/frontend/src/components/FunnelStepperHeader.js` - Unified 9-step stepper
- `/app/frontend/src/pages/sales-funnel/ProformaInvoice.js` - Invoice UI
- `/app/frontend/src/pages/OnboardedClients.js` - Onboarded clients
- `/app/frontend/src/components/sales/LeadsTable.jsx` - 9-stage funnel bar
- `/app/backend/routers/leads.py` - Batch auto-sync, funnel progress
- `/app/backend/routers/kickoff.py` - Kickoff & project creation (FIXED)
- `/app/backend/routers/payments.py` - Payment verification (FIXED)

## P1 - Upcoming Tasks
- Sales Dashboard vs Reality gap analysis (user uploaded screenshot)
- Consultant Notifications when assigned to project/SOW

## P2 - Future/Backlog
- Refactor ConsultingMeetings.js (>2300 lines)
- Governance Dashboard UI
- Onboarding timeline view in Onboarded Clients page
